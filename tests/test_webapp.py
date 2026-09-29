import json
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient
from harness.contracts import ClientProfile
from harness.webapp import create_app


def payload():
    return {
        "id": "NP-001", "title": "Margen sobre costo",
        "architecture": "Silver comercial", "source_target": "fact_ventas_cabecera",
        "business_rules": "margen_bruto / costo_total", "nonfunctional": "Sin deploy",
        "validation": "Positivo, cero y NULL",
    }


def test_one_manual_form_and_validation(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"pr_url": "example"})
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert page.text.count("<form") == 1
        assert "Arquitectura" in page.text
        assert "Cancelar HU" in page.text
        assert "Detener App" in page.text
        assert "NP-001" not in page.text
        bad = client.post("/run", json={**payload(), "validation": " "})
        assert bad.status_code == 422


def test_configuration_exposes_display_hints_without_github_credentials(tmp_path: Path):
    profile = ClientProfile(name="sample", repository="o/r", base_branch="develop", allowed_paths=["notebooks/"], openspec_root="openspec", github_app_id=123, ui={"display_name": "Sample"})
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {}, profile=profile)
    with TestClient(app) as client:
        response = client.get("/configuration")
        assert response.json()["ui"]["display_name"] == "Sample"
        assert "github_app_id" not in response.text


def test_same_story_in_another_profile_cannot_reuse_previous_clients_result(tmp_path: Path):
    first = ClientProfile(name="first", repository="one/repo", base_branch="develop", allowed_paths=["notebooks/"], openspec_root="openspec")
    second = ClientProfile(name="second", repository="two/repo", base_branch="develop", allowed_paths=["notebooks/"], openspec_root="openspec")
    with TestClient(create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"pr_url": "https://github.com/one/repo/pull/1"}, profile=first)) as client:
        first_id = client.post("/run", json=payload()).json()["run_id"]
    with TestClient(create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"pr_url": "https://github.com/two/repo/pull/1"}, profile=second)) as client:
        second_id = client.post("/run", json=payload()).json()["run_id"]
        assert second_id != first_id


def test_submit_persists_run_record(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"pr_url": "https://github.com/owner/repo/pull/1", "changed_files": ["notebooks/a.ipynb"]})
    with TestClient(app) as client:
        accepted = client.post("/run", json=payload())
        assert accepted.status_code == 202
        run_id = accepted.json()["run_id"]
        result = client.get(f"/runs/{run_id}")
        assert result.status_code == 200
        assert json.loads((tmp_path / f"{run_id}.json").read_text())["state"] in {"queued", "running", "complete"}


def test_restart_marks_abandoned_run_interrupted_and_allows_retry(tmp_path: Path):
    first = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"pr_url": "example"})
    run_id = __import__("uuid").uuid5(__import__("uuid").NAMESPACE_URL, __import__("harness.contracts", fromlist=["Story"]).Story.model_validate(payload()).model_dump_json()).hex
    (tmp_path / f"{run_id}.json").write_text(json.dumps({"state": "running", "story_id": "NP-001", "attempt_id": "old-attempt", "attempts": [{"attempt_id": "old-attempt", "state": "running"}]}), encoding="utf-8")
    with TestClient(first) as client:
        assert client.get(f"/runs/{run_id}").json()["state"] == "interrupted"
        accepted = client.post("/run", json=payload())
        assert accepted.status_code == 202
        assert accepted.json()["state"] == "queued"
        assert len(json.loads((tmp_path / f"{run_id}.json").read_text())["attempts"]) == 2


def test_run_contract_records_hu_files_and_timestamps(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"changed_files": ["notebooks/a.ipynb"], "pr_url": "example"})
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        import time
        for _ in range(50):
            record = client.get(f"/runs/{run_id}").json()
            if record["state"] == "complete":
                break
            time.sleep(0.01)
        assert record["story"]["business_rules"] == payload()["business_rules"]
        assert record["changed_files"] == ["notebooks/a.ipynb"]
        assert record["created_at"] and record["updated_at"] and record["finished_at"]
        assert record["run_id"] == run_id
        assert record["attempts"][-1]["changed_files"] == ["notebooks/a.ipynb"]
        assert record["attempts"][-1]["result"]["pr_url"] == "example"


