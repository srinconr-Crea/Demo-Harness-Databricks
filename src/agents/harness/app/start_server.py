"""FastAPI entry point for the resumable OpenSpec conversation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import uvicorn
import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import ApiClient, Config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.client_config import load_selected_profile
from harness.contracts import (
    AgentCallContract,
    RatioSpec,
    parse_agent_output,
)
from harness.conversation import ConversationEngine
from harness.conversation_webapp import create_conversation_app
from harness.coordination import DeltaRunCoordinator, SqliteRunCoordinator
from harness.github import GitHubAppClient
from harness.models import (
    ModelClient,
    load_model_config,
    load_runtime_config,
    sanitize_log_value,
)
from harness.openspec import OpenSpecCLI
from harness.sandbox import verify_general_patch, verify_safe_ratio
from harness.sandbox_job import SandboxJobRunner
from harness.store import LocalRunStore, VolumeRunStore

PROFILE = load_selected_profile(ROOT)
ROUTING, PRICES, PRICING_SOURCE = load_model_config(ROOT / "config" / "defaults" / "models.yaml")
RUNTIME = load_runtime_config(ROOT / "config" / "defaults" / "runtime.yaml")
AGENT_CONFIG = yaml.safe_load((ROOT / "config" / "defaults" / "agents.yaml").read_text(encoding="utf-8"))
MODEL_CONFIG = yaml.safe_load((ROOT / 'config' / 'defaults' / 'models.yaml').read_text(encoding='utf-8'))
WORKSPACE = WorkspaceClient()
run_directory = os.environ.get("RUN_STORE_DIR")
STORE = VolumeRunStore(WORKSPACE.files, run_directory) if run_directory else LocalRunStore(ROOT / ".runs")
table = os.environ.get("HARNESS_RUN_STATE_TABLE")
COORDINATOR = (
    DeltaRunCoordinator(WORKSPACE.api_client, os.environ["HARNESS_WAREHOUSE_ID"], table)
    if table else SqliteRunCoordinator(ROOT / ".runs" / "state.db")
)
job_id = os.environ.get("HARNESS_SANDBOX_JOB_ID")
SANDBOX_JOB = (
    SandboxJobRunner(WORKSPACE.api_client, WORKSPACE.files, job_id=int(job_id),
                     volume_dir=os.environ["HARNESS_SANDBOX_DIR"])
    if job_id and os.environ.get("HARNESS_SANDBOX_DIR") else None
)


def github_factory():
    if PROFILE.github_app_id is None or PROFILE.github_installation_id is None:
        raise ValueError("El perfil no configura la GitHub App")
    private_key = os.environ["GITHUB_APP_PRIVATE_KEY"].replace("\\n", "\n")
    return GitHubAppClient(
        PROFILE.github_app_id, PROFILE.github_installation_id, private_key,
        repository=PROFILE.repository, base_branch=PROFILE.base_branch,
    )


def models_factory(run_id: str, attempt_id: str):
    record = STORE.load(run_id)
    story_id = record["story_id"]

    def save_call(role, response) -> None:
        try:
            parsed_output = parse_agent_output(role, response.text) if response.status == "complete" else None
        except ValueError:
            try:
                parsed_output = json.loads(response.text) if response.status == "complete" else None
            except json.JSONDecodeError:
                parsed_output = None
        contract = AgentCallContract(
            call_id=response.call_id, run_id=run_id, attempt_id=attempt_id,
            story_id=story_id, role=role, model=response.model, status=response.status,
            finish_reason=response.finish_reason, effective_max_tokens=response.effective_max_tokens,
            acceptance=response.acceptance, parent_call_id=response.parent_call_id,
            recovery_index=response.recovery_index, normalized_sha256=response.normalized_sha256,
            response_evidence_sha256=STORE.save_instruction_snapshot(run_id, attempt_id,
                {'kind': 'model_response', 'call_id': response.call_id,
                 'original': response.text, 'normalized': response.normalized_text}),
            stage=response.stage, revision=response.revision,
            approved_sha256=response.approved_sha256,
            instruction_provenance=response.instruction_provenance,
            context_provenance=response.context_provenance,
            profile_provenance=next(a for a in record['attempts'] if a['attempt_id'] == attempt_id).get('profile_provenance'),
            input_text=response.input_text, output_text=response.output_text,
            input_sha256=response.input_sha256, output_sha256=response.output_sha256,
            parsed_output=sanitize_log_value(parsed_output, RUNTIME["logging"]["max_text_chars"]),
            client_request_id=response.call_id, databricks_request_id=response.databricks_request_id,
            response=response.output_text, started_at=response.started_at,
            completed_at=response.completed_at, duration_ms=response.duration_ms,
            error=response.error, input_tokens=response.input_tokens,
            output_tokens=response.output_tokens, estimated_cost_usd=response.cost_usd,
            pricing_source=PRICING_SOURCE,
        )
        STORE.save_agent_call(run_id, response.call_id, contract.model_dump(mode="json"))

    client = ModelClient(
        WORKSPACE.api_client, ROUTING, PRICES, on_call=save_call,
        log_text_limit=RUNTIME["logging"]["max_text_chars"],
        system_prompt=AGENT_CONFIG["system_prompt"], max_tokens=AGENT_CONFIG["max_tokens"],
        role_max_tokens=AGENT_CONFIG.get('role_max_tokens'),
        endpoint_capabilities=MODEL_CONFIG.get('endpoint_capabilities'),
        usage_context={"run_id": run_id, "attempt_id": attempt_id,
                       "story_id": story_id, "client_profile": PROFILE.name},
    )
    # A separate SDK transport bounds only advisory calls. Storage retains the main client.
    config_values = WORKSPACE.config.as_dict()
    config_values.update(http_timeout_seconds=20, retry_timeout_seconds=1)
    client.advisory_api = ApiClient(Config(**config_values))
    return client


def run_tests(root, profile, paths, record, attempt):
    if profile.general_patch:
        return verify_general_patch(
            root, profile, paths, SANDBOX_JOB,
            run_id=record["run_id"], attempt_id=attempt["attempt_id"],
            revision=attempt["revision"],
        )
    spec = RatioSpec.model_validate(attempt["context"]["ratio_spec"])
    passed = verify_safe_ratio(WORKSPACE.api_client, os.environ["HARNESS_WAREHOUSE_ID"], spec)
    return {"passed": passed, "evidence": ["Tres filas SQL sintéticas: positivo, cero y NULL"]}


ENGINE = ConversationEngine(
    PROFILE, STORE, COORDINATOR, github_factory, models_factory, OpenSpecCLI(), run_tests,
)
app = create_conversation_app(ENGINE, PROFILE)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
