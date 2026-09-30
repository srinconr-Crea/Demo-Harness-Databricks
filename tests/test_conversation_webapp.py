from pathlib import Path

from fastapi.testclient import TestClient

from harness.contracts import StoryRequest
from harness.conversation_webapp import create_conversation_app
from test_conversation import make_engine


def test_two_field_api_enforces_identity_and_review_revision(tmp_path: Path):
    engine, _github, _models, store, _coordination, profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu="HU-API", description="Cambiar salida"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Salida 2", expected_revision=0, key="answer-api")
    attempt = store.load(run_id)["attempts"][-1]
    app = create_conversation_app(engine, profile)
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert page.text.count("<form") == 1
        assert 'name="hu"' in page.text and 'name="description"' in page.text
        assert client.get(f"/runs/{run_id}").status_code == 401
        assert client.get(f"/runs/{run_id}", headers={"x-forwarded-user": "otro@example.com"}).status_code == 403
        owner = {"x-forwarded-user": "ana@example.com"}
        assert client.get(f"/runs/{run_id}", headers=owner).json()["state"] == "awaiting_plan_review"
        assert client.get(f"/runs/{run_id}/events?after=0&limit=2", headers=owner).json()["events"]
        assert client.get(f"/runs/{run_id}/diff", headers=owner).status_code == 409
        assert client.post(f"/runs/{run_id}/retry", headers=owner, json={"expected_revision": attempt["revision"]}).status_code == 409
        assert client.post("/run", headers=owner, json={"hu": "HU", "description": "Texto", "unsafe": "x"}).status_code == 422
        wrong = {"action": "approve", "expected_revision": attempt["revision"],
                 "expected_hash": "0" * 64, "idempotency_key": "wrong-hash"}
        assert client.post(f"/runs/{run_id}/actions", headers=owner, json=wrong).status_code == 409
        wrong["expected_hash"] = attempt["context"]["plan_hash"]
        wrong["expected_revision"] = 0
        assert client.post(f"/runs/{run_id}/actions", headers=owner, json=wrong).status_code == 409
