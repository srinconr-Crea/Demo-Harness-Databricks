import json
from decimal import Decimal
from pathlib import Path

import pytest
from harness.contracts import AgentCallContract, ClientProfile, Story, load_profile
from harness.models import ModelClient
from harness.store import LocalRunStore
from harness.webapp import CancelledRun
from harness.workflow import run_story
from test_notebook_edit import fixture_notebook
from test_openspec import FakePlanner


class FakeGitHub:
    def __init__(self):
        self.published = False

    def base_sha(self, branch):
        assert branch == "develop"
        return "abc123"

    def read_file(self, path, *, ref):
        assert ref == "abc123"
        return fixture_notebook(), "file-sha"

    def read_openspec_files(self, _base_sha):
        return {}

    def create_feature_pr(self, *args, on_progress=None):
        self.published = True
        self.files = args[-1]
        if on_progress:
            on_progress("pr_created", pr_url="https://github.com/srinconr-Crea/Naturapet_DLH/pull/999")
        return "https://github.com/srinconr-Crea/Naturapet_DLH/pull/999"


class FakeModel:
    def __init__(self, verifier_ok=True):
        self.verifier_ok = verifier_ok
        self.calls = []

    def complete(self, role, prompt, **kwargs):
        self.calls.append(role)
        if role == "planner":
            return FakePlanner(json.loads(prompt)["expected_expression"]).complete(role, prompt, **kwargs)
        elif role == "developer":
            text = json.dumps({"expression": json.loads(prompt)["expected_expression"]})
        else:
            text = json.dumps({"approved": self.verifier_ok, "notes": "Verificado"})
        return type("Response", (), {"text": text, "cost_usd": None})()


def story():
    return Story(
        id="NP-001", title="Margen sobre costo en Silver comercial",
        architecture="Silver comercial", source_target="fact_ventas_cabecera",
        business_rules="margen_sobre_costo_pct = margen_bruto / costo_total; NULL para costo 0 o NULL",
        nonfunctional="Sin cambios a jobs", validation="Caso positivo, cero y NULL",
    )


def profile():
    return ClientProfile(repository="srinconr-Crea/Naturapet_DLH", base_branch="develop", allowed_paths=["notebooks/comercial/silver/"], openspec_root="openspec", strategy={"kind": "silver_safe_ratio", "notebook": "notebooks/comercial/silver/04_business_derivations.ipynb", "table": "fact_ventas_cabecera", "anchor_column": "margen_pct", "allowed_source_columns": ["margen_bruto", "costo_total", "base_neta_sin_iva"]})


def test_gate_blocks_publication_when_remote_sandbox_fails():
    github = FakeGitHub()
    with pytest.raises(ValueError, match="sandbox"):
        run_story(story(), profile(), github, FakeModel(), lambda source: False)
    assert not github.published


def test_success_routes_three_roles_and_opens_pr():
    github = FakeGitHub()
    models = FakeModel()
    report = run_story(story(), profile(), github, models, lambda source: True)
    assert github.published
    assert models.calls == ["planner"] * 4 + ["developer", "verifier"]
    assert report.pr_url.endswith("/999")
    assert "notebooks/comercial/silver/04_business_derivations.ipynb" in report.changed_files
    assert any(path.startswith("openspec/changes/archive/") for path in report.changed_files)


def test_second_story_uses_hu_formula_without_code_change():
    second = story().model_copy(update={"id": "NP-002", "title": "Costo sobre venta neta", "business_rules": "costo_sobre_venta_pct = costo_total / base_neta_sin_iva; NULL si venta neta es cero o NULL"})
    report = run_story(second, profile(), FakeGitHub(), FakeModel(), lambda spec: spec.output_column == "costo_sobre_venta_pct")
    assert "costo_sobre_venta_pct" in report.diff
    assert "margen_sobre_costo_pct" not in report.diff


def test_fenced_json_from_verifier_is_accepted():
    class FencedVerifier(FakeModel):
        def complete(self, role, prompt, **kwargs):
            response = super().complete(role, prompt, **kwargs)
            if role == "verifier":
                response.text = "```json\n" + response.text + "\n```"
            return response

    report = run_story(story(), profile(), FakeGitHub(), FencedVerifier(), lambda source: True)
    assert report.remote_check == "passed"


def test_verifier_cannot_override_deterministic_gate():
    github = FakeGitHub()
    with pytest.raises(ValueError, match="verificador"):
        run_story(story(), profile(), github, FakeModel(verifier_ok=False), lambda source: True)
    assert not github.published


