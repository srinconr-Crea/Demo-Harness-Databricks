"""FastAPI entry point for the single manual HU interface."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from databricks.sdk import WorkspaceClient
from harness.contracts import (
    AgentCallContract,
    Story,
    load_client_profile,
    parse_agent_output,
)
from harness.github import GitHubAppClient
from harness.models import (
    ModelClient,
    load_model_config,
    load_runtime_config,
    sanitize_log_value,
)
from harness.sandbox import verify_safe_ratio
from harness.store import LocalRunStore, VolumeRunStore
from harness.webapp import create_app
from harness.workflow import run_story

PROFILE = load_client_profile(ROOT / "config" / "clients", os.environ["HARNESS_CLIENT_PROFILE"])
ROUTING, PRICES, PRICING_SOURCE = load_model_config(ROOT / "config" / "defaults" / "models.yaml")
RUNTIME = load_runtime_config(ROOT / "config" / "defaults" / "runtime.yaml")
AGENT_CONFIG = yaml.safe_load((ROOT / "config" / "defaults" / "agents.yaml").read_text(encoding="utf-8"))
run_directory = os.environ.get("RUN_STORE_DIR")
store = VolumeRunStore(WorkspaceClient().files, run_directory) if run_directory else LocalRunStore(ROOT / ".runs")


def execute_story(story: Story, run_id: str, attempt_id: str, control) -> dict:
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
        try:
            parsed_output = parse_agent_output(role, response.text) if response.status == "complete" else None
        except ValueError:
            parsed_output = None
        record = AgentCallContract(
            call_id=response.call_id, run_id=run_id, attempt_id=attempt_id, story_id=story.id,
            role=role, model=response.model, status=response.status,
            input_text=response.input_text, output_text=response.output_text,
            input_sha256=response.input_sha256, output_sha256=response.output_sha256,
            parsed_output=sanitize_log_value(parsed_output, RUNTIME["logging"]["max_text_chars"]), client_request_id=response.call_id,
            databricks_request_id=response.databricks_request_id,
            response=response.output_text, started_at=response.started_at,
            completed_at=response.completed_at, duration_ms=response.duration_ms, error=response.error,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens, estimated_cost_usd=response.cost_usd,
            pricing_source=PRICING_SOURCE,
        )
        store.save_agent_call(run_id, response.call_id, record.model_dump(mode="json"))

    models = ModelClient(
        workspace.api_client, ROUTING, PRICES, on_call=save_call,
        log_text_limit=RUNTIME["logging"]["max_text_chars"],
        system_prompt=AGENT_CONFIG["system_prompt"], max_tokens=AGENT_CONFIG["max_tokens"],
        usage_context={"run_id": run_id, "attempt_id": attempt_id, "story_id": story.id, "client_profile": PROFILE.name},
    )
    report = run_story(story, PROFILE, github, models, lambda spec: verify_safe_ratio(workspace.api_client, os.environ["HARNESS_WAREHOUSE_ID"], spec), control=control, agent_config=AGENT_CONFIG, attempt_id=attempt_id)
    return asdict(report)


def stop_app_as_user(user_token: str) -> None:
    host = WorkspaceClient().config.host
    WorkspaceClient(host=host, token=user_token).apps.stop(name=os.environ["HARNESS_APP_NAME"])


app = create_app(store, execute_story, PROFILE, stopper=stop_app_as_user, app_name=os.environ.get("HARNESS_APP_NAME"))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
