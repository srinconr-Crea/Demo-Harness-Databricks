"""Local browser fixture: real API, Git checkout and OpenSpec; simulated models/PR.

Run explicitly with --data-dir and --port. Bound to loopback only; never deploy
this module in the Databricks App. No external model or GitHub call is made.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import uvicorn

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src" / "agents" / "harness"))

from harness.contracts import ClientProfile
from harness.conversation import ConversationEngine
from harness.conversation_webapp import create_conversation_app
from harness.coordination import SqliteRunCoordinator
from harness.openspec import OpenSpecCLI
from harness.sandbox import verify_general_patch
from harness.sandbox_job import SandboxJobRunner
from harness.store import LocalRunStore
from test_conversation import FakeGithub, FakeModels, git, make_engine
from test_repository_workflow import repository_profile


def create_fixture(data_dir: Path):
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    case = data_dir / "case"
    case.mkdir(exist_ok=True)
    profile_file = data_dir / "profile.json"
    if profile_file.is_file():
        profile = ClientProfile.model_validate_json(profile_file.read_text(encoding="utf-8"))
        source = case / "source"
        github = FakeGithub(source, git("rev-parse", "HEAD", cwd=source))
        store = LocalRunStore(data_dir / "records")
        engine = ConversationEngine(profile, store, SqliteRunCoordinator(case / "state.db"),
                                    lambda: github, lambda *_args: FakeModels(), OpenSpecCLI(), None)
    else:
        engine, github, _models, store, _coordinator, profile = make_engine(case)
        profile = repository_profile()
        (github.source / 'tests').mkdir()
        (github.source / 'tests/test_value.py').write_text(
            "from pathlib import Path\nimport os\ndef test_value():\n    assert (Path(__file__).parents[1] / 'src/value.py').read_text().strip() == 'VALUE = 2'\n    assert 'GITHUB_APP_PRIVATE_KEY' not in os.environ\n", encoding='utf-8')
        (github.source / 'tests/test_config.py').write_text(
            "import json, sqlite3, tomllib\nfrom pathlib import Path\ndef test_config():\n    root = Path(__file__).parents[1]\n    assert json.loads((root / 'config.json').read_text())['value'] == 2\n    assert tomllib.loads((root / 'settings.toml').read_text())['value'] == 2\n    assert sqlite3.connect(':memory:').execute((root / 'query.sql').read_text()).fetchone() == (2,)\n", encoding='utf-8')
        git('add', '.', cwd=github.source)
        git('commit', '-m', 'functional synthetic tests', cwd=github.source)
        github.sha = git('rev-parse', 'HEAD', cwd=github.source)
        profile_file.write_text(profile.model_dump_json(), encoding="utf-8")
    engine.profile = profile
    if sys.platform == 'win32':
        # Browser fixtures run under a long workspace path; production uses UC.
        store.directory = Path('\\\\?\\' + str(store.directory.resolve()))
    engine.publication_mode = 'approved_plan'
    engine.cli = OpenSpecCLI()
    import nbformat
    extra_files = {'config/app.yaml': 'value: 2\n', 'config.json': '{"value": 2}\n',
        'settings.toml': 'value = 2\n', 'docs/result.md': '# Resultado\nSalida 2.\n',
        'result.txt': 'Salida 2\n', 'query.sql': 'SELECT 2 AS value;\n',
        'notebooks/value.ipynb': nbformat.writes(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('%sql\nSELECT 2')]))}

    class BrowserModels(FakeModels):
        def __init__(self, run_id, attempt_id):
            super().__init__()
            self.run_id, self.attempt_id = run_id, attempt_id

        def complete(self, role, prompt, **kwargs):
            payload = json.loads(prompt)
            if role == 'developer' and not payload.get('context_history'):
                return type('Response', (), {'text': json.dumps({'context_request': {'op': 'read_file', 'path': 'src/value.py'}})})()
            response = super().complete(role, prompt, **kwargs)
            if role == "planner" and json.loads(prompt)["artifact"] == "proposal":
                response.text = json.dumps({'summary': 'Cambiar VALUE a 2 y documentar/configurar la salida. Probar sintaxis, formatos y suite funcional; aprobar autoriza el PR automático.',
                    'manifest': [{'op': 'modify', 'path': 'src/value.py'}, *[{'op': 'create', 'path': p} for p in extra_files]], "content":
                    "# Proposal\n\n## Why\nActualizar salida del cliente sintético.\n\n"
                    "## What Changes\n- Cambiar VALUE a 2.\n\n## Capabilities\n\n"
                    "### New Capabilities\n- `client-value`: salida comprobable.\n\n"
                    "### Modified Capabilities\n\n## Impact\nSolo src/value.py.\n"})
            if role == 'planner' and json.loads(prompt)['artifact'] == 'specs':
                value = json.loads(response.text)
                value['content'] = value['content'].replace('## ADDED Requirements', '## Purpose\n\nDefinir la salida comprobable del cliente sintético y sus formatos asociados.\n\n## ADDED Requirements')
                response.text = json.dumps(value)
            if role == 'planner' and payload['artifact'] in {'design', 'tasks'}:
                # The real CLI's template is authoritative for required headings.
                value = json.loads(response.text)
                for line in payload.get('template', '').splitlines():
                    if line.startswith('## ') and '<!--' not in line and line not in value['content'].splitlines():
                        value['content'] += '\n' + line + '\n' + (
                            '- [ ] 1.2 Verificar salida sintética.\n' if payload['artifact'] == 'tasks'
                            else 'Alcance local sintético; conservar controles y verificar salida.\n')
                response.text = json.dumps(value)
            if role == 'developer':
                value = json.loads(response.text)
                value['operations'][0]['expected_sha256'] = payload['context_history'][-1]['result']['sha256']
                value['operations'].extend({'op': 'create', 'path': p, 'content': c} for p, c in extra_files.items())
                response.text = json.dumps(value)
            call_id = uuid.uuid4().hex
            store.save_agent_call(self.run_id, call_id, {
                "run_id": self.run_id, "attempt_id": self.attempt_id,
                "call_id": call_id, "role": role, "stage": kwargs.get("stage"),
                "revision": kwargs.get("revision"), "status": "complete",
                "model": "fixture-simulated", "input_tokens": 10, "output_tokens": 20,
                "estimated_cost_usd": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            time.sleep(0.4)  # Allow the browser to observe incremental artifacts.
            return response

    engine.models_factory = lambda run_id, attempt_id: BrowserModels(run_id, attempt_id)
    class LocalJob:
        def run(self, root, **kwargs):
            import hashlib
            import importlib.util
            script_path = REPOSITORY / 'src/agents/harness/app/sandbox_job_runner.py'
            spec = importlib.util.spec_from_file_location('local_isolated_job', script_path)
            script = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(script)
            directory = data_dir / 'sandbox' / kwargs['run_id'] / kwargs['attempt_id'] / ('1-' + 'a' * 16)
            directory.mkdir(parents=True, exist_ok=True)
            package = SandboxJobRunner._archive(root, profile)
            (directory / 'input.zip').write_bytes(package)
            script._sandbox_path = lambda _value, name: directory / name
            result = script.run('input', 'result', hashlib.sha256(package).hexdigest(), kwargs['test_paths'])
            return {**result, 'job_run_id': 'local-synthetic'}
    engine.test_runner = lambda root, current_profile, paths, record, attempt: verify_general_patch(
        root, current_profile, paths, LocalJob(), run_id=record['run_id'], attempt_id=attempt['attempt_id'], revision=attempt['revision'])
    app = create_conversation_app(engine, profile)

    @app.middleware("http")
    async def local_identity(request, call_next):
        request.scope["headers"] = [*request.scope["headers"],
                                    (b"x-forwarded-user", b"ana@example.com")]
        return await call_next(request)

    app.state.fixture_github = github
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(create_fixture(args.data_dir), host="127.0.0.1", port=args.port)
