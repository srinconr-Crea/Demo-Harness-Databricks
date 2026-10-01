import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from harness.sandbox_job import SandboxJobRunner


def test_managed_sandbox_grants_keep_app_and_job_access_on_redeployment():
    """Managed UC grants must retain permissions also added by App bindings."""
    import yaml

    repository = Path(__file__).resolve().parents[1]
    volume = yaml.safe_load((repository / "resources/volumes.yml").read_text())["resources"]["volumes"]["sandbox"]
    grants = {entry["principal"]: set(entry["privileges"]) for entry in volume["grants"]}
    assert set(grants) == {"${var.sandbox_service_principal}",
                           "${resources.apps.harness.service_principal_client_id}"}
    assert all(privileges == {"READ_VOLUME", "WRITE_VOLUME"} for privileges in grants.values())


class Files:
    def __init__(self):
        self.values = {}

    def create_directory(self, _path):
        pass

    def upload(self, path, content, overwrite):
        assert overwrite
        self.values[path] = content.read()

    def download(self, path):
        return type("Download", (), {"contents": io.BytesIO(self.values[path])})()


class API:
    def __init__(self, files):
        self.files = files
        self.submissions = []

    def do(self, method, path, body=None):
        if method == "POST":
            assert path.endswith("/jobs/run-now")
            self.submissions.append(body)
            params = body["job_parameters"]
            self.files.values[params["result_path"]] = json.dumps({
                "run_id": "a" * 32, "attempt_id": "b" * 32,
                "archive_sha256": params["archive_sha256"], "passed": True,
                "evidence": ["2 passed"],
            }).encode()
            return {"run_id": 42}
        assert method == "GET" and path.endswith("run_id=42")
        return {"state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"}}


def test_job_uploads_bounded_checkout_and_reads_matching_result(tmp_path: Path):
    root = tmp_path / "client"
    (root / "src").mkdir(parents=True)
    (root / "src" / "value.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("origin", encoding="utf-8")
    files = Files()
    api = API(files)
    runner = SandboxJobRunner(api, files, job_id=9,
                              volume_dir="/Volumes/demo_harness_catalog/schema/demo_harness_sandbox")
    result = runner.run(root, run_id="a" * 32, attempt_id="b" * 32, revision=2,
                        test_paths=["tests"])
    assert result["passed"] is True and result["job_run_id"] == 42
    body = api.submissions[0]
    assert body["job_id"] == 9 and len(body["idempotency_token"]) == 64
    with zipfile.ZipFile(io.BytesIO(files.values[body["job_parameters"]["input_path"]])) as archive:
        assert archive.namelist() == ["src/value.py"]


def test_sandbox_script_runs_tests_without_app_secrets(tmp_path: Path, monkeypatch):
    from importlib.util import module_from_spec, spec_from_file_location

    path = Path(__file__).resolve().parents[1] / "src" / "agents" / "harness" / "app" / "sandbox_job_runner.py"
    spec = spec_from_file_location("sandbox_job_runner", path)
    script = module_from_spec(spec)
    spec.loader.exec_module(script)
    directory = tmp_path / ("a" * 32) / ("b" * 32) / "1-abcdef0123456789"
    directory.mkdir(parents=True)
    source = directory / "input.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("src/value.py", "VALUE = 42\n")
        archive.writestr("tests/test_import.py", "from src.value import VALUE\ndef test_checkout_import():\n    assert VALUE == 42\n")
        archive.writestr("tests/test_value.py", "import os\ndef test_secret_absent():\n    assert 'GITHUB_APP_PRIVATE_KEY' not in os.environ\n    assert 'DATABRICKS_TOKEN' not in os.environ\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "sensitive")
    monkeypatch.setenv("DATABRICKS_TOKEN", "sensitive")
    monkeypatch.setattr(script, "_sandbox_path", lambda _value, name: directory / name)
    result = script.run("input", "result", digest, ["tests"])
    assert result["passed"] is True
    assert json.loads((directory / "result.json").read_text(encoding="utf-8"))["archive_sha256"] == digest


def test_sandbox_script_rejects_archive_traversal(tmp_path: Path, monkeypatch):
    from importlib.util import module_from_spec, spec_from_file_location

    path = Path(__file__).resolve().parents[1] / "src" / "agents" / "harness" / "app" / "sandbox_job_runner.py"
    spec = spec_from_file_location("sandbox_job_runner_bad", path)
    script = module_from_spec(spec)
    spec.loader.exec_module(script)
    directory = tmp_path / ("a" * 32) / ("b" * 32) / "1-abcdef0123456789"
    directory.mkdir(parents=True)
    source = directory / "input.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../escape.py", "print('bad')")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(script, "_sandbox_path", lambda _value, name: directory / name)
    with pytest.raises(ValueError, match="inválid"):
        script.run("input", "result", digest, ["tests"])


@pytest.mark.parametrize('outcome', ['passed', 'failed', 'timeout', 'missing_cli', 'missing_target'])
def test_bundle_validation_is_fixed_bounded_and_mandatory(tmp_path, monkeypatch, outcome):
    import subprocess
    from importlib.util import module_from_spec, spec_from_file_location

    path = Path(__file__).resolve().parents[1] / 'src/agents/harness/app/sandbox_job_runner.py'
    spec = spec_from_file_location('sandbox_bundle_runner', path)
    script = module_from_spec(spec)
    spec.loader.exec_module(script)
    directory = tmp_path / ('a' * 32) / ('b' * 32) / '1-abcdef0123456789'
    directory.mkdir(parents=True)
    source = directory / 'input.zip'
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr('databricks.yml', 'bundle:\n  name: synthetic\n')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(script, '_sandbox_path', lambda _value, name: directory / name)
    monkeypatch.setattr(script.shutil, 'which', lambda _name: None if outcome == 'missing_cli' else '/trusted/databricks')
    def execute(command, **kwargs):
        assert command == ['/trusted/databricks', 'bundle', 'validate', '--strict', '-t', 'sandbox']
        assert kwargs['timeout'] == 600 and 'DATABRICKS_TOKEN' not in kwargs['env']
        assert not kwargs.get('shell')
        if outcome == 'timeout':
            raise subprocess.TimeoutExpired(command, 600)
        return subprocess.CompletedProcess(command, 1 if outcome == 'failed' else 0, 'x' * 8000, '')
    monkeypatch.setattr(script.subprocess, 'run', execute)
    if outcome in {'missing_cli', 'missing_target'}:
        with pytest.raises(ValueError, match='CLI|Objetivos'):
            script.run('input', 'result', digest, [], '' if outcome == 'missing_target' else 'sandbox')
    else:
        result = script.run('input', 'result', digest, [], 'sandbox')
        assert result['passed'] == (outcome == 'passed')
        assert len(result['evidence'][0]) <= 6000
