import json
from pathlib import Path

from fastapi.testclient import TestClient
from harness.webapp import create_app


def payload():
    return {
        "id": "NP-001", "title": "Margen sobre costo",
        "architecture": "Silver comercial", "source_target": "fact_ventas_cabecera",
        "business_rules": "margen_bruto / costo_total", "nonfunctional": "Sin deploy",
        "validation": "Positivo, cero y NULL",
    }


def test_one_manual_form_and_validation(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id: {"pr_url": "example"})
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert page.text.count("<form") == 1
        assert "Arquitectura" in page.text
        assert "NP-001" not in page.text
        bad = client.post("/run", json={**payload(), "validation": " "})
        assert bad.status_code == 422


def test_submit_persists_run_record(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id: {"pr_url": "https://github.com/owner/repo/pull/1", "changed_files": ["notebooks/a.ipynb"]})
    with TestClient(app) as client:
        accepted = client.post("/run", json=payload())
        assert accepted.status_code == 202
        run_id = accepted.json()["run_id"]
        result = client.get(f"/runs/{run_id}")
        assert result.status_code == 200
        assert json.loads((tmp_path / f"{run_id}.json").read_text())["state"] in {"queued", "running", "complete"}


def test_restart_marks_abandoned_run_interrupted_and_allows_retry(tmp_path: Path):
    first = create_app(tmp_path, runner=lambda story, run_id, attempt_id: {"pr_url": "example"})
    run_id = __import__("uuid").uuid5(__import__("uuid").NAMESPACE_URL, __import__("harness.contracts", fromlist=["Story"]).Story.model_validate(payload()).model_dump_json()).hex
    (tmp_path / f"{run_id}.json").write_text(json.dumps({"state": "running", "story_id": "NP-001", "attempt_id": "old-attempt", "attempts": [{"attempt_id": "old-attempt", "state": "running"}]}), encoding="utf-8")
    with TestClient(first) as client:
        assert client.get(f"/runs/{run_id}").json()["state"] == "interrupted"
        accepted = client.post("/run", json=payload())
        assert accepted.status_code == 202
        assert accepted.json()["state"] == "queued"
        assert len(json.loads((tmp_path / f"{run_id}.json").read_text())["attempts"]) == 2


def test_run_contract_records_hu_files_and_timestamps(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id: {"changed_files": ["notebooks/a.ipynb"], "pr_url": "example"})
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


def test_retry_preserves_legacy_failed_record_as_previous_attempt(tmp_path: Path):
    from uuid import NAMESPACE_URL, uuid5

    from harness.contracts import Story

    run_id = uuid5(NAMESPACE_URL, Story.model_validate(payload()).model_dump_json()).hex
    (tmp_path / f"{run_id}.json").write_text(json.dumps({"state": "failed", "story_id": "NP-001", "error": "old failure"}), encoding="utf-8")
    app = create_app(tmp_path, runner=lambda story, run_id, attempt_id: {"changed_files": []})
    with TestClient(app) as client:
        assert client.post("/run", json=payload()).status_code == 202
        attempts = client.get(f"/runs/{run_id}").json()["attempts"]
        assert attempts[0]["state"] == "failed"
        assert attempts[0]["error"] == "old failure"
        assert len(attempts) == 2
