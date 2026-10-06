import json
from pathlib import Path

import pytest

from harness.contracts import StoryRequest
from harness.openspec import OpenSpecCLI, propose_client_change, mark_tasks_complete
from openspec_helpers import prepare_manual


BASE = '# Ingestion\n\n## Purpose\nIngest synthetic data safely.\n\n## Requirements\n\n### Requirement: Ingest\nThe system SHALL ingest records.\n\n#### Scenario: Input\n- **WHEN** records arrive\n- **THEN** ingest them\n'
DELTA = '## MODIFIED Requirements\n\n### Requirement: Ingest\nThe system SHALL ingest validated records.\n\n#### Scenario: Input\n- **WHEN** valid records arrive\n- **THEN** ingest them\n'
ADDED = DELTA.replace('MODIFIED', 'ADDED')


class Planner:
    def __init__(self, capabilities, delta=DELTA):
        self.capabilities = capabilities
        self.delta = delta
        self.prompts = []

    def complete(self, role, prompt, **kwargs):
        payload = json.loads(prompt)
        self.prompts.append(payload)
        artifact = payload['artifact']
        content = {
            'proposal': '# Proposal\n\n## Why\nValidate ingestion.\n\n## What Changes\nImprove ingestion.\n\n## Capabilities\nDeclared in typed contract.\n\n## Impact\nSynthetic client.\n',
            'specs': self.delta,
            'design': '# Design\n\n## Context\nSynthetic client.\n\n## Goals / Non-Goals\nValidate ingestion.\n\n## Decisions\nUse validation.\n\n## Risks / Trade-offs\nTest input.\n',
            'tasks': '## 1. Implementation\n\n- [ ] 1.1 Implement ingestion validation.\n',
        }[artifact]
        result = {'content': content}
        if artifact == 'proposal' and self.capabilities is not None:
            result['capabilities'] = self.capabilities
        return type('Response', (), {'text': json.dumps(result)})()


def client(tmp_path):
    root = tmp_path / 'client'
    root.mkdir()
    cli = OpenSpecCLI()
    prepare_manual(root, cli=cli)
    target = root / 'openspec/specs/bronze-ingestion/spec.md'
    target.parent.mkdir(parents=True)
    target.write_text(BASE, encoding='utf-8')
    return root, cli


def propose(root, cli, planner, **kwargs):
    return propose_client_change(cli, root, 'validate-ingestion', StoryRequest(hu='HU-1', description='Validate ingestion'), planner, **kwargs)


def test_existing_capability_uses_its_destination_and_full_base(tmp_path):
    root, cli = client(tmp_path)
    planner = Planner([{'kind': 'modified', 'path': 'bronze-ingestion'}])
    plan = propose(root, cli, planner)
    assert 'openspec/changes/validate-ingestion/specs/bronze-ingestion/spec.md' in plan.artifacts
    assert not (root / 'openspec/changes/validate-ingestion/specs/validate-ingestion/spec.md').exists()
    assert next(p for p in planner.prompts if p['artifact'] == 'specs')['base_spec'] == (root / 'openspec/specs/bronze-ingestion/spec.md').read_bytes().decode('utf-8')


@pytest.mark.parametrize('capabilities', [None, [], [{'kind': 'modified', 'path': 'missing'}], [{'kind': 'new', 'path': '../escape'}], [{'kind': 'new', 'path': 'bronze-ingestion'}]])
def test_invalid_capabilities_fail_before_delta_write(tmp_path, capabilities):
    root, cli = client(tmp_path)
    with pytest.raises(ValueError):
        propose(root, cli, Planner(capabilities))
    assert not list((root / 'openspec/changes/validate-ingestion').glob('specs/**/*.md'))


def test_modified_requirement_must_exist_in_declared_base(tmp_path):
    root, cli = client(tmp_path)
    with pytest.raises(ValueError, match='requisito'):
        propose(root, cli, Planner([{'kind': 'modified', 'path': 'bronze-ingestion'}], DELTA.replace('Requirement: Ingest', 'Requirement: Absent')))


def test_update_removes_stale_delta_preserves_history_and_archives(tmp_path):
    root, cli = client(tmp_path)
    history = []
    first = propose(root, cli, Planner([{'kind': 'modified', 'path': 'bronze-ingestion'}]), on_artifact=lambda *args: history.append(args))
    second = propose(root, cli, Planner([{'kind': 'new', 'path': 'new-ingestion'}], ADDED), feedback='New capability instead', on_artifact=lambda *args: history.append(args))
    assert set(p.relative_to(root).as_posix() for p in (root / 'openspec/changes/validate-ingestion/specs').rglob('spec.md')) == {p for p in second.artifacts if '/specs/' in p}
    assert any(item[0] in first.artifacts and item[1] == DELTA for item in history)
    mark_tasks_complete(root, 'validate-ingestion')
    cli.archive(root, 'validate-ingestion')
    assert (root / 'openspec/specs/new-ingestion/spec.md').exists()
    assert (root / 'openspec/specs/bronze-ingestion/spec.md').read_text(encoding='utf-8') == BASE


def test_multiple_capabilities_including_existing_nested_path(tmp_path):
    root, cli = client(tmp_path)
    nested = root / 'openspec/specs/data/bronze/spec.md'
    nested.parent.mkdir(parents=True)
    nested.write_text(BASE, encoding='utf-8')
    capabilities = [{'kind': 'modified', 'path': 'bronze-ingestion'}, {'kind': 'modified', 'path': 'data/bronze'}, {'kind': 'new', 'path': 'validation-report'}]

    class Multiple(Planner):
        def complete(self, role, prompt, **kwargs):
            payload = json.loads(prompt)
            self.delta = ADDED if payload.get('capability', {}).get('kind') == 'new' else DELTA
            return super().complete(role, prompt, **kwargs)

    plan = propose(root, cli, Multiple(capabilities))
    assert {p for p in plan.artifacts if '/specs/' in p} == {f'openspec/changes/validate-ingestion/specs/{c["path"]}/spec.md' for c in capabilities}
    mark_tasks_complete(root, 'validate-ingestion')
    cli.archive(root, 'validate-ingestion')
    assert 'validated' in nested.read_text(encoding='utf-8')


def test_cli_strict_validation_rejects_incomplete_modified_requirement(tmp_path):
    root, cli = client(tmp_path)
    with pytest.raises(ValueError, match='OpenSpec'):
        propose(root, cli, Planner([{'kind': 'modified', 'path': 'bronze-ingestion'}], '## MODIFIED Requirements\n\n### Requirement: Ingest\nThe system SHALL ingest records.\n'))


def test_runtime_artifact_mismatch_is_harness_defect_without_update_cycle(tmp_path):
    root, cli = client(tmp_path)
    planner = Planner([{'kind': 'modified', 'path': 'bronze-ingestion'}])

    def corrupt(path, content, digest):
        if '/specs/' in path:
            (root / path).write_text(ADDED, encoding='utf-8')

    with pytest.raises(ValueError) as failure:
        propose(root, cli, planner, on_artifact=corrupt)
    assert failure.value.category == 'harness_defect'
    assert len([p for p in planner.prompts if p['artifact'] == 'proposal']) == 1
