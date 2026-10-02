"""Exercise the distributable product and its real FastAPI entrypoint offline."""

import hashlib
import importlib.util
import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packaged_product(tmp_path):
    product = tmp_path / 'product'
    product.mkdir()
    paths = subprocess.run(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode().split('\0')
    for relative in paths:
        source = ROOT / relative
        if relative and source.is_file() and (
            relative.startswith(('src/agents/', 'resources/', 'scripts/', 'examples/legacy-agentops-scaffold/'))
            or relative in {'.gitignore', 'databricks.yml'}
        ):
            target = product / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for command in (
        ['git', 'init', '-b', 'develop'], ['git', 'add', '.'],
        ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'synthetic'],
    ):
        subprocess.run(command, cwd=product, check=True, capture_output=True)
    profile = tmp_path / 'profile.yaml'
    profile.write_text('name: synthetic\nrepository: example/synthetic\nbase_branch: develop\nopenspec_root: openspec\n', encoding='utf-8')
    environment = tmp_path / 'environment.yaml'
    environment.write_bytes((ROOT / 'examples/naturapet/environment.yaml').read_bytes())
    spec = importlib.util.spec_from_file_location('scaffold_packager', ROOT / 'scripts/prepare_installation.py')
    packager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packager)
    return packager.prepare('synthetic', profile, environment, root=product)


def test_distributable_keeps_runtime_and_excludes_legacy(packaged_product):
    package = packaged_product
    app_root = package / 'src/agents/harness'
    manifest = json.loads((package / 'installation.json').read_text(encoding='utf-8'))
    for relative, digest in manifest['source_sha256'].items():
        assert hashlib.sha256((package / relative).read_bytes()).hexdigest() == digest
    for relative in (
        'app/start_server.py', 'app/index.html', 'app/provision_run_state.py',
        'app/sandbox_job_runner.py', 'harness/evaluation.py',
        'config/defaults/models.yaml', 'config/defaults/context.yaml',
        'package.json', 'package-lock.json', 'uv.lock',
    ):
        assert (app_root / relative).is_file(), relative
    assert (package / 'resources/experiment.yml').is_file()
    assert not (package / 'resources/uc_function_registration.yml').exists()
    assert not (package / 'examples').exists()
    for relative in ('agent.py', 'graph.py', 'tools.py', 'app/utils.py', 'eval'):
        assert not (app_root / relative).exists(), relative
    config = yaml.safe_load((package / 'databricks.yml').read_text(encoding='utf-8'))
    assert config['targets']['dev']['variables']['client_profile_sha256'] == manifest['profile_sha256']
    assert hashlib.sha256((app_root / 'config/deployment/client.yaml').read_bytes()).hexdigest() == manifest['profile_sha256']
    assert 'openspec' in (app_root / 'package.json').read_text(encoding='utf-8')


def test_packaged_fastapi_entrypoint_starts_without_credentials(packaged_product, monkeypatch):
    import databricks.sdk

    package = packaged_product
    app_root = package / 'src/agents/harness'
    manifest = json.loads((package / 'installation.json').read_text(encoding='utf-8'))
    for name in (
        'HARNESS_CLIENT_PROFILE', 'RUN_STORE_DIR', 'HARNESS_RUN_STATE_TABLE',
        'HARNESS_SANDBOX_JOB_ID', 'HARNESS_SANDBOX_DIR', 'GITHUB_APP_PRIVATE_KEY',
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('HARNESS_CLIENT_PROFILE_PATH', 'config/deployment/client.yaml')
    monkeypatch.setenv('HARNESS_CLIENT_PROFILE_SHA256', manifest['profile_sha256'])
    monkeypatch.setattr(databricks.sdk, 'WorkspaceClient', lambda: SimpleNamespace(files=None))
    previous_path = sys.path[:]
    try:
        server = runpy.run_path(str(app_root / 'app/start_server.py'), run_name='offline_startup')
        with TestClient(server['app']) as client:
            assert client.get('/').status_code == 200
            assert client.get('/configuration').status_code == 200
        assert server['PROFILE'].repository == 'example/synthetic'
        assert server['SANDBOX_JOB'] is None
    finally:
        sys.path[:] = previous_path
