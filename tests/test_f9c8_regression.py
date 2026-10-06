"""Synthetic f9c8 shape, with real OpenSpec CLI and eleven pure filename criteria.

These cases are synthetic acceptance criteria, not recovered production data or
the exact historical test suite. Model endpoints and GitHub publication are fake.
"""
import hashlib
import json
import os
import subprocess
import sys

import pytest

from harness.contracts import ClientProfile, StoryRequest
from harness.openspec import OpenSpecCLI
from test_conversation import git, make_engine
from test_capability_contract import BASE


CASES = [
    ('orders.csv', 'orders'), ('Orders.JSON', 'orders'), ('ORDERS.parquet', 'orders'),
    ('sales-2026.csv', 'sales_2026'), ('sales data.json', 'sales_data'),
    ('001-orders.parquet', 't_001_orders'), ('folder/orders.csv', 'orders'),
    ('folder\\orders.json', 'orders'), ('many...dots.parquet', 'many_dots'),
    ('orders.csv.gz', 'orders_csv_gz'), ('already_valid', 'already_valid'),
]
IMPLEMENTATION = '''import re


def normalize_table_name(filename):
    name = filename.replace('\\\\', '/').rsplit('/', 1)[-1].lower()
    name = re.sub(r'\\.(csv|json|parquet)$', '', name)
    name = re.sub(r'[^a-z0-9_]+', '_', name).strip('_')
    return 't_' + name if name[:1].isdigit() else name
'''
TEST_SOURCE = ('import pytest\nfrom src.io import normalize_table_name\n\n'
               '@pytest.mark.parametrize("filename,expected", ' + repr(CASES) + ')\n'
               'def test_normalize(filename, expected):\n'
               '    assert normalize_table_name(filename) == expected\n')
MANIFEST = [{'op': 'modify', 'path': 'src/io.py'}, {'op': 'create', 'path': 'tests/test_normalize.py'}]
DELTA = ('## MODIFIED Requirements\n\n### Requirement: Ingest\n'
         'The system SHALL normalize table names for CSV, JSON and Parquet filenames according to eleven synthetic criteria.\n\n'
         '#### Scenario: Input\n- **WHEN** input arrives\n- **THEN** it is ingested\n\n'
         + '\n'.join(f'#### Scenario: Synthetic criterion {i}\n- **WHEN** the filename is `{name}`\n- **THEN** the normalized name is `{expected}`\n'
                       for i, (name, expected) in enumerate(CASES, 1)))
PROPOSAL = '# Proposal\n\n## Why\nNormalize synthetic ingestion filenames.\n\n## What Changes\nUpdate io.py and add eleven tests.\n\n## Capabilities\n\n### New Capabilities\n\n### Modified Capabilities\n- `bronze-ingestion`: normalize filename-derived table names.\n\n## Impact\nPure filename transformation and synthetic tests.\n'
DESIGN = '# Design\n\n## Context\nSynthetic ingestion client.\n\n## Goals / Non-Goals\nPreserve eleven pure filename criteria.\n\n## Decisions\nNormalize names with deterministic regular expressions.\n\n## Risks / Trade-offs\nFixtures contain no customer data.\n'
TASKS = '## 1. Implementation\n\n- [ ] 1.1 Normalize filename-derived table names.\n- [ ] 1.2 Verify all eleven synthetic criteria.\n'


class Models:
    def __init__(self):
        self.prompts = []
        self.calls = []
        self.semantic_calls = 0

    def complete(self, role, prompt, **kwargs):
        payload = json.loads(prompt)
        self.prompts.append((role, payload, kwargs))
        self.calls.append((role, kwargs.get('stage')))
        if role == 'explorer':
            value = {'summary': 'Normalize table names with eleven synthetic criteria.', 'questions': []}
        elif role == 'planner':
            artifact = payload['artifact']
            value = {'content': {'proposal': PROPOSAL, 'specs': DELTA, 'design': DESIGN, 'tasks': TASKS}[artifact]}
            if artifact == 'proposal':
                value.update(summary='Normalize CSV/JSON/Parquet table names; verify eleven criteria.', manifest=MANIFEST,
                             capabilities=[{'kind': 'modified', 'path': 'bronze-ingestion'}])
        elif role == 'developer':
            sources = {s['path']: s for s in payload['evidence_bundle']['current_sources']}
            if kwargs['stage'] == 'applying':
                value = {'operations': [
                    {'op': 'modify', 'path': 'src/io.py', 'content': IMPLEMENTATION, 'expected_sha256': sources['src/io.py']['sha256']},
                    {'op': 'create', 'path': 'tests/test_normalize.py', 'content': TEST_SOURCE}],
                    'coverage': [{'path': item['path'], 'status': 'applied'} for item in MANIFEST], 'notes': 'Both approved files applied.'}
            else:
                value = {'operations': [], 'coverage': [{'path': item['path'], 'status': 'already_conformant',
                          'sha256': sources[item['path']]['sha256']} for item in MANIFEST],
                         'notes': 'Current candidate already meets all eleven synthetic criteria; re-check current evidence.'}
        elif role == 'openspec_verifier':
            self.semantic_calls += 1
            if self.semantic_calls == 1:
                value = {'approved': False, 'findings': [{'category': 'implementation', 'code': 'normalization_recheck',
                    'criterion': 'Eleven synthetic normalization scenarios', 'evidence': 'Synthetic initial review requests re-check of current applied implementation against all criteria.',
                    'paths': ['src/io.py', 'tests/test_normalize.py'], 'operations': ['modify'],
                    'recommendation': 'Check existing candidate bytes and complete coverage before writing.'}]}
            else:
                value = {'approved': True, 'findings': []}
        else:
            value = {'approved': True, 'findings': []}
        return type('Response', (), {'text': json.dumps(value)})()


