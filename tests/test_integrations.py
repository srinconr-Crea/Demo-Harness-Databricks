from decimal import Decimal

import pytest
from harness.github import GitHubAppClient
from harness.models import ModelClient, load_model_config


class FakeWorkspaceAPI:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def do(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.response


def test_model_router_uses_foundation_endpoint_and_records_tokens():
    api = FakeWorkspaceAPI({"choices": [{"message": {"content": "{\"ok\":true}"}}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}})
    client = ModelClient(api, {"analyst": "databricks-claude-sonnet-5"}, {"databricks-claude-sonnet-5": (Decimal("0.000003"), Decimal("0.000015"))})
    response = client.complete("analyst", "Analiza la HU")
    assert response.text == '{"ok":true}'
    assert response.cost_usd == Decimal("0.000600")
    assert api.calls[0][1] == "/serving-endpoints/databricks-claude-sonnet-5/invocations"
    assert "temperature" not in api.calls[0][2]


def test_model_usage_missing_is_not_zero():
    api = FakeWorkspaceAPI({"choices": [{"message": {"content": "ok"}}]})
    client = ModelClient(api, {"verifier": "databricks-claude-haiku-4-5"}, {})
    assert client.complete("verifier", "Revisa").cost_usd is None


def test_model_call_sink_receives_role_response_usage_and_cost():
    saved = []
    api = FakeWorkspaceAPI({"choices": [{"message": {"content": '{"valid": true}'}}], "usage": {"prompt_tokens": 2, "completion_tokens": 3}})
    client = ModelClient(api, {"analyst": "approved-model"}, {"approved-model": (Decimal("0.1"), Decimal("0.2"))}, on_call=lambda role, call: saved.append((role, call)))
    client.complete("analyst", "Analiza")
    assert saved[0][0] == "analyst"
    assert saved[0][1].text == '{"valid": true}'
    assert saved[0][1].input_tokens == 2
    assert saved[0][1].cost_usd == Decimal("0.8")


def test_model_config_is_keyed_by_endpoint_not_hardcoded_role_prices(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("routing:\n  analyst: custom-a\n  developer: custom-a\n  verifier: custom-b\npricing:\n  source: estimated\n  endpoints:\n    custom-a: {input_usd_per_token: 0.1, output_usd_per_token: 0.2}\n    custom-b: {input_usd_per_token: 0.3, output_usd_per_token: 0.4}\n", encoding="utf-8")
    routing, prices, source = load_model_config(path)
    assert routing["developer"] == "custom-a"
    assert prices["custom-b"] == (Decimal("0.3"), Decimal("0.4"))
    assert source == "estimated"


def test_model_normalizes_text_blocks_from_foundation_api():
    api = FakeWorkspaceAPI({"choices": [{"message": {"content": [
        {"type": "text", "text": '{"valid": true}'},
    ]}}], "usage": {"prompt_tokens": 1, "completion_tokens": 2}})
    client = ModelClient(api, {"analyst": "databricks-claude-sonnet-5"}, {})
    assert client.complete("analyst", "Analiza").text == '{"valid": true}'


def test_github_rejects_unapproved_repository_and_base_branch():
    client = GitHubAppClient(5075619, 164865183, "not-a-real-key", repository="srinconr-Crea/Naturapet_DLH", base_branch="develop")
    with pytest.raises(ValueError):
        client.create_feature_pr("other/repo", "feature/np-001", "develop", "title", "body", "sha", {})
    with pytest.raises(ValueError):
        client.create_feature_pr("srinconr-Crea/Naturapet_DLH", "feature/np-001", "main", "title", "body", "sha", {})


def test_existing_pr_only_reused_when_content_matches():
    class ExistingPR(GitHubAppClient):
        def _request(self, method, path, **kwargs):
            assert method == "GET"
            if path.endswith("/pulls"):
                return [{"html_url": "https://github.com/srinconr-Crea/Naturapet_DLH/pull/123"}]
            return {"merge_base_commit": {"sha": "base-sha"}, "files": [{"filename": "notebooks/comercial/silver/test.ipynb", "status": "modified"}]}

        def read_file(self, path, *, ref):
            assert ref == "feature/np-001"
            return "unexpected content", "sha"

    client = ExistingPR(1, 2, "unused", repository="srinconr-Crea/Naturapet_DLH", base_branch="develop")
    with pytest.raises(ValueError, match="PR existente"):
        client.create_feature_pr(
            "srinconr-Crea/Naturapet_DLH", "feature/np-001", "develop", "title", "body", "base-sha",
            {"notebooks/comercial/silver/test.ipynb": ("validated content", "source-sha")},
        )


def test_existing_pr_with_extra_file_is_not_reused():
    class ExtraFilePR(GitHubAppClient):
        def _request(self, method, path, **kwargs):
            if path.endswith("/pulls"):
                return [{"html_url": "https://github.com/o/r/pull/1"}]
            return {"merge_base_commit": {"sha": "base-sha"}, "files": [{"filename": "notebooks/a.ipynb", "status": "modified"}, {"filename": ".github/workflows/x.yml", "status": "added"}]}

        def read_file(self, path, *, ref):
            return "validated content", "sha"

    client = ExtraFilePR(1, 2, "unused", repository="o/r", base_branch="develop")
    with pytest.raises(ValueError, match="archivos adicionales"):
        client.create_feature_pr("o/r", "feature/np-002", "develop", "title", "body", "base-sha", {"notebooks/a.ipynb": ("validated content", "sha")})
