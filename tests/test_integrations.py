from decimal import Decimal

import pytest
from harness.github import GitHubAppClient
from harness.models import (
    ModelClient,
    load_model_config,
    load_runtime_config,
    sanitize_log_value,
)


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


def test_model_call_id_is_sent_before_invocation_and_input_output_are_recorded():
    saved = []
    api = FakeWorkspaceAPI({"choices": [{"message": {"content": '{"valid":true}'}}], "usage": {"prompt_tokens": 2, "completion_tokens": 3}})
    client = ModelClient(api, {"analyst": "endpoint"}, {"endpoint": (Decimal("0.1"), Decimal("0.2"))}, on_call=lambda role, call: saved.append(call))
    client.complete("analyst", "Analiza", call_id="call-123", usage_context={"run_id": "run-1"})
    body = api.calls[0][2]
    assert body["client_request_id"] == "call-123"
    assert body["usage_context"]["run_id"] == "run-1"
    assert saved[0].call_id == "call-123"
    assert "Analiza" in saved[0].input_text
    assert saved[0].output_text == '{"valid":true}'
    assert saved[0].status == "complete"
    assert saved[0].input_sha256 and saved[0].output_sha256


def test_model_failure_is_logged_without_fabricating_cost():
    class FailingAPI:
        def do(self, *_args, **_kwargs):
            raise RuntimeError("endpoint unavailable")

    saved = []
    client = ModelClient(FailingAPI(), {"analyst": "endpoint"}, {}, on_call=lambda role, call: saved.append(call))
    with pytest.raises(RuntimeError, match="endpoint unavailable"):
        client.complete("analyst", "Analiza", call_id="call-123")
    assert saved[0].status == "failed"
    assert saved[0].cost_usd is None
    assert saved[0].output_text is None


def test_empty_model_response_is_logged_as_failure():
    saved = []
    client = ModelClient(FakeWorkspaceAPI({"choices": []}), {"analyst": "endpoint"}, {}, on_call=lambda role, call: saved.append(call))
    with pytest.raises(ValueError, match="Respuesta vacía"):
        client.complete("analyst", "Analiza")
    assert len(saved) == 1 and saved[0].status == "failed"
    assert saved[0].cost_usd is None


def test_nested_parsed_output_is_redacted_before_persistence():
    value = {"notes": ["dapi12345678901234567890"]}
    assert sanitize_log_value(value, 1000) == {"notes": ["[REDACTED_TOKEN]"]}


def test_model_config_is_keyed_by_endpoint_not_hardcoded_role_prices(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("routing:\n  analyst: custom-a\n  developer: custom-a\n  verifier: custom-b\npricing:\n  source: estimated\n  endpoints:\n    custom-a: {input_usd_per_token: 0.1, output_usd_per_token: 0.2}\n    custom-b: {input_usd_per_token: 0.3, output_usd_per_token: 0.4}\n", encoding="utf-8")
    routing, prices, source = load_model_config(path)
    assert routing["developer"] == "custom-a"
    assert prices["custom-b"] == (Decimal("0.3"), Decimal("0.4"))
    assert source == "estimated"


def test_runtime_logging_limits_are_loaded_from_yaml(tmp_path):
    path = tmp_path / "runtime.yaml"
    path.write_text("logging:\n  max_text_chars: 1200\n", encoding="utf-8")
    assert load_runtime_config(path)["logging"]["max_text_chars"] == 1200


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


@pytest.mark.parametrize(("runs", "expected"), [
    ([], "pending"),
    ([{"status": "in_progress"}], "pending"),
    ([{"status": "completed", "conclusion": "success"}], "passed"),
    ([{"status": "completed", "conclusion": "failure"}], "failed"),
])
def test_pr_check_snapshot_never_calls_missing_checks_passed(runs, expected):
    class Checks(GitHubAppClient):
        def _checks_request(self, path):
            assert "/check-runs" in path
            return {"check_runs": runs}

    client = Checks(1, 2, "unused", repository="o/r", base_branch="develop")
    assert client.pr_check_status("o/r", "feature/test") == expected


def test_check_read_uses_separate_narrow_token():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"check_runs": []}

    class Http:
        def get(self, path, headers):
            assert headers["Authorization"] == "Bearer checks-token"
            return Response()

    class Checks(GitHubAppClient):
        def _new_installation_token(self, permissions):
            assert permissions == {"checks": "read"}
            return "checks-token"

    client = Checks(1, 2, "unused", repository="o/r", base_branch="develop", http=Http())
    assert client.pr_check_status("o/r", "feature/test") == "pending"
