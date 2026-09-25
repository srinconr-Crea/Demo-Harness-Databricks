"""FastAPI entry point for the single manual HU interface."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
import yaml
from databricks.sdk import WorkspaceClient
from harness.contracts import Story, load_profile
from harness.github import GitHubAppClient
from harness.models import ModelClient
from harness.sandbox import verify_silver_rule
from harness.store import VolumeRunStore
from harness.webapp import create_app
from harness.workflow import run_story

PROFILE = load_profile(ROOT / "config" / "clients" / "naturapet.yaml")
MODELS = yaml.safe_load((ROOT / "config" / "defaults" / "models.yaml").read_text(encoding="utf-8"))


def execute_story(story: Story) -> dict:
    private_key = os.environ["GITHUB_APP_PRIVATE_KEY"].replace("\\n", "\n")
    github = GitHubAppClient(
        int(os.environ["GITHUB_APP_ID"]),
        int(os.environ["GITHUB_INSTALLATION_ID"]),
        private_key,
        repository=PROFILE.repository,
    )
    workspace = WorkspaceClient()
    pricing = MODELS["pricing"]
    rates = {
        MODELS["analyst"]: (
            Decimal(str(pricing["sonnet_5_input_usd_per_token"])),
            Decimal(str(pricing["sonnet_5_output_usd_per_token"])),
        ),
        MODELS["verifier"]: (
            Decimal(str(pricing["haiku_4_5_input_usd_per_token"])),
            Decimal(str(pricing["haiku_4_5_output_usd_per_token"])),
        ),
    }
    models = ModelClient(workspace.api_client, {role: MODELS[role] for role in ("analyst", "developer", "verifier")}, rates)
    report = run_story(story, PROFILE, github, models, lambda source: verify_silver_rule(workspace.api_client, os.environ["HARNESS_WAREHOUSE_ID"]))
    return asdict(report)


run_directory = os.environ.get("RUN_STORE_DIR")
store = VolumeRunStore(WorkspaceClient().files, run_directory) if run_directory else ROOT / ".runs"
app = create_app(store, execute_story)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
