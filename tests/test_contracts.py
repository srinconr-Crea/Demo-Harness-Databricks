import json
from decimal import Decimal
from pathlib import Path

import pytest
import harness.contracts as contracts
from harness.contracts import (
    AgentCallContract,
    ClientProfile,
    RunAttempt,
    RunContract,
    Story,
    estimate_cost,
    load_client_profile,
    parse_agent_output,
    parse_ratio_story,
)


def valid_story():
    return {
        "id": "NP-001",
        "title": "Margen sobre costo en Silver comercial",
        "architecture": "Silver comercial en notebook existente",
        "source_target": "fact_ventas_cabecera -> misma tabla Silver",
        "business_rules": "margen_bruto / costo_total; NULL si costo es cero o nulo",
        "nonfunctional": "No modificar jobs ni datos actuales",
        "validation": "Probar costo positivo, cero y nulo",
    }


def test_two_field_story_request_rejects_blank_input():
    assert contracts.StoryRequest(hu=" HU-42 ", description=" Añadir un reporte ").hu == "HU-42"
    with pytest.raises(ValueError):
        contracts.StoryRequest(hu=" ", description="Añadir un reporte")
    with pytest.raises(ValueError):
        contracts.StoryRequest(hu="HU-42", description=" ")


def test_new_attempt_tracks_review_stage_and_legacy_run_remains_readable():
    approval = contracts.RunApproval(kind="plan", revision=2, sha256="a" * 64, actor="ana@example.com")
    event = contracts.RunEvent(seq=1, stage="awaiting_plan_review", kind="approval", revision=2)
    attempt = RunAttempt(
        attempt_id="attempt-one", state="awaiting_plan_review", stage="awaiting_plan_review",
        revision=2, base_sha="b" * 40, checkpoint_id="checkpoint-one",
        approvals=[approval], timeline=[event],
    )
    assert attempt.approvals[0].sha256 == "a" * 64
    assert attempt.timeline[0].seq == 1
    legacy = RunContract.model_validate({
        "schema_version": 3, "run_id": "legacy-run", "story_id": "NP-001",
        "story": valid_story(), "state": "complete", "attempts": [],
    })
    assert legacy.schema_version == 3
    assert isinstance(legacy.story, Story)
    with pytest.raises(ValueError):
        contracts.RunApproval(kind="diff", revision=1, sha256="short", actor="ana@example.com")


def test_story_requires_all_five_manual_sections():
    data = valid_story()
    data["validation"] = " "
    with pytest.raises(ValueError):
        Story.model_validate(data)


def test_profile_restricts_path_and_branch():
    profile = ClientProfile(
        repository="srinconr-Crea/Naturapet_DLH",
        base_branch="develop",
        allowed_paths=["notebooks/comercial/silver/"],
        openspec_root="openspec",
    )
    assert profile.allows("notebooks/comercial/silver/04_business_derivations.ipynb")
    assert not profile.allows("notebooks/comercial/silverish/other.ipynb")
    assert not profile.allows(".github/workflows/databricks-cicd.yml")
    assert profile.allows_openspec("openspec/config.yaml")
    assert not profile.allows_openspec("openspec/../.github/workflows/x.yml")
    assert not profile.allows_openspec("notebooks/a.ipynb")
    assert profile.feature_branch(Story.model_validate(valid_story())) == "feature/np-001-margen-sobre-costo-en-silver-comercial"


def test_cost_uses_independent_input_and_output_rates():
    assert estimate_cost(1000, 200, Decimal("0.000001"), Decimal("0.000005")) == Decimal("0.002000")


def test_cost_missing_usage_stays_unknown():
    assert estimate_cost(None, 200, Decimal("0.001"), Decimal("0.005")) is None


def test_ratio_story_is_derived_from_hu_not_client_profile():
    profile = ClientProfile(
        repository="srinconr-Crea/Naturapet_DLH", base_branch="develop",
        allowed_paths=["notebooks/comercial/silver/"],
        openspec_root="openspec",
        strategy={"kind": "silver_safe_ratio", "notebook": "notebooks/comercial/silver/04_business_derivations.ipynb", "table": "fact_ventas_cabecera", "anchor_column": "margen_pct", "allowed_source_columns": ["margen_bruto", "costo_total", "base_neta_sin_iva"]},
    )
    data = valid_story()
    data["business_rules"] = "margen_sobre_costo_pct = margen_bruto / costo_total; NULL si costo es cero o nulo"
    spec = parse_ratio_story(Story.model_validate(data), profile)
    assert (spec.output_column, spec.numerator, spec.denominator) == ("margen_sobre_costo_pct", "margen_bruto", "costo_total")


def test_ratio_story_rejects_columns_not_allowed_by_profile():
    profile = ClientProfile(repository="o/r", base_branch="develop", allowed_paths=["notebooks/"], openspec_root="openspec", strategy={"kind": "silver_safe_ratio", "notebook": "notebooks/a.ipynb", "table": "fact_ventas_cabecera", "anchor_column": "margen_pct", "allowed_source_columns": ["margen_bruto", "costo_total"]})
    data = valid_story()
    data["business_rules"] = "otra_pct = secreto / costo_total"
    with pytest.raises(ValueError, match="permitidas"):
        parse_ratio_story(Story.model_validate(data), profile)


