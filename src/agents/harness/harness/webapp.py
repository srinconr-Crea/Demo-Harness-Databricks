"""Manual HU interface with durable, joinable run records."""

from __future__ import annotations

import threading
import uuid
import hashlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from .contracts import ClientProfile, RunContract, Story
from .models import sanitize_log_value
from .store import LocalRunStore

INDEX = Path(__file__).resolve().parents[1] / "app" / "index.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CancelledRun(Exception):
    """The current attempt observed a cooperative cancellation request."""


class RunControl:
    def __init__(self, check_cancel, begin_publication, record_publication, record_changed_files, record_event, record_openspec_artifact, record_openspec):
        self.check_cancel = check_cancel
        self.begin_publication = begin_publication
        self.record_publication = record_publication
        self.record_changed_files = record_changed_files
        self.record_event = record_event
        self.record_openspec_artifact = record_openspec_artifact
        self.record_openspec = record_openspec


def create_app(
    run_dir: Path | object,
    runner: Callable[[Story, str, str, RunControl], dict],
    profile: ClientProfile | None = None,
    *,
    stopper: Callable[[str], None] | None = None,
    app_name: str | None = None,
) -> FastAPI:
    store = LocalRunStore(run_dir) if isinstance(run_dir, Path) else run_dir
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="harness-run")
    lock = threading.Lock()
    instance_id = uuid.uuid4().hex
    stopping = False

    def save(run_id: str, record: dict) -> None:
        validated = RunContract.model_validate(record)
        store.save(run_id, validated.model_dump(mode="json"))

    def history(record: dict | None, run_id: str) -> list[dict]:
        if not record:
            return []
        attempts = list(record.get("attempts") or [])
        if attempts:
            last = attempts[-1]
            if not last.get("changed_files") and record.get("changed_files"):
                last["changed_files"] = record["changed_files"]
            if last.get("result") is None and record.get("result"):
                last["result"] = record["result"]
            return attempts
        return [{
            "attempt_id": record.get("attempt_id") or f"legacy-{run_id}",
            "state": record["state"], "queued_at": record.get("created_at"),
            "started_at": record.get("started_at"), "finished_at": record.get("finished_at"),
            "error": record.get("error"),
            "changed_files": record.get("changed_files") or [], "result": record.get("result"),
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
        executor.shutdown(wait=True)

    app = FastAPI(title="Databricks Development Harness", lifespan=lifespan)

    def _control(run_id: str, attempt_id: str) -> RunControl:
        def current() -> dict:
            record = store.load(run_id)
            if not record or record.get("attempt_id") != attempt_id:
                raise CancelledRun()
            return record

        def check_cancel() -> None:
            with lock:
                record = current()
                attempt = record["attempts"][-1]
                if attempt.get("cancel_requested_at") and attempt.get("publication", {}).get("stage", "not_started") == "not_started":
                    raise CancelledRun()

        def begin_publication() -> None:
            with lock:
                record = current()
                attempt = record["attempts"][-1]
                if attempt.get("cancel_requested_at"):
                    raise CancelledRun()
                attempt["publication"] = {"stage": "publishing", "started_at": _now()}
                save(run_id, record)

        def record_publication(stage: str, **details) -> None:
            with lock:
                record = current()
                record["attempts"][-1].setdefault("publication", {}).update(stage=stage, **details)
                save(run_id, record)

        def record_changed_files(files: list[str]) -> None:
            with lock:
                record = current()
                record["attempts"][-1]["changed_files"] = files
                record["changed_files"] = files
                save(run_id, record)

        def record_event(stage: str, status: str, **details) -> None:
            with lock:
                record = current()
                record["attempts"][-1].setdefault("events", []).append({"at": _now(), "stage": stage, "status": status, **details})
                save(run_id, record)

        def record_openspec_artifact(path: str, content: str, sha256: str) -> None:
            artifact_id = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
            safe_content = sanitize_log_value(content, len(content))
            store.save_openspec_artifact(run_id, attempt_id, artifact_id, {
                "run_id": run_id, "attempt_id": attempt_id, "path": path,
                "sha256": sha256, "stored_sha256": hashlib.sha256(safe_content.encode("utf-8")).hexdigest(),
                "content": safe_content,
            })
            with lock:
                record = current()
                record["attempts"][-1].setdefault("openspec", {}).setdefault("artifacts", {})[path] = {"artifact_id": artifact_id, "sha256": sha256}
                save(run_id, record)

        def record_openspec(**details) -> None:
            with lock:
                record = current()
                record["attempts"][-1].setdefault("openspec", {}).update(details)
                save(run_id, record)

        return RunControl(check_cancel, begin_publication, record_publication, record_changed_files, record_event, record_openspec_artifact, record_openspec)

    def execute(run_id: str, attempt_id: str, story: Story) -> None:
        with lock:
            record = store.load(run_id)
            if not record or record.get("attempt_id") != attempt_id or record.get("state") == "cancelled":
                return
            timestamp = _now()
            record.update(state="running", started_at=timestamp, updated_at=timestamp)
            record["attempts"][-1].update(state="running", started_at=timestamp)
            save(run_id, record)
        try:
            result = runner(story, run_id, attempt_id, _control(run_id, attempt_id))
        except CancelledRun:
            state, result, message = "cancelled", None, None
        except Exception as error:  # noqa: BLE001 - background failures become visible run records
            state, result, message = "failed", None, sanitize_log_value(str(error), 1000)
        else:
            state, message = "complete", None
        with lock:
            record = store.load(run_id)
            timestamp = _now()
            files = result.get("changed_files", []) if result else record["attempts"][-1].get("changed_files", [])
            record.update(state=state, updated_at=timestamp, finished_at=timestamp, result=result, error=message, changed_files=files)
            record["attempts"][-1].update(state=state, finished_at=timestamp, error=message, changed_files=files, result=result)
            save(run_id, record)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX.read_text(encoding="utf-8")

    @app.get("/configuration")
    def configuration():
        return {"profile": profile.name if profile else None, "ui": profile.ui if profile else {}, "strategy": profile.strategy.kind if profile and profile.strategy else None}

    @app.post("/run", status_code=202)
    def submit(payload: dict):
        try:
            story = Story.model_validate(payload)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=error.errors(include_url=False, include_context=False)) from error
        identity = story.model_dump_json()
        if profile:
            identity += profile.model_dump_json()
        run_id = uuid.uuid5(uuid.NAMESPACE_URL, identity).hex
        with lock:
            if stopping:
                raise HTTPException(status_code=409, detail="La App está deteniéndose")
            existing = store.load(run_id)
            if existing and existing["state"] in {"queued", "running", "complete"}:
                return {"run_id": run_id, "state": existing["state"]}
            timestamp = _now()
            attempt_id = uuid.uuid4().hex
            record = {
                "schema_version": 3, "run_id": run_id, "story_id": story.id, "story": story.model_dump(),
                "client_profile": profile.name if profile else None,
                "client_profile_version": profile.version if profile else None,
                "repository": profile.repository if profile else None,
                "state": "queued", "instance_id": instance_id, "attempt_id": attempt_id,
                "attempts": history(existing, run_id),
                "created_at": existing.get("created_at", timestamp) if existing else timestamp,
                "updated_at": timestamp, "started_at": None, "finished_at": None,
                "changed_files": [], "result": None, "error": None,
                "stop_requests": existing.get("stop_requests", []) if existing else [],
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

    @app.get("/runs/{run_id}/openspec/{attempt_id}/{artifact_id}")
    def openspec_artifact(run_id: str, attempt_id: str, artifact_id: str):
        if any(len(value) != 32 or any(char not in "0123456789abcdef" for char in value) for value in (run_id, attempt_id)):
            raise HTTPException(status_code=404)
        if len(artifact_id) != 24 or any(char not in "0123456789abcdef" for char in artifact_id):
            raise HTTPException(status_code=404)
        record = store.load(run_id)
        attempt = next((item for item in record.get("attempts", []) if item.get("attempt_id") == attempt_id), None) if record else None
        if not attempt or artifact_id not in {item.get("artifact_id") for item in attempt.get("openspec", {}).get("artifacts", {}).values()}:
            raise HTTPException(status_code=404)
        artifact = store.load_openspec_artifact(run_id, attempt_id, artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404)
        return artifact

    @app.post("/runs/{run_id}/cancel", status_code=202)
    def cancel(run_id: str, request: Request):
        if len(run_id) != 32 or any(char not in "0123456789abcdef" for char in run_id):
            raise HTTPException(status_code=404)
        with lock:
            record = store.load(run_id)
            if not record:
                raise HTTPException(status_code=404)
            if record["state"] not in {"queued", "running"}:
                raise HTTPException(status_code=409, detail="La HU ya está en estado final")
            timestamp = _now()
            attempt = record["attempts"][-1]
            attempt["cancel_requested_at"] = timestamp
            attempt["cancel_requested_by"] = request.headers.get("x-forwarded-user", "unknown")
            if record["state"] == "queued":
                record.update(state="cancelled", updated_at=timestamp, finished_at=timestamp)
                attempt.update(state="cancelled", finished_at=timestamp)
            else:
                record["updated_at"] = timestamp
            save(run_id, record)
            return {"run_id": run_id, "state": record["state"], "cancel_requested_at": timestamp}

    @app.post("/app/stop", status_code=202)
    def stop(payload: dict, request: Request):
        nonlocal stopping
        token = request.headers.get("x-forwarded-access-token")
        if not token:
            raise HTTPException(status_code=401, detail="Falta autorización del usuario")
        if not stopper or not app_name:
            raise HTTPException(status_code=503, detail="La parada no está configurada")
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or len(run_id) != 32 or any(char not in "0123456789abcdef" for char in run_id):
            raise HTTPException(status_code=404)
        with lock:
            if stopping:
                raise HTTPException(status_code=409, detail="La App ya se está deteniendo")
            record = store.load(run_id)
            if not record:
                raise HTTPException(status_code=404)
            if record["state"] not in {"complete", "failed", "cancelled", "interrupted"}:
                raise HTTPException(status_code=409, detail="La HU sigue activa")
            if any((other := store.load(key)) and other.get("state") in {"queued", "running"} for key in store.list_runs()):
                raise HTTPException(status_code=409, detail="Hay otra HU activa")
            request_id = uuid.uuid4().hex
            event = {"request_id": request_id, "requested_at": _now(), "requested_by": request.headers.get("x-forwarded-user", "unknown"), "app_name": app_name, "state": "requested"}
            record.setdefault("stop_requests", []).append(event)
            save(run_id, record)
            stopping = True
        try:
            stopper(token)
        except Exception as error:
            with lock:
                record = store.load(run_id)
                next(item for item in record["stop_requests"] if item.get("request_id") == request_id)["state"] = "denied" if isinstance(error, PermissionError) or getattr(error, "error_code", None) == "PERMISSION_DENIED" else "failed"
                save(run_id, record)
                stopping = False
            raise HTTPException(status_code=403 if isinstance(error, PermissionError) or getattr(error, "error_code", None) == "PERMISSION_DENIED" else 502, detail="Databricks no autorizó la parada" if isinstance(error, PermissionError) else "No se pudo detener la App") from error
        return {"state": "stop_requested", "app_name": app_name}

    return app
