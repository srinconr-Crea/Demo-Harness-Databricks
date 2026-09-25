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
    app = create_app(tmp_path, runner=lambda story: {"pr_url": "example"})
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert page.text.count("<form") == 1
        assert "Arquitectura" in page.text
        bad = client.post("/run", json={**payload(), "validation": " "})
        assert bad.status_code == 422


def test_submit_persists_run_record(tmp_path: Path):
    app = create_app(tmp_path, runner=lambda story: {"pr_url": "https://github.com/owner/repo/pull/1"})
    with TestClient(app) as client:
        accepted = client.post("/run", json=payload())
        assert accepted.status_code == 202
        run_id = accepted.json()["run_id"]
        result = client.get(f"/runs/{run_id}")
        assert result.status_code == 200
        assert json.loads((tmp_path / f"{run_id}.json").read_text())["state"] in {"queued", "running", "complete"}
