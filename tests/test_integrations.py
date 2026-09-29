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


def test_four_planner_calls_use_sonnet_and_each_reaches_json_sink():
    saved = []
    api = FakeWorkspaceAPI({"choices": [{"message": {"content": '{"content":"valid artifact"}'}}], "usage": {"prompt_tokens": 2, "completion_tokens": 3}})
    model = "databricks-claude-sonnet-5"
    client = ModelClient(api, {"planner": model}, {model: (Decimal("0.1"), Decimal("0.2"))}, on_call=lambda role, call: saved.append((role, call)))
    for artifact in ("proposal", "specs", "design", "tasks"):
        client.complete("planner", artifact)
    assert len(saved) == 4
    assert all(role == "planner" and call.model == model and call.cost_usd == Decimal("0.8") for role, call in saved)
    assert all(path == "/serving-endpoints/databricks-claude-sonnet-5/invocations" for _method, path, _body in api.calls)


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
    path.write_text("routing:\n  planner: databricks-claude-sonnet-5\n  developer: custom-a\n  verifier: custom-b\npricing:\n  source: estimated\n  endpoints:\n    databricks-claude-sonnet-5: {input_usd_per_token: 0.1, output_usd_per_token: 0.2}\n    custom-a: {input_usd_per_token: 0.1, output_usd_per_token: 0.2}\n    custom-b: {input_usd_per_token: 0.3, output_usd_per_token: 0.4}\n", encoding="utf-8")
    routing, prices, source = load_model_config(path)
    assert routing["developer"] == "custom-a"
    assert prices["custom-b"] == (Decimal("0.3"), Decimal("0.4"))
    assert source == "estimated"


def test_planner_model_is_fixed_to_sonnet_five(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("routing:\n  planner: other-model\n  developer: other-model\n  verifier: other-model\npricing:\n  source: estimated\n  endpoints:\n    other-model: {input_usd_per_token: 0.1, output_usd_per_token: 0.2}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="planner"):
        load_model_config(path)


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


def test_github_reads_only_client_openspec_files_at_base_sha():
    class ClientTree(GitHubAppClient):
        def _request(self, method, path, **_kwargs):
            assert method == "GET"
            if path.endswith("/git/commits/base-sha"):
                return {"tree": {"sha": "tree-sha"}}
            assert path.endswith("/git/trees/tree-sha?recursive=1")
            return {"truncated": False, "tree": [
                {"path": "openspec/config.yaml", "type": "blob", "size": 20},
                {"path": "openspec/specs/cap/spec.md", "type": "blob", "size": 30},
                {"path": "notebooks/source.ipynb", "type": "blob", "size": 50},
            ]}

        def read_file(self, path, *, ref):
            assert ref == "base-sha"
            return f"content: {path}", "sha"

    client = ClientTree(1, 2, "unused", repository="o/r", base_branch="develop")
    files = client.read_openspec_files("base-sha")
    assert set(files) == {"openspec/config.yaml", "openspec/specs/cap/spec.md"}
    assert files["openspec/config.yaml"][1] == "sha"


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


def test_github_publishes_code_and_openspec_in_one_commit():
    calls = []

    class AtomicClient(GitHubAppClient):
        def _request(self, method, path, **kwargs):
            calls.append((method, path, kwargs.get("json")))
            if path.endswith("/pulls") and method == "GET":
                return []
            if "/git/ref/heads/" in path and method == "GET":
                response = __import__("httpx").Response(404, request=__import__("httpx").Request("GET", "https://api.github.com" + path))
                raise __import__("httpx").HTTPStatusError("missing", request=response.request, response=response)
            if path.endswith("/git/commits/base-sha"):
                return {"tree": {"sha": "base-tree"}}
            if path.endswith("/git/blobs"):
                return {"sha": f"blob-{len([call for call in calls if call[1].endswith('/git/blobs')])}"}
            if path.endswith("/git/trees"):
                assert kwargs["json"]["base_tree"] == "base-tree"
                assert {item["path"] for item in kwargs["json"]["tree"]} == {"notebooks/a.ipynb", "openspec/config.yaml"}
                return {"sha": "new-tree"}
            if path.endswith("/git/commits"):
                assert kwargs["json"]["parents"] == ["base-sha"]
                return {"sha": "new-commit"}
            if path.endswith("/git/refs"):
                assert kwargs["json"]["sha"] == "new-commit"
                return {}
            if path.endswith("/pulls"):
                return {"html_url": "https://github.com/o/r/pull/1"}
            raise AssertionError((method, path))

    client = AtomicClient(1, 2, "unused", repository="o/r", base_branch="develop")
    url = client.create_feature_pr("o/r", "feature/story", "develop", "story", "body", "base-sha", {
        "notebooks/a.ipynb": ("updated", "old-sha"),
        "openspec/config.yaml": ("schema: spec-driven", None),
    })
    assert url.endswith("/1")
    assert not any(method == "PUT" for method, _path, _body in calls)
    assert len([call for call in calls if call[1].endswith("/git/commits") and call[0] == "POST"]) == 1


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
