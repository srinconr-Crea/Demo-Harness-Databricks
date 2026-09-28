import json
from pathlib import Path

import pytest
from harness.contracts import ClientProfile, Story, load_profile
from harness.webapp import CancelledRun
from harness.workflow import run_story
from test_notebook_edit import fixture_notebook


class FakeGitHub:
    def __init__(self):
        self.published = False

    def base_sha(self, branch):
        assert branch == "develop"
        return "abc123"

    def read_file(self, path, *, ref):
        assert ref == "abc123"
        return fixture_notebook(), "file-sha"

    def create_feature_pr(self, *args, on_progress=None):
        self.published = True
        if on_progress:
            on_progress("pr_created", pr_url="https://github.com/srinconr-Crea/Naturapet_DLH/pull/999")
        return "https://github.com/srinconr-Crea/Naturapet_DLH/pull/999"


class FakeModel:
    def __init__(self, verifier_ok=True):
        self.verifier_ok = verifier_ok
        self.calls = []

    def complete(self, role, prompt):
        self.calls.append(role)
        if role == "analyst":
            text = '{"valid": true, "notes": "Medida aditiva"}'
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
    return ClientProfile(repository="srinconr-Crea/Naturapet_DLH", base_branch="develop", allowed_paths=["notebooks/comercial/silver/"], strategy={"kind": "silver_safe_ratio", "notebook": "notebooks/comercial/silver/04_business_derivations.ipynb", "table": "fact_ventas_cabecera", "anchor_column": "margen_pct", "allowed_source_columns": ["margen_bruto", "costo_total", "base_neta_sin_iva"]})


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
    assert models.calls == ["analyst", "developer", "verifier"]
    assert report.pr_url.endswith("/999")
    assert report.changed_files == ["notebooks/comercial/silver/04_business_derivations.ipynb"]


def test_second_story_uses_hu_formula_without_code_change():
    second = story().model_copy(update={"id": "NP-002", "title": "Costo sobre venta neta", "business_rules": "costo_sobre_venta_pct = costo_total / base_neta_sin_iva; NULL si venta neta es cero o NULL"})
    report = run_story(second, profile(), FakeGitHub(), FakeModel(), lambda spec: spec.output_column == "costo_sobre_venta_pct")
    assert "costo_sobre_venta_pct" in report.diff
    assert "margen_sobre_costo_pct" not in report.diff


def test_fenced_json_from_verifier_is_accepted():
    class FencedVerifier(FakeModel):
        def complete(self, role, prompt):
            response = super().complete(role, prompt)
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

        def begin_publication(self):
            raise CancelledRun()

        def record_publication(self, stage, **details):
            self.progress.append((stage, details))

    github = FakeGitHub()
    control = Control()
    with pytest.raises(CancelledRun):
        run_story(story(), profile(), github, FakeModel(), lambda spec: True, control=control)
    assert control.changed == ["notebooks/comercial/silver/04_business_derivations.ipynb"]
    assert not github.published


def test_second_profile_isolated_by_yaml_and_uses_its_own_path():
    sample = load_profile(Path(__file__).parent / "fixtures" / "clients" / "independent.yaml")
    assert sample.repository == "example/independent-analytics"
    assert not sample.allows(profile().strategy.notebook)
    report = run_story(story(), sample, FakeGitHub(), FakeModel(), lambda spec: True)
    assert report.changed_files == [sample.strategy.notebook]
    assert profile().strategy.notebook not in report.changed_files
