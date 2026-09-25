import json

import pytest
from harness.contracts import ClientProfile, Story
from harness.workflow import run_story
from test_notebook_edit import fixture_notebook


class FakeGitHub:
    def __init__(self):
        self.published = False

    def base_sha(self, branch):
        assert branch == "develop"
        return "abc123"

    def read_file(self, path, *, ref):
        assert ref == "develop"
        return fixture_notebook(), "file-sha"

    def create_feature_pr(self, *args):
        self.published = True
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
            text = '{"expression": "safe_divide(F.col(\'margen_bruto\'), F.col(\'costo_total\'))"}'
        else:
            text = json.dumps({"approved": self.verifier_ok, "notes": "Verificado"})
        return type("Response", (), {"text": text, "cost_usd": None})()


def story():
    return Story(
        id="NP-001", title="Margen sobre costo en Silver comercial",
        architecture="Silver comercial", source_target="fact_ventas_cabecera",
        business_rules="margen_bruto / costo_total; NULL para costo 0 o NULL",
        nonfunctional="Sin cambios a jobs", validation="Caso positivo, cero y NULL",
    )


def profile():
    return ClientProfile(repository="srinconr-Crea/Naturapet_DLH", base_branch="develop", allowed_paths=["notebooks/comercial/silver/"])


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
