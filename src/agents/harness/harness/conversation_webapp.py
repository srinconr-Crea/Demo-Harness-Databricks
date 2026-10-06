"""Authenticated two-field conversation API for the client OpenSpec workflow."""

from __future__ import annotations

import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ValidationError

from .contracts import StoryRequest
from .models import sanitize_log_value

INDEX = Path(__file__).resolve().parents[1] / "app" / "index.html"


class ActionRequest(BaseModel):
    action: Literal["answer", "approve", "changes", "cancel"]
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    expected_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    text: str | None = Field(default=None, max_length=10000)


class RetryRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    failure_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


def create_conversation_app(engine, profile) -> FastAPI:
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="harness-conversation")
    error_lock = Lock()

    def background(run_id: str, action: dict | None = None, retry_legacy: bool = False, retry_options: dict | None = None) -> None:
        try:
            if retry_options:
                engine.retry(run_id, **retry_options)
                return
            if retry_legacy:
                engine.retry_legacy(run_id)
            if action:
                engine.act(run_id, action["action"], actor=action["actor"],
                           expected_revision=action["expected_revision"],
                           expected_hash=action.get("expected_hash"),
                           text=action.get("text"), key=action["idempotency_key"])
            else:
                engine.advance(run_id)
        except Exception as error:  # noqa: BLE001 - surfaced as a durable event
            if str(error) == "El intento ya está siendo procesado":
                return
            # The engine owns state transitions under its lease. A worker must never
            # overwrite a checkpoint or a newer transition after losing ownership.
            logging.getLogger(__name__).error('Fallo del trabajador: %s', type(error).__name__)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        for run_id in engine.store.list_runs():
            try:
                record = engine.get(run_id)
                timeline = record['attempts'][-1].get('timeline') or []
                if record["state"] in {"queued", "running"} and not (timeline and timeline[-1]['kind'] == 'error'):
                    executor.submit(background, run_id)
            except Exception as recovery_error:  # noqa: BLE001 - recover other runs independently
                logging.getLogger(__name__).error('No se pudo recuperar el intento: %s', type(recovery_error).__name__)
                continue
        yield
        executor.shutdown(wait=True)

    app = FastAPI(title="Databricks Development Harness", lifespan=lifespan)

    def run_id_or_404(run_id: str) -> None:
        if re.fullmatch(r"[a-f0-9]{32}", run_id) is None:
            raise HTTPException(status_code=404)

    def actor_or_401(request: Request) -> str:
        actor = request.headers.get("x-forwarded-user", "").strip()
        if not actor:
            raise HTTPException(status_code=401, detail="Falta identidad autenticada de Databricks")
        return actor

    def authorized_run(run_id: str, request: Request) -> tuple[dict, str]:
        run_id_or_404(run_id)
        actor = actor_or_401(request)
        try:
            record = engine.get(run_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        messages = record["attempts"][-1].get("messages") or []
        submitter = messages[0].get("actor") if messages else None
        if actor != submitter and actor not in profile.reviewers:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta conversación")
        return record, actor

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX.read_text(encoding="utf-8")

    @app.get("/configuration")
    def configuration():
        return {"profile": profile.name, "ui": profile.ui,
                "strategies": [kind for kind, enabled in (
                    ("silver_safe_ratio", profile.strategy), ("general_patch", profile.general_patch)
                ) if enabled]}

    @app.post("/run", status_code=202)
    def submit(payload: dict, request: Request):
        actor = actor_or_401(request)
        try:
            story = StoryRequest.model_validate(payload)
            run_id = engine.submit(story, actor=actor)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=error.errors(include_url=False, include_context=False)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        executor.submit(background, run_id)
        return {"run_id": run_id, "state": "queued"}

    @app.get("/runs/{run_id}")
    def status(run_id: str, request: Request):
        return sanitize_log_value(authorized_run(run_id, request)[0], 200000)

    @app.get("/runs/{run_id}/events")
    def events(run_id: str, request: Request, after: int = 0, limit: int = 50):
        record, _actor = authorized_run(run_id, request)
        if after < 0 or not 1 <= limit <= 100:
            raise HTTPException(status_code=422, detail="Paginación inválida")
        timeline = record["attempts"][-1].get("timeline") or []
        page = [event for event in timeline if event["seq"] > after][:limit]
        return {"events": page, "next": page[-1]["seq"] if page else after,
                "state": record["state"]}

    @app.get("/runs/{run_id}/calls")
    def calls(run_id: str, request: Request):
        record, _actor = authorized_run(run_id, request)
        attempt_id = record["attempts"][-1]["attempt_id"]
        items = engine.store.list_agent_calls(run_id, attempt_id)
        return {"calls": sorted(({
            "call_id": item.get("call_id"), "role": item.get("role"),
            "stage": item.get("stage"), "revision": item.get("revision"),
            "candidate_revision": item.get("candidate_revision"), "candidate_hash": item.get("candidate_hash"),
            "model": item.get("model"), "status": item.get("status"),
            "input_tokens": item.get("input_tokens"), "output_tokens": item.get("output_tokens"),
            "estimated_cost_usd": item.get("estimated_cost_usd"),
            "profile_provenance": item.get("profile_provenance"),
            "completed_at": item.get("completed_at"),
        } for item in items), key=lambda item: item["completed_at"] or "")}

    @app.get("/runs/{run_id}/artifacts/{artifact_id}")
    def artifact(run_id: str, artifact_id: str, request: Request):
        record, _actor = authorized_run(run_id, request)
        if re.fullmatch(r"[a-f0-9]{24}", artifact_id) is None:
            raise HTTPException(status_code=404)
        attempt = record["attempts"][-1]
        refs = attempt.get("openspec", {}).get("artifacts", {})
        path = next((name for name, ref in refs.items() if ref["artifact_id"] == artifact_id), None)
        if path is None:
            history = attempt.get('openspec', {}).get('artifact_history', {})
            path = next((name for name, versions in history.items()
                         if any(ref['artifact_id'] == artifact_id for ref in versions)), None)
            if path is None:
                raise HTTPException(status_code=404)
            historical = engine.store.load_openspec_artifact(run_id, attempt['attempt_id'], artifact_id)
            if not historical:
                raise HTTPException(status_code=404)
            return {**historical, 'redacted': True}
        checkpoint_id = attempt.get("checkpoint_id")
        if checkpoint_id:
            checkpoint = engine.store.load_checkpoint(run_id, attempt["attempt_id"], checkpoint_id)
            contents = checkpoint["files"].get(path)
            if contents is not None and hashlib.sha256(contents).hexdigest() == refs[path]["sha256"]:
                return {"path": path, "content": contents.decode("utf-8"), "sha256": refs[path]["sha256"]}
        historical = engine.store.load_openspec_artifact(run_id, attempt["attempt_id"], artifact_id)
        if not historical:
            raise HTTPException(status_code=404)
        return {**historical, "redacted": True}

    @app.get("/runs/{run_id}/diff")
    def diff(run_id: str, request: Request):
        record, _actor = authorized_run(run_id, request)
        attempt = record["attempts"][-1]
        context = attempt.get("context") or {}
        digest = context.get("diff_sha256")
        if not digest or attempt['stage'] not in {'awaiting_diff_review', 'publishing', 'complete'}:
            raise HTTPException(status_code=409, detail="El diff final todavía no está disponible")
        return {"revision": attempt["revision"], "candidate_hash": context["candidate_hash"],
                "diff_sha256": digest,
                "diff": engine.store.load_review_diff(run_id, attempt["attempt_id"], attempt["revision"], digest)}

    @app.post("/runs/{run_id}/actions", status_code=202)
    def action(run_id: str, payload: ActionRequest, request: Request):
        _record, actor = authorized_run(run_id, request)
        try:
            engine.check_action(run_id, payload.action, actor=actor,
                                expected_revision=payload.expected_revision,
                                expected_hash=payload.expected_hash, text=payload.text,
                                key=payload.idempotency_key)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        executor.submit(background, run_id, {**payload.model_dump(), "actor": actor})
        return {"run_id": run_id, "state": "action_queued", "idempotency_key": payload.idempotency_key}

    @app.post("/runs/{run_id}/retry", status_code=202)
    def retry(run_id: str, payload: RetryRequest, request: Request):
        record, _actor = authorized_run(run_id, request)
        attempt = record["attempts"][-1]
        failure = attempt.get('failure') or {}
        if record['state'] == 'failed' and engine.profile_matches(record) and engine.context_matches(record):
            if (not failure.get('retryable') or attempt['revision'] != payload.expected_revision
                    or failure.get('id') != payload.failure_id):
                raise HTTPException(status_code=409, detail='No hay una etapa fallida vigente para reintentar')
            executor.submit(background, run_id, retry_options={**payload.model_dump(), 'actor': _actor})
            return {'run_id': run_id, 'state': 'retry_queued'}
        timeline = attempt.get("timeline") or []
        legacy = attempt.get('context', {}).get('instruction_engine') != 'client-skills-v1'
        if record.get('repository') != profile.repository:
            raise HTTPException(status_code=409, detail='El repositorio no corresponde a esta instalación')
        legacy = legacy or not engine.profile_matches(record) or not engine.context_matches(record)
        if (record["state"] not in {"queued", "running", "awaiting_plan_review", "awaiting_clarification", "awaiting_diff_review", "failed"}
                or attempt["revision"] != payload.expected_revision
                or (not legacy and (record['state'] not in {'queued', 'running'} or not timeline or timeline[-1]['kind'] != 'error'))):
            raise HTTPException(status_code=409, detail="No hay una etapa fallida vigente para reintentar")
        executor.submit(background, run_id, retry_legacy=legacy)
        return {"run_id": run_id, "state": "retry_queued"}

    return app