def test_openspec_artifacts_are_joined_to_attempt_and_retrievable(tmp_path: Path):
    def runner(story, run_id, attempt_id, control):
        control.record_openspec_artifact("openspec/changes/hu/proposal.md", "proposal dapi12345678901234567890", "source-hash")
        control.record_openspec(change_id="hu", state="validated")
        return {"changed_files": ["openspec/changes/hu/proposal.md"]}

    with TestClient(create_app(tmp_path, runner=runner)) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            record = client.get(f"/runs/{run_id}").json()
            if record["state"] in {"complete", "failed"}:
                break
            time.sleep(0.02)
        assert record["state"] == "complete", record.get("error") or record["state"]
        attempt = record["attempts"][-1]
        assert attempt["openspec"]["state"] == "validated"
        artifact_id = attempt["openspec"]["artifacts"]["openspec/changes/hu/proposal.md"]["artifact_id"]
        artifact = client.get(f"/runs/{run_id}/openspec/{attempt['attempt_id']}/{artifact_id}")
        assert artifact.status_code == 200
        assert "[REDACTED_TOKEN]" in artifact.json()["content"]
        assert "dapi12345678901234567890" not in artifact.text


def test_retry_preserves_legacy_failed_record_as_previous_attempt(tmp_path: Path):
    from uuid import NAMESPACE_URL, uuid5

    from harness.contracts import Story

    run_id = uuid5(NAMESPACE_URL, Story.model_validate(payload()).model_dump_json()).hex
    (tmp_path / f"{run_id}.json").write_text(json.dumps({"state": "failed", "story_id": "NP-001", "error": "old failure"}), encoding="utf-8")
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {"changed_files": []})
    with TestClient(app) as client:
        assert client.post("/run", json=payload()).status_code == 202
        attempts = client.get(f"/runs/{run_id}").json()["attempts"]
        assert attempts[0]["state"] == "failed"
        assert attempts[0]["error"] == "old failure"
        assert len(attempts) == 2


def test_cancel_running_hu_stops_at_next_safe_point(tmp_path: Path):
    started = threading.Event()
    release = threading.Event()
    published = []

    def runner(story, run_id, attempt_id, control):
        started.set()
        assert release.wait(3)
        control.check_cancel()
        published.append(True)
        return {"changed_files": ["notebooks/a.ipynb"]}

    app = create_app(tmp_path, runner=runner)
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        assert started.wait(3)
        cancelled = client.post(f"/runs/{run_id}/cancel", headers={"x-forwarded-user": "owner@example.com"})
        assert cancelled.status_code == 202
        release.set()
        for _ in range(100):
            record = client.get(f"/runs/{run_id}").json()
            if record["state"] == "cancelled":
                break
            time.sleep(0.01)
        assert record["state"] == "cancelled"
        assert record["attempts"][-1]["cancel_requested_by"] == "owner@example.com"
        assert not published


def test_cancel_queued_hu_never_starts_its_runner(tmp_path: Path):
    started = threading.Event()
    release = threading.Event()
    seen = []

    def runner(story, run_id, attempt_id, control):
        seen.append(story.id)
        if story.id == "NP-001":
            started.set()
            assert release.wait(3)
        return {"changed_files": []}

    app = create_app(tmp_path, runner=runner)
    with TestClient(app) as client:
        client.post("/run", json=payload())
        assert started.wait(3)
        second = client.post("/run", json={**payload(), "id": "NP-002"}).json()["run_id"]
        assert client.post(f"/runs/{second}/cancel").status_code == 202
        release.set()
        time.sleep(0.05)
        assert seen == ["NP-001"]
        assert client.get(f"/runs/{second}").json()["state"] == "cancelled"