def test_client_profile_selection_cannot_escape_config_directory(tmp_path):
    (tmp_path / "naturapet.yaml").write_text("repository: o/r\nbase_branch: develop\nallowed_paths: [notebooks/]\nopenspec_root: openspec\n", encoding="utf-8")
    assert load_client_profile(tmp_path, "naturapet").repository == "o/r"
    with pytest.raises(ValueError):
        load_client_profile(tmp_path, "../outside")


def test_profile_requires_standard_openspec_root():
    with pytest.raises(ValueError):
        ClientProfile(repository="o/r", base_branch="develop", allowed_paths=["notebooks/"])
    with pytest.raises(ValueError):
        ClientProfile(repository="o/r", base_branch="develop", allowed_paths=["notebooks/"], openspec_root="../other")


def test_naturapet_profile_enables_general_changes_and_required_validation():
    config_dir = Path(__file__).resolve().parents[1] / "src" / "agents" / "harness" / "config" / "clients"
    profile = load_client_profile(config_dir, "naturapet")
    from harness.validation import validation_plan
    assert profile.strategy is None
    assert profile.repository_policy.scope == 'repository'
    for path in ['src/common/config.py', 'notebooks/finanzas/gold/one.ipynb',
                 'conf/environments/dev.yml', 'resources/jobs/one.job.yml', 'README.md']:
        assert profile.allows_code(path)
    for path in ['.agents/skills/one/SKILL.md', '.github/workflows/deploy.yml',
                 'openspec/config.yaml', 'AGENTS.md', '.env', 'private/value.py', 'data/raw.json']:
        assert not profile.allows_code(path)
    code = validation_plan(profile, ['src/common/config.py'])
    assert code['requires_job'] and code['test_paths'] == ['tests']
    assert any(check['adapter'] == 'pytest_sandbox' for check in code['checks'])
    bundle = validation_plan(profile, ['resources/jobs/one.job.yml'])
    assert bundle['bundle_target'] == 'dev' and bundle['requires_job']
    assert any(check['adapter'] == 'databricks_bundle_validate' for check in bundle['checks'])
    assert not validation_plan(profile, ['README.md'])['requires_job']


def test_attempt_preserves_result_and_publication_for_historical_join():
    attempt = RunAttempt(
        attempt_id="attempt-one", state="complete", changed_files=["notebooks/one.ipynb"],
        result={"pr_url": "https://github.com/o/r/pull/1"},
        publication={"stage": "pr_created", "branch": "feature/one"},
    )
    assert attempt.model_dump()["changed_files"] == ["notebooks/one.ipynb"]
    assert attempt.publication["stage"] == "pr_created"
    assert attempt.openspec.change_id is None


def test_agent_call_contract_exposes_input_output_and_request_join():
    call = AgentCallContract(
        call_id="call-one", run_id="run-one", attempt_id="attempt-one", story_id="NP-001",
        role="analyst", model="endpoint", status="complete", input_text='{"story":"NP-001"}',
        output_text='{"valid":true}', parsed_output={"valid": True},
        client_request_id="call-one", started_at="2026-09-28T19:00:00Z",
        completed_at="2026-09-28T19:00:01Z", pricing_source="configured",
    )
    assert call.client_request_id == call.call_id
    assert call.input_text and call.output_text and call.parsed_output["valid"]


def test_agent_call_joins_stage_revision_and_approved_hash_without_fabricated_cost():
    call = AgentCallContract(
        call_id="call-2", run_id="run-1", attempt_id="attempt-1", story_id="HU-1",
        role="developer", model="databricks-claude-sonnet-5", pricing_source="configured",
        stage="applying", revision=3, approved_sha256="a" * 64,
    )
    assert call.estimated_cost_usd is None
    assert (call.run_id, call.attempt_id, call.stage, call.revision, call.approved_sha256) == (
        "run-1", "attempt-1", "applying", 3, "a" * 64,
    )
    historical = AgentCallContract.model_validate({
        "schema_version": 2, "call_id": "old", "run_id": "run-1",
        "attempt_id": "attempt-1", "story_id": "HU-1", "role": "planner",
        "model": "databricks-claude-sonnet-5", "pricing_source": "configured",
    })
    assert historical.stage is None and historical.approved_sha256 is None


def test_agent_output_schema_rejects_wrong_role_fields():
    assert parse_agent_output("analyst", '{"valid":true,"notes":"ok"}')["valid"] is True
    with pytest.raises(ValueError):
        parse_agent_output("verifier", '{"valid":true}')


def test_planner_output_requires_bounded_manifest():
    valid = json.dumps({"content": "# Proposal\n\n## Why\nNeed a change.", "strategy": "silver_safe_ratio", "expression": "safe_divide(F.col('a'), F.col('b'))", "code_path": "notebooks/a.ipynb"})
    parsed = parse_agent_output("planner", valid)
    assert parsed["strategy"] == "silver_safe_ratio"
    with pytest.raises(ValueError):
        parse_agent_output("planner", '{"content":"text","code_path":"notebooks/a.ipynb"}')
