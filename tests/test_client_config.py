import hashlib
import importlib.util
import io
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from harness.client_config import load_selected_profile, provenance, read_profile
from harness.contracts import AgentCallContract, ClientProfile, StoryRequest
from harness.conversation import ConversationEngine
from harness.conversation_webapp import create_conversation_app
from harness.github import GitHubAppClient
from harness.patch import FileOperation, apply_file_operations
from harness.sandbox_job import SandboxJobRunner
from test_conversation import make_engine

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_installation', ROOT / 'scripts/prepare_installation.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


def write_profile(tmp_path, data=None):
    path = tmp_path / 'profile.yaml'
    path.write_text(data or 'name: test\nrepository: example/client\nbase_branch: develop\nopenspec_root: openspec\n', encoding='utf-8')
    return path, {'HARNESS_CLIENT_PROFILE_PATH': str(path),
                  'HARNESS_CLIENT_PROFILE_SHA256': hashlib.sha256(path.read_bytes()).hexdigest()}


def test_external_profile_is_loaded_once_and_relative_to_root(tmp_path):
    path, env = write_profile(tmp_path)
    env['HARNESS_CLIENT_PROFILE_PATH'] = 'profile.yaml'
    profile = load_selected_profile(tmp_path, env)
    original = provenance(profile)
    path.write_text('repository: other/repo', encoding='utf-8')
    assert provenance(profile) == original
    assert profile.repository == 'example/client'
    with pytest.raises(ValueError):
        load_selected_profile(tmp_path, env)


