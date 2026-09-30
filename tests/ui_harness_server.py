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

from harness.conversation_webapp import create_conversation_app
from harness.contracts import ClientProfile
from harness.conversation import ConversationEngine
from harness.coordination import SqliteRunCoordinator
from harness.openspec import OpenSpecCLI
from harness.store import LocalRunStore
from test_conversation import FakeGithub, FakeModels, git, make_engine


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
        profile_file.write_text(profile.model_dump_json(), encoding="utf-8")
    engine.cli = OpenSpecCLI()

    class BrowserModels(FakeModels):
        def __init__(self, run_id, attempt_id):
            super().__init__()
            self.run_id, self.attempt_id = run_id, attempt_id

        def complete(self, role, prompt, **kwargs):
            response = super().complete(role, prompt, **kwargs)
            if role == "planner" and json.loads(prompt)["artifact"] == "proposal":
                response.text = json.dumps({"content":
                    "# Proposal\n\n## Why\nActualizar salida del cliente sintético.\n\n"
                    "## What Changes\n- Cambiar VALUE a 2.\n\n## Capabilities\n\n"
                    "### New Capabilities\n- `client-value`: salida comprobable.\n\n"
                    "### Modified Capabilities\n\n## Impact\nSolo src/value.py.\n"})
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
    engine.test_runner = lambda root, *_args: {
        "passed": (root / "src/value.py").read_bytes() == b"VALUE = 2\n",
        "evidence": ["Comprobación determinista del cliente sintético: VALUE = 2"],
    }
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
