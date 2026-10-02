import json
from decimal import Decimal

import pytest
from harness.contracts import ClientProfile
from harness.models import ModelClient, ModelInvocationError
from harness.openspec import OpenSpecCLI, instruction_context
from harness.repo_context import RepoContext, contextual_answer
from harness.skills import SKILLS, SkillCatalog
from harness.store import LocalRunStore
from openspec_helpers import prepare_manual, write_skills


def profile(**kwargs):
    return ClientProfile(repository='example/client', base_branch='develop',
                         openspec_root='openspec', **kwargs)

@pytest.mark.parametrize('damage', ['missing', 'utf8', 'name', 'version', 'size', 'denied'])
def test_skill_catalog_rejects_invalid_preparation(tmp_path, damage):
    write_skills(tmp_path)
    target = tmp_path / '.agents/skills/openspec-explore/SKILL.md'
    p = profile()
    if damage == 'missing':
        target.unlink()
    elif damage == 'utf8':
        target.write_bytes(b'\xff')
    elif damage in {'name', 'version'}:
        target.write_text(target.read_text().replace('openspec-explore' if damage == 'name' else '1.13.2', 'invalid'))
    elif damage == 'size':
        target.write_bytes(b'a' * 131073)
    else:
        p.repository_policy.denied_paths = ['.agents/']
    with pytest.raises(ValueError, match='Preparación manual'):
        SkillCatalog(tmp_path, p, '1.13.2')

def test_skill_path_escape_and_junction_are_rejected(tmp_path):
    from harness.skills import checked_file
    with pytest.raises(ValueError):
        checked_file(tmp_path, '../outside', 100)
    write_skills(tmp_path)
    folder = tmp_path / '.agents/skills/openspec-explore'
    moved = tmp_path / 'outside'
    folder.rename(moved)
    import os
    import subprocess
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(folder), str(moved)], check=True, capture_output=True)
    else:
        folder.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='Preparación manual'):
        SkillCatalog(tmp_path, profile(), '1.13.2')

def test_catalog_and_prompt_budgets_and_immutable_skill(tmp_path):
    write_skills(tmp_path)
    p = profile(openspec_skills={'max_catalog_bytes': 1024})
    with pytest.raises(ValueError, match='Catálogo'):
        SkillCatalog(tmp_path, p, '1.13.2')
    p = profile(openspec_skills={'max_prompt_bytes': 1024})
    catalog = SkillCatalog(tmp_path, p, '1.13.2')
    payload, extras = catalog.compose('explore', {'story': 'x' * 2000})
    class NoCall:
        def complete(self, *args, **kwargs):
            raise AssertionError('No debe invocarse el modelo')
    with pytest.raises(ValueError, match='presupuesto'):
        contextual_answer(NoCall(), 'explorer', payload, **extras)
    target = tmp_path / catalog.entries['explore']['path']
    target.write_text(target.read_text() + '\nChanged')
    with pytest.raises(ValueError, match='cambiaron'):
        catalog.compose('explore', {})

def test_normalized_snapshots_survive_new_checkout_and_tampering(tmp_path):
    first, second = tmp_path / 'a', tmp_path / 'b'
    first.mkdir(); second.mkdir()
    write_skills(first); write_skills(second)
    store = LocalRunStore(tmp_path / 'records')
    values = []
    for root in (first, second):
        catalog = SkillCatalog(root, profile(), '1.13.2')
        _, extras = catalog.compose('apply', {}, instructions={'path': str(root.resolve() / 'openspec/tasks.md')},
            base_sha='a'*40, on_snapshot=lambda s: store.save_instruction_snapshot('run', 'attempt', s))
        values.append(extras['instruction_provenance'])
    assert values[0] == values[1]
    digest = values[0]['snapshot_sha256']
    assert store.load_instruction_snapshot('run', 'attempt', digest)['skill']['name'] == 'openspec-apply-change'
    (store.directory / f'instructions/run/attempt/{digest}.json').write_text('{}')
    with pytest.raises(ValueError, match='integridad'):
        store.load_instruction_snapshot('run', 'attempt', digest)

def test_every_context_round_logs_provenance_without_changing_endpoint_context(tmp_path):
    write_skills(tmp_path)
    (tmp_path / 'source.txt').write_text('hello')
    p = profile()
    class API:
        def __init__(self):
            self.bodies = []
        def do(self, *args, body):
            self.bodies.append(body)
            reply = {'context_request': {'op': 'read_file', 'path': 'source.txt'}} if len(self.bodies) == 1 else {'summary': 'ok', 'questions': []}
            return {'choices': [{'message': {'content': json.dumps(reply)}}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
    api = API()
    model = ModelClient(api, {'explorer': 'sonnet'}, {'sonnet': (Decimal('.1'), Decimal('.2'))},
                        usage_context={'run_id': 'run'})
    payload, extras = SkillCatalog(tmp_path, p, '1.13.2').compose('explore', {})
    assert contextual_answer(model, 'explorer', payload, RepoContext(tmp_path, p), **extras)['summary'] == 'ok'
    assert len(model.calls) == 2
    assert all(c.instruction_provenance == extras['instruction_provenance'] for c in model.calls)
    assert all(b['usage_context'] == {'run_id': 'run'} for b in api.bodies)
    class Failure:
        def do(self, *args, **kwargs):
            raise RuntimeError('endpoint down')
    model.api = Failure()
    with pytest.raises(ModelInvocationError):
        contextual_answer(model, 'explorer', payload, **extras)
    assert model.calls[-1].instruction_provenance == extras['instruction_provenance']
    assert model.calls[-1].cost_usd is None

def test_real_manual_agents_init_installs_all_workflows(tmp_path):
    prepare_manual(tmp_path)
    catalog = SkillCatalog(tmp_path, profile(), OpenSpecCLI().version())
    assert set(catalog.entries) == set(SKILLS)
    assert all(len(item['content']) > 1000 for item in catalog.entries.values())

def test_cli_context_rejects_external_paths_and_blocked_apply(tmp_path):
    from test_conversation import FakeCLI
    root = tmp_path
    cli = FakeCLI()
    cli.new_change(root, 'change-one')
    (root / 'openspec/changes/change-one/tasks.md').write_text('- [ ] task')
    original = cli.instructions
    for field, replacement in [('state', 'blocked'), ('schemaName', 'custom'),
                               ('contextFiles', {'tasks': [str(tmp_path.parent / 'outside.md')]})]:
        cli.instructions = lambda r, a, c, field=field, replacement=replacement: {**original(r, a, c), field: replacement}
        with pytest.raises(ValueError):
            instruction_context(cli, root, 'change-one', 'apply', profile())

def test_skills_are_read_only_even_for_repository_scope():
    p = profile(repository_policy={'scope': 'repository'}, general_patch={
        'extensions': ['.md'], 'operations': ['modify'], 'max_files': 1, 'max_bytes': 100,
        'test_adapters': ['markdown_structure']})
    assert p.allows_read('.agents/skills/openspec-explore/SKILL.md')
    assert not p.allows_code('.agents/skills/openspec-explore/SKILL.md')