@pytest.mark.parametrize('damage', ['missing', 'yaml', 'large', 'hash', 'secret', 'unknown', 'contract', 'unreadable'])
def test_external_profile_fails_closed_without_raw_content(tmp_path, monkeypatch, damage):
    path, env = write_profile(tmp_path)
    if damage == 'missing':
        path.unlink()
    elif damage == 'hash':
        env['HARNESS_CLIENT_PROFILE_SHA256'] = '0' * 64
    elif damage == 'unreadable':
        monkeypatch.setattr(Path, 'open', lambda *a, **k: (_ for _ in ()).throw(PermissionError('sensitive-content')))
    else:
        content = {'yaml': '[invalid', 'large': 'x' * 131073, 'secret': 'token: sensitive-content',
                   'unknown': 'not_supported: sensitive-content', 'contract': 'repository: sensitive-content'}[damage]
        path.write_text(content, encoding='utf-8')
        env['HARNESS_CLIENT_PROFILE_SHA256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError) as exc:
        load_selected_profile(tmp_path, env)
    assert 'sensitive-content' not in str(exc.value)


@pytest.mark.parametrize('env', [{}, {'HARNESS_CLIENT_PROFILE_SHA256': 'a' * 64},
    {'HARNESS_CLIENT_PROFILE_PATH': 'profile.yaml'},
    {'HARNESS_CLIENT_PROFILE_PATH': '../profile.yaml', 'HARNESS_CLIENT_PROFILE_SHA256': 'a' * 64},
    {'HARNESS_CLIENT_PROFILE_PATH': 'profile.yaml', 'HARNESS_CLIENT_PROFILE': 'test'},
    {'HARNESS_CLIENT_PROFILE': '../test'}])
def test_selector_errors_do_not_fall_back(tmp_path, env):
    with pytest.raises(ValueError):
        load_selected_profile(tmp_path, env)


def test_legacy_profile_and_link_rejection(tmp_path, monkeypatch):
    path, _ = write_profile(tmp_path)
    directory = tmp_path / 'config/clients'
    directory.mkdir(parents=True)
    (directory / 'test.yaml').write_bytes(path.read_bytes())
    assert provenance(load_selected_profile(tmp_path, {'HARNESS_CLIENT_PROFILE': 'test'}))['mode'] == 'legacy'
    monkeypatch.setattr(Path, 'is_symlink', lambda p: p == path)
    with pytest.raises(ValueError):
        read_profile(path, mode='external')


@pytest.mark.parametrize('op', ['create', 'modify', 'delete'])
def test_harness_policy_is_protected_in_editor_and_publisher(tmp_path, op):
    profile = ClientProfile(repository='example/client', base_branch='develop', openspec_root='openspec',
        repository_policy={'scope': 'repository'}, general_patch={'operations': ['create', 'modify', 'delete'],
        'extensions': ['.yaml'], 'max_files': 3, 'max_bytes': 1000, 'test_adapters': ['yaml_validate']})
    assert not profile.allows_code('.harness/client.yaml')
    target = tmp_path / '.harness/client.yaml'
    target.parent.mkdir()
    if op != 'create':
        target.write_text('name: original', encoding='utf-8')
    values = {'op': op, 'path': '.harness/client.yaml', 'content': None if op == 'delete' else 'name: unsafe'}
    if op != 'create':
        values['expected_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        apply_file_operations(tmp_path, profile, [FileOperation(**values)])
    github = GitHubAppClient(1, 2, 'unused', repository='example/client', base_branch='develop')
    with pytest.raises(ValueError):
        github.create_feature_pr('example/client', 'feature/test', 'develop', 'title', 'body', 'a'*40,
                                 {'.HARNESS/client.yaml': ('x', None)})
    payload = SandboxJobRunner._archive(tmp_path)
    assert not any('.harness' in p.casefold() for p in zipfile.ZipFile(io.BytesIO(payload)).namelist())


def test_changed_profile_blocks_recovery_and_explicit_retry_replans(tmp_path):
    engine, github, models, store, coordinator, profile = make_engine(tmp_path)
    run = engine.submit(StoryRequest(hu='HU', description='Cambiar salida'), actor='ana')
    engine.advance(run)
    old = store.load(run)['attempts'][-1]
    changed = profile.model_copy(deep=True)
    changed.version = '2'
    other = ConversationEngine(changed, store, coordinator, lambda: github, lambda *_: models,
                               engine.cli, engine.test_runner)
    with pytest.raises(ValueError, match='perfil'):
        other.act(run, 'answer', actor='ana', expected_revision=0, key='answer', text='2')
    with pytest.raises(ValueError, match='perfil'):
        other.advance(run, action={'kind': 'answer', 'actor': 'ana', 'key': 'unsafe', 'text': '2'})
    other.retry_legacy(run)
    current = other.get(run)
    assert len(current['attempts']) == 2
    assert current['attempts'][-1]['approvals'] == []
    assert current['attempts'][-1]['profile_provenance']['sha256'] != old['profile_provenance']['sha256']
    other.advance(run)
    assert other.get(run)['state'] == 'awaiting_clarification'
    assert store.load_profile_snapshot(old['profile_provenance']['snapshot_sha256'])
    call = AgentCallContract(call_id='c', run_id=run, attempt_id=old['attempt_id'], story_id='HU',
        role='explorer', model='configured', pricing_source='configured', profile_provenance=old['profile_provenance'])
    assert call.profile_provenance == old['profile_provenance']


def test_historical_missing_profile_allows_cancel_but_requires_new_attempt(tmp_path):
    engine, github, _, store, _, _ = make_engine(tmp_path)
    run = engine.submit(StoryRequest(hu='HU', description='Cambiar salida'), actor='ana')
    engine.advance(run)
    record = store.load(run)
    record['attempts'][-1].pop('profile_provenance')
    store.save(run, record)
    assert engine.get(run)['attempts'][-1].get('profile_provenance') is None
    with pytest.raises(ValueError):
        engine.act(run, 'answer', actor='ana', expected_revision=0, key='no', text='2')
    engine.github_factory = lambda: (_ for _ in ()).throw(AssertionError('cancel must not clone'))
    engine.act(run, 'cancel', actor='ana', expected_revision=0, key='cancel')
    assert engine.get(run)['state'] == 'cancelled'
    engine.github_factory = lambda: github
    engine.retry_legacy(run)
    assert engine.get(run)['attempts'][-1]['stage'] == 'exploring'


def test_retry_cannot_move_run_to_another_repository(tmp_path):
    engine, _, _, _, _, _ = make_engine(tmp_path)
    run = engine.submit(StoryRequest(hu='HU', description='Cambiar salida'), actor='ana')
    engine.profile.repository = 'other/client'
    with pytest.raises(ValueError, match='repositorio'):
        engine.retry_legacy(run)


def test_packaging_two_clients_and_configuration(tmp_path):
    # Small product checkout exercises actual Git discovery, not a mocked copy list.
    (tmp_path / 'src/agents/harness/app').mkdir(parents=True)
    (tmp_path / 'src/agents/harness/app/index.html').write_text('common-product', encoding='utf-8')
    models_path = tmp_path / 'src/agents/harness/config/defaults/models.yaml'
    models_path.parent.mkdir(parents=True)
    models_path.write_bytes((ROOT / 'src/agents/harness/config/defaults/models.yaml').read_bytes())
    (tmp_path / '.gitignore').write_text('.deployments/\nnode_modules/\n', encoding='utf-8')
    (tmp_path / 'databricks.yml').write_bytes((ROOT / 'databricks.yml').read_bytes())
    subprocess.run(['git', 'init', '-b', 'develop'], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'product'], cwd=tmp_path, check=True, capture_output=True)
    path, _ = write_profile(tmp_path)
    env = yaml.safe_load((ROOT / 'examples/naturapet/environment.yaml').read_text(encoding='utf-8'))
    env_path = tmp_path / 'environment.yaml'
    env_path.write_text(yaml.safe_dump(env), encoding='utf-8')
    env['variables']['sonnet_endpoint'] = 'databricks-claude-sonnet-5'
    env_path.write_text(yaml.safe_dump(env), encoding='utf-8')
    with pytest.raises(ValueError, match='routing'):
        packager.prepare('bad-routing', path, env_path, root=tmp_path)
    assert not (tmp_path / '.deployments/bad-routing').exists()
    env['variables']['sonnet_endpoint'] = 'databricks-claude-sonnet-5-5'
    env_path.write_text(yaml.safe_dump(env), encoding='utf-8')
    first = packager.prepare('client-a', path, env_path, root=tmp_path)
    path.write_text(path.read_text().replace('example/client', 'example/client-b').replace('name: test', 'name: client-b'), encoding='utf-8')
    env['bundle_name'] = 'demo_harness_second'
    env['variables']['app_name'] = 'demo-harness-second'
    env['variables']['catalog'] = 'demo_harness_second'
    env_path.write_text(yaml.safe_dump(env), encoding='utf-8')
    second = packager.prepare('client-b', path, env_path, root=tmp_path)
    for package, repo in ((first, 'example/client'), (second, 'example/client-b')):
        app_root = package / 'src/agents/harness'
        config = yaml.safe_load((package / 'databricks.yml').read_text())
        selection = {'HARNESS_CLIENT_PROFILE_PATH': 'config/deployment/client.yaml',
                     'HARNESS_CLIENT_PROFILE_SHA256': config['targets']['dev']['variables']['client_profile_sha256']}
        assert load_selected_profile(app_root, selection).repository == repo
        assert not (app_root / 'config/clients').exists()
        assert not (package / '.git').exists()
    assert (first / 'src/agents/harness/app/index.html').read_bytes() == (second / 'src/agents/harness/app/index.html').read_bytes()
    with pytest.raises(ValueError, match='Destino'):
        packager.prepare('client-a', path, env_path, root=tmp_path)
    with pytest.raises(ValueError):
        packager.prepare('../escape', path, env_path, root=tmp_path)


@pytest.mark.parametrize('client_name', ['Cliente A', 'Cliente B'])
def test_ui_reads_name_without_exposing_profile(tmp_path, client_name):
    engine, _, _, _, _, profile = make_engine(tmp_path)
    profile.ui = {'display_name': client_name}
    with TestClient(create_conversation_app(engine, profile)) as client:
        config = client.get('/configuration').json()
        assert config['ui']['display_name'] == client_name
        assert 'repository' not in config and 'github_installation_id' not in config
        assert 'HARNESS_CLIENT_PROFILE_PATH' not in client.get('/').text
