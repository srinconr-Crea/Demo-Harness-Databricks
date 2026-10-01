"""Product acceptance with synthetic repositories and a mocked Windows CLI."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from harness.client_config import read_profile
from harness.contracts import StoryRequest
from harness.conversation import ConversationEngine
from harness.conversation_webapp import create_conversation_app
from test_conversation import make_engine, git

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['client-a', 'client-b'])
def test_two_clients_use_the_same_engine_with_external_profiles(tmp_path, name):
    base, github, models, store, coordinator, profile = make_engine(tmp_path)
    # A pure client test runs against the changed checkout without Databricks credentials.
    tests = github.source / 'tests'
    tests.mkdir()
    (tests / 'test_value.py').write_text('from src.value import VALUE\ndef test_value():\n    assert VALUE == 2\n', encoding='utf-8')
    git('add', '.', cwd=github.source)
    git('commit', '-m', 'synthetic test', cwd=github.source)
    github.sha = git('rev-parse', 'HEAD', cwd=github.source)
    profile.name = name
    profile.repository = f'example/{name}'
    profile.ui = {'display_name': name}
    path = tmp_path / 'approved.yaml'
    import yaml
    path.write_text(yaml.safe_dump(profile.model_dump(mode='json')), encoding='utf-8')
    selected = read_profile(path, mode='external', expected_hash=hashlib.sha256(path.read_bytes()).hexdigest())
    def publish(repository, branch, base_branch, title, body, base_sha, files, **kwargs):
        assert repository == f'example/{name}' and base_branch == 'develop' and branch.startswith('feature/')
        github.published.append(files)
        return f'https://github.com/example/{name}/pull/1'
    github.create_feature_pr = publish
    def test_runner(root, *_args):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('DATABRICKS_', 'GITHUB_', 'AWS_', 'AZURE_'))}
        env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        completed = subprocess.run([sys.executable, '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider',
                                    '-o', 'pythonpath=.'], cwd=root, env=env, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return {'passed': True, 'evidence': [completed.stdout]}
    engine = ConversationEngine(selected, store, coordinator, lambda: github, lambda *_: models,
                                base.cli, test_runner)
    run = engine.submit(StoryRequest(hu='HU', description='Cambiar VALUE a 2'), actor='ana')
    engine.advance(run)
    engine.act(run, 'answer', actor='ana', expected_revision=0, key='answer', text='Salida 2')
    plan = engine.get(run)['attempts'][-1]
    restarted = ConversationEngine(selected, store, coordinator, lambda: github, lambda *_: models,
                                   base.cli, test_runner)
    restarted.act(run, 'approve', actor='ana', expected_revision=plan['revision'],
                  expected_hash=plan['context']['plan_hash'], key='approve')
    final = restarted.get(run)['attempts'][-1]
    assert final['stage'] == 'complete' and len(github.published) == 1
    assert final['profile_provenance']['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert final['publication']['pr_url'] == f'https://github.com/example/{name}/pull/1'
    with TestClient(create_conversation_app(restarted, selected)) as client:
        assert client.get('/configuration').json()['ui']['display_name'] == name


@pytest.mark.parametrize('case', ['ok', 'start-error', 'get-error', 'missing-url', 'bad-url', 'wrong-app', 'missing-argument'])
def test_windows_launcher_uses_selected_app_and_url(case):
    import importlib.util
    spec = importlib.util.spec_from_file_location('start_harness', ROOT / 'scripts/start_harness.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    commands, opened = [], []
    def run(command, **kwargs):
        commands.append(command)
        assert command[3] == 'App with spaces' and command[5] == 'Profile with spaces'
        if case == command[2] + '-error':
            raise subprocess.CalledProcessError(1, command)
        value = {'name': 'Other App' if case == 'wrong-app' else 'App with spaces',
                 'url': 'https://untrusted.example.com' if case == 'bad-url' else 'https://selected.azure.databricksapps.com'}
        if case == 'missing-url':
            value.pop('url')
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(value))
    def open_url(url):
        opened.append(url)
        return True
    if case == 'ok':
        assert helper.start('App with spaces', 'Profile with spaces', run=run, open_url=open_url) == 'https://selected.azure.databricksapps.com'
        assert len(commands) == 2 and len(opened) == 1
    else:
        with pytest.raises(ValueError):
            helper.start('' if case == 'missing-argument' else 'App with spaces', 'Profile with spaces', run=run, open_url=open_url)
        assert not opened
