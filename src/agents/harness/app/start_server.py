"""FastAPI entry point for the single manual HU interface."""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from databricks.sdk import WorkspaceClient
from harness.contracts import AgentCallContract, Story, load_client_profile
from harness.github import GitHubAppClient
from harness.models import ModelClient, load_model_config
from harness.sandbox import verify_safe_ratio
from harness.store import LocalRunStore, VolumeRunStore
from harness.webapp import create_app
from harness.workflow import run_story

PROFILE = load_client_profile(ROOT / "config" / "clients", os.environ.get("HARNESS_CLIENT_PROFILE", "naturapet"))
ROUTING, PRICES, PRICING_SOURCE = load_model_config(ROOT / "config" / "defaults" / "models.yaml")
run_directory = os.environ.get("RUN_STORE_DIR")
store = VolumeRunStore(WorkspaceClient().files, run_directory) if run_directory else LocalRunStore(ROOT / ".runs")


def execute_story(story: Story, run_id: str, attempt_id: str) -> dict:
    if PROFILE.github_app_id is None or PROFILE.github_installation_id is None:
        raise ValueError("El perfil no configura la GitHub App")
    private_key = os.environ["GITHUB_APP_PRIVATE_KEY"].replace("\\n", "\n")
    github = GitHubAppClient(
        PROFILE.github_app_id,
        PROFILE.github_installation_id,
        private_key,
        repository=PROFILE.repository,
        base_branch=PROFILE.base_branch,
    )
    workspace = WorkspaceClient()

    def save_call(role, response) -> None:
        call_id = uuid.uuid4().hex
        record = AgentCallContract(
            call_id=call_id, run_id=run_id, attempt_id=attempt_id, story_id=story.id,
            role=role, model=response.model, response=response.text,
            completed_at=datetime.now(timezone.utc), input_tokens=response.input_tokens,
            output_tokens=response.output_tokens, estimated_cost_usd=response.cost_usd,
            pricing_source=PRICING_SOURCE,
        )
        store.save_agent_call(run_id, call_id, record.model_dump(mode="json"))

    models = ModelClient(workspace.api_client, ROUTING, PRICES, on_call=save_call)
    report = run_story(story, PROFILE, github, models, lambda spec: verify_safe_ratio(workspace.api_client, os.environ["HARNESS_WAREHOUSE_ID"], spec))
    return asdict(report)


app = create_app(store, execute_story, PROFILE)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