def prepare(tmp_path):
    engine, github, _, store, _, _ = make_engine(tmp_path)
    source = github.source
    (source / 'src/io.py').write_text('def normalize_table_name(filename):\n    return filename\n', encoding='utf-8')
    target = source / 'openspec/specs/bronze-ingestion/spec.md'
    target.parent.mkdir(parents=True)
    target.write_text(BASE, encoding='utf-8')
    git('add', '.', cwd=source)
    git('commit', '-m', 'Synthetic ingestion base', cwd=source)
    github.sha = git('rev-parse', 'HEAD', cwd=source)
    engine.profile = ClientProfile(repository='example/client', base_branch='develop', allowed_paths=['src/', 'tests/'], openspec_root='openspec',
        general_patch={'allowed_paths': ['src/', 'tests/'], 'extensions': ['.py'], 'operations': ['modify', 'create'],
                       'max_files': 2, 'max_bytes': 10000, 'test_adapters': ['python_compile', 'pytest_sandbox'], 'test_paths': ['tests']})
    engine.publication_mode = 'approved_plan'
    engine.cli = OpenSpecCLI()
    models = Models()
    engine.models_factory = lambda *_: models
    return engine, github, models, store


def test_real_cli_rejects_modified_requirement_at_change_id_destination(tmp_path):
    engine, github, _, _ = prepare(tmp_path)
    root = github.source
    engine.cli.new_change(root, 'wrong-ingestion-destination')
    change = root / 'openspec/changes/wrong-ingestion-destination'
    for filename, content in [('proposal.md', PROPOSAL), ('design.md', DESIGN), ('tasks.md', TASKS.replace('[ ]', '[x]')),
                              ('specs/wrong-ingestion-destination/spec.md', DELTA)]:
        target = change / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    with pytest.raises(ValueError, match='OpenSpec'):
        engine.cli.archive(root, 'wrong-ingestion-destination')
    assert (root / 'openspec/specs/bronze-ingestion/spec.md').read_text(encoding='utf-8') == BASE


def test_correct_destination_two_applied_files_noop_coverage_and_eleven_criteria(tmp_path):
    engine, github, models, store = prepare(tmp_path)
    observed = []

    def runner(root, profile, paths, record, attempt):
        completed = subprocess.run([sys.executable, '-B', '-m', 'pytest', 'tests/test_normalize.py', '-q', '-p', 'no:cacheprovider'],
            cwd=root, env={**os.environ, 'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
            text=True, capture_output=True, timeout=45, check=False)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert '11 passed' in completed.stdout
        observed.append({'paths': list(paths), 'io': (root / 'src/io.py').read_bytes(),
                         'tests': (root / 'tests/test_normalize.py').read_bytes(), 'output': completed.stdout})
        return {'passed': True, 'evidence': [completed.stdout], 'criteria_count': 11}

    engine.test_runner = runner
    run_id = engine.submit(StoryRequest(hu='HU-F9C8-SYNTHETIC', description='Normalize CSV/JSON/Parquet table names preserving eleven synthetic criteria'), actor='ana@example.com')
    engine.advance(run_id)
    plan = store.load(run_id)['attempts'][-1]
    assert plan['stage'] == 'awaiting_plan_review'
    engine.act(run_id, 'approve', actor='ana@example.com', expected_revision=plan['revision'], expected_hash=plan['context']['plan_hash'], key='approve')
    final = store.load(run_id)['attempts'][-1]
    assert final['stage'] == 'complete'
    assert len(observed) == 2 and observed[0]['io'] == observed[1]['io'] and observed[0]['tests'] == observed[1]['tests']
    assert all(o['paths'] == ['src/io.py', 'tests/test_normalize.py'] for o in observed)
    assert final['context']['candidate_revision'] == 1 and final['context']['implementation_correction_count'] == 1
    assert final['revision'] == plan['revision'] and [a['kind'] for a in final['approvals']] == ['plan']
    assert final['context']['task_evidence']['plan_hash'] == plan['context']['plan_hash']
    assert final['context']['task_evidence']['verification'] == 'passed'
    assert all(final['context']['task_evidence'][key] == 'complete' for key in ['sync', 'archive', 'publication'])
    assert len([c for c in models.calls if c[0] == 'planner']) == 4
    assert not any(e['kind'] in {'scope_changed', 'update'} for e in final['timeline'])
    assert len(github.published) == 1
    files = github.published[0]
    assert 'openspec/specs/bronze-ingestion/spec.md' in files
    assert not any('/specs/hu-f9c8-synthetic-' in path for path in files)
    assert files['src/io.py'][0] == IMPLEMENTATION and files['tests/test_normalize.py'][0] == TEST_SOURCE
    specs_prompt = next(p for role, p, _ in models.prompts if role == 'planner' and p['artifact'] == 'specs')
    assert specs_prompt['output_path'] == 'specs/bronze-ingestion/spec.md'
    assert specs_prompt['base_spec'].replace('\r\n', '\n') == BASE
    verify_prompt = next(p for role, p, _ in models.prompts if role == 'openspec_verifier')
    assert all(verify_prompt['evidence_bundle']['task_evidence'][key] == 'pending' for key in ['sync', 'archive', 'publication'])
    assert files['openspec/specs/bronze-ingestion/spec.md'][0].count('#### Scenario: Synthetic criterion ') == 11