def test_stop_app_requires_terminal_run_and_callers_token(tmp_path: Path):
    stopped = []
    app = create_app(
        tmp_path, runner=lambda story, run_id, attempt_id, control: {"changed_files": []},
        stopper=lambda token: stopped.append(token), app_name="demo-harness-app",
    )
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        for _ in range(100):
            if client.get(f"/runs/{run_id}").json()["state"] == "complete":
                break
            time.sleep(0.01)
        assert client.post("/app/stop", json={"run_id": run_id}).status_code == 401
        response = client.post("/app/stop", json={"run_id": run_id}, headers={"x-forwarded-access-token": "user-token", "x-forwarded-user": "owner@example.com"})
        assert response.status_code == 202
        assert stopped == ["user-token"]
        audit = client.get(f"/runs/{run_id}").json()["stop_requests"]
        assert audit[0]["requested_by"] == "owner@example.com"
        assert "user-token" not in json.dumps(audit)


def test_stop_denied_by_databricks_preserves_audit_and_returns_403(tmp_path: Path):
    def deny(_token):
        raise PermissionError("CAN MANAGE required")

    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {}, stopper=deny, app_name="demo-harness-app")
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        for _ in range(100):
            if client.get(f"/runs/{run_id}").json()["state"] == "complete":
                break
            time.sleep(0.01)
        response = client.post("/app/stop", json={"run_id": run_id}, headers={"x-forwarded-access-token": "user-token"})
        assert response.status_code == 403
        audit = client.get(f"/runs/{run_id}").json()["stop_requests"]
        assert audit[-1]["state"] == "denied"
        assert "user-token" not in json.dumps(audit)


def test_cancel_after_publication_begins_cannot_hide_created_pr(tmp_path: Path):
    started = threading.Event()
    release = threading.Event()

    def runner(story, run_id, attempt_id, control):
        control.begin_publication()
        control.record_publication("branch_created", branch="feature/test")
        started.set()
        assert release.wait(3)
        control.record_publication("pr_created", pr_url="https://github.com/o/r/pull/1")
        return {"pr_url": "https://github.com/o/r/pull/1", "changed_files": ["notebooks/a.ipynb"]}

    app = create_app(tmp_path, runner=runner)
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        assert started.wait(3)
        assert client.post(f"/runs/{run_id}/cancel").status_code == 202
        release.set()
        for _ in range(100):
            record = client.get(f"/runs/{run_id}").json()
            if record["state"] == "complete":
                break
            time.sleep(0.01)
        assert record["result"]["pr_url"].endswith("/1")
        assert record["attempts"][-1]["publication"]["stage"] == "pr_created"


def test_failed_attempt_keeps_gate_events_and_changed_files(tmp_path: Path):
    def runner(story, run_id, attempt_id, control):
        control.record_changed_files(["notebooks/a.ipynb"])
        control.record_event("sandbox", "failed")
        raise ValueError("sandbox failed")

    app = create_app(tmp_path, runner=runner)
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        for _ in range(100):
            record = client.get(f"/runs/{run_id}").json()
            if record["state"] == "failed":
                break
            time.sleep(0.01)
        attempt = record["attempts"][-1]
        assert attempt["changed_files"] == ["notebooks/a.ipynb"]
        assert attempt["events"][0]["stage"] == "sandbox"


def test_stop_request_blocks_new_hu_until_failure_is_recorded(tmp_path: Path):
    entered = threading.Event()
    release = threading.Event()

    def stopper(_token):
        entered.set()
        assert release.wait(3)
        raise PermissionError("denied")

    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id, control: {}, stopper=stopper, app_name="demo-harness-app")
    with TestClient(app) as client:
        run_id = client.post("/run", json=payload()).json()["run_id"]
        for _ in range(100):
            if client.get(f"/runs/{run_id}").json()["state"] == "complete":
                break
            time.sleep(0.01)
        result = []
        thread = threading.Thread(target=lambda: result.append(client.post("/app/stop", json={"run_id": run_id}, headers={"x-forwarded-access-token": "token"}).status_code))
        thread.start()
        assert entered.wait(3)
        assert client.post("/run", json={**payload(), "id": "NP-002"}).status_code == 409
        release.set()
        thread.join(3)
        assert result == [403]
        assert client.post("/run", json={**payload(), "id": "NP-002"}).status_code == 202
