import json
from decimal import Decimal
from pathlib import Path

import pytest
from harness.contracts import (
    AgentCallContract,
    ClientProfile,
    RunAttempt,
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


def test_naturapet_profile_accepts_second_story_without_hu_specific_yaml():
    config_dir = Path(__file__).resolve().parents[1] / "src" / "agents" / "harness" / "config" / "clients"
    profile = load_client_profile(config_dir, "naturapet")
    data = valid_story()
    data.update(id="NP-002", title="Costo sobre venta neta en Silver comercial", business_rules="costo_sobre_venta_pct = costo_total / base_neta_sin_iva; NULL cuando la venta neta sea cero o NULL")
    spec = parse_ratio_story(Story.model_validate(data), profile)
    assert spec.output_column == "costo_sobre_venta_pct"
    assert profile.allows(profile.strategy.notebook)


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
