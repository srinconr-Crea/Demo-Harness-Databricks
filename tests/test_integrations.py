from decimal import Decimal

import pytest
from harness.github import GitHubAppClient
from harness.models import ModelClient


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


def test_github_rejects_unapproved_repository_and_base_branch():
    client = GitHubAppClient(5075619, 164865183, "not-a-real-key", repository="srinconr-Crea/Naturapet_DLH")
    with pytest.raises(ValueError):
        client.create_feature_pr("other/repo", "feature/np-001", "develop", "title", "body", "sha", {})
    with pytest.raises(ValueError):
        client.create_feature_pr("srinconr-Crea/Naturapet_DLH", "feature/np-001", "main", "title", "body", "sha", {})