def test_cancel_before_publication_preserves_changed_file_without_creating_pr():
    class Control:
        def __init__(self):
            self.changed = []
            self.progress = []

        def check_cancel(self):
            return None

        def record_changed_files(self, files):
            self.changed = files

        def record_event(self, stage, status, **details):
            self.progress.append((stage, status))

        def record_openspec_artifact(self, path, content, sha256):
            self.progress.append(("openspec_artifact", path))

        def record_openspec(self, **details):
            self.progress.append(("openspec", details))

        def begin_publication(self):
            raise CancelledRun()

        def record_publication(self, stage, **details):
            self.progress.append((stage, details))

    github = FakeGitHub()
    control = Control()
    with pytest.raises(CancelledRun):
        run_story(story(), profile(), github, FakeModel(), lambda spec: True, control=control)
    assert "notebooks/comercial/silver/04_business_derivations.ipynb" in control.changed
    assert not github.published


def test_second_profile_isolated_by_yaml_and_uses_its_own_path():
    sample = load_profile(Path(__file__).parent / "fixtures" / "clients" / "independent.yaml")
    assert sample.repository == "example/independent-analytics"
    assert not sample.allows(profile().strategy.notebook)
    report = run_story(story(), sample, FakeGitHub(), FakeModel(), lambda spec: True)
    assert sample.strategy.notebook in report.changed_files
    assert profile().strategy.notebook not in report.changed_files


def test_synthetic_story_initializes_openspec_and_logs_sonnet_planning_costs(tmp_path: Path):
    class FoundationAPI:
        def __init__(self):
            self.roles = []

        def do(self, method, endpoint, body=None):
            assert method == "POST"
            prompt = body["messages"][-1]["content"]
            if "sonnet-5" in endpoint:
                role = "planner"
                expression = json.loads(prompt)["expected_expression"]
                output = FakePlanner(expression).complete(role, prompt).text
            elif "developer" in endpoint:
                role = "developer"
                output = json.dumps({"expression": json.loads(prompt)["expected_expression"]})
            else:
                role = "verifier"
                output = '{"approved": true}'
            self.roles.append(role)
            return {"choices": [{"message": {"content": output}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}

    api = FoundationAPI()
    store = LocalRunStore(tmp_path / "runs")
    sonnet = "databricks-claude-sonnet-5"
    prices = {endpoint: (Decimal("0.000003"), Decimal("0.000015")) for endpoint in (sonnet, "developer", "verifier")}
    models = ModelClient(api, {"planner": sonnet, "developer": "developer", "verifier": "verifier"}, prices, on_call=lambda role, call: store.save_agent_call("run123", call.call_id, AgentCallContract(call_id=call.call_id, run_id="run123", attempt_id="attempt123", story_id="NP-001", role=role, model=call.model, status=call.status, input_text=call.input_text, output_text=call.output_text, input_sha256=call.input_sha256, output_sha256=call.output_sha256, input_tokens=call.input_tokens, output_tokens=call.output_tokens, estimated_cost_usd=call.cost_usd, pricing_source="test").model_dump(mode="json")))
    github = FakeGitHub()
    report = run_story(story(), profile(), github, models, lambda spec: True, attempt_id="attempt123")
    assert api.roles == ["planner"] * 4 + ["developer", "verifier"]
    assert "openspec/config.yaml" in github.files
    assert any(path.startswith("openspec/changes/archive/") for path in github.files)
    assert report.model_cost_usd == Decimal("0.000630")
    saved = [json.loads(path.read_text(encoding="utf-8")) for path in (tmp_path / "runs" / "agent_calls").glob("*.json")]
    assert len(saved) == 6
    assert len([item for item in saved if item["role"] == "planner" and item["model"] == sonnet and item["estimated_cost_usd"] == "0.000105"]) == 4


def test_retry_uses_distinct_client_change_and_feature_branch():
    first = FakeGitHub()
    second = FakeGitHub()
    first_report = run_story(story(), profile(), first, FakeModel(), lambda spec: True, attempt_id="a" * 32)
    second_report = run_story(story(), profile(), second, FakeModel(), lambda spec: True, attempt_id="b" * 32)
    assert first_report.branch != second_report.branch
    assert any("aaaaaaaaaaaa" in path for path in first.files if path.startswith("openspec/changes/archive/"))
    assert any("bbbbbbbbbbbb" in path for path in second.files if path.startswith("openspec/changes/archive/"))
