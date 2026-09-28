"""Manual HU interface with durable, joinable run records."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from .contracts import ClientProfile, RunContract, Story
from .store import LocalRunStore

INDEX = Path(__file__).resolve().parents[1] / "app" / "index.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app(run_dir: Path | object, runner: Callable[[Story, str, str], dict], profile: ClientProfile | None = None) -> FastAPI:
    store = LocalRunStore(run_dir) if isinstance(run_dir, Path) else run_dir
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="harness-run")
    lock = threading.Lock()
    instance_id = uuid.uuid4().hex

    def save(run_id: str, record: dict) -> None:
        validated = RunContract.model_validate(record)
        store.save(run_id, validated.model_dump(mode="json"))

    def history(record: dict | None, run_id: str) -> list[dict]:
        if not record:
            return []
        attempts = list(record.get("attempts") or [])
        if attempts:
            return attempts
        return [{
            "attempt_id": record.get("attempt_id") or f"legacy-{run_id}",
            "state": record["state"], "queued_at": record.get("created_at"),
            "started_at": record.get("started_at"), "finished_at": record.get("finished_at"),
            "error": record.get("error"),
        }]

    def reconcile_abandoned() -> None:
        for run_id in store.list_runs():
            record = store.load(run_id)
            if record and record.get("state") in {"queued", "running"} and record.get("instance_id") != instance_id:
                timestamp = _now()
                record["attempts"] = history(record, run_id)
                record.update(run_id=run_id, state="interrupted", updated_at=timestamp, finished_at=timestamp, error="La App se detuvo antes de terminar; reenvía la HU para reintentar")
                record["attempts"][-1].update(state="interrupted", finished_at=timestamp, error=record["error"])
                save(run_id, record)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        reconcile_abandoned()
        yield
        executor.shutdown(wait=False)

    app = FastAPI(title="Databricks Development Harness", lifespan=lifespan)

    def execute(run_id: str, attempt_id: str, story: Story) -> None:
        record = store.load(run_id)
        if not record or record.get("attempt_id") != attempt_id:
            return
        timestamp = _now()
        record.update(state="running", started_at=timestamp, updated_at=timestamp)
        record["attempts"][-1].update(state="running", started_at=timestamp)
        save(run_id, record)
        try:
            result = runner(story, run_id, attempt_id)
        except Exception as error:  # noqa: BLE001 - background failures become visible run records
            state, result, message = "failed", None, str(error)[:1000]
        else:
            state, message = "complete", None
        record = store.load(run_id)
        timestamp = _now()
        record.update(state=state, updated_at=timestamp, finished_at=timestamp, result=result, error=message, changed_files=result.get("changed_files", []) if result else [])
        record["attempts"][-1].update(state=state, finished_at=timestamp, error=message)
        save(run_id, record)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX.read_text(encoding="utf-8")

    @app.post("/run", status_code=202)
    def submit(payload: dict):
        try:
            story = Story.model_validate(payload)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=error.errors(include_url=False, include_context=False)) from error
        run_id = uuid.uuid5(uuid.NAMESPACE_URL, story.model_dump_json()).hex
        with lock:
            existing = store.load(run_id)
            if existing and existing["state"] in {"queued", "running", "complete"}:
                return {"run_id": run_id, "state": existing["state"]}
            timestamp = _now()
            attempt_id = uuid.uuid4().hex
            record = {
                "schema_version": 2, "run_id": run_id, "story_id": story.id, "story": story.model_dump(),
                "client_profile": profile.name if profile else None,
                "client_profile_version": profile.version if profile else None,
                "repository": profile.repository if profile else None,
                "state": "queued", "instance_id": instance_id, "attempt_id": attempt_id,
                "attempts": history(existing, run_id),
                "created_at": existing.get("created_at", timestamp) if existing else timestamp,
                "updated_at": timestamp, "started_at": None, "finished_at": None,
                "changed_files": [], "result": None, "error": None,
            }
            record["attempts"].append({"attempt_id": attempt_id, "state": "queued", "queued_at": timestamp})
            save(run_id, record)
            executor.submit(execute, run_id, attempt_id, story)
        return {"run_id": run_id, "state": "queued"}

    @app.get("/runs/{run_id}")
    def status(run_id: str):
        if len(run_id) != 32 or any(char not in "0123456789abcdef" for char in run_id):
            raise HTTPException(status_code=404)
        result = store.load(run_id)
        if not result:
            raise HTTPException(status_code=404)
        return result

    return app
