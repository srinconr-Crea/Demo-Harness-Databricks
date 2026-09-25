"""Single manual HU interface and persistent run status."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from .contracts import Story
from .store import LocalRunStore

INDEX = Path(__file__).resolve().parents[1] / "app" / "index.html"


def create_app(run_dir: Path | object, runner: Callable[[Story], dict]) -> FastAPI:
    store = LocalRunStore(run_dir) if isinstance(run_dir, Path) else run_dir
    app = FastAPI(title="Databricks Development Harness")
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="harness-run")
    lock = threading.Lock()

    save = store.save
    load = store.load

    def execute(run_id: str, story: Story) -> None:
        save(run_id, {"state": "running", "story_id": story.id})
        try:
            result = runner(story)
            save(run_id, {"state": "complete", "story_id": story.id, "result": result})
        except Exception as error:  # noqa: BLE001 - background failures become visible run records
            save(run_id, {"state": "failed", "story_id": story.id, "error": str(error)[:1000]})

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
            existing = load(run_id)
            if existing and existing["state"] in {"queued", "running", "complete"}:
                return {"run_id": run_id, "state": existing["state"]}
            save(run_id, {"state": "queued", "story_id": story.id})
            executor.submit(execute, run_id, story)
        return {"run_id": run_id, "state": "queued"}

    @app.get("/runs/{run_id}")
    def status(run_id: str):
        if len(run_id) != 32 or any(char not in "0123456789abcdef" for char in run_id):
            raise HTTPException(status_code=404)
        result = load(run_id)
        if not result:
            raise HTTPException(status_code=404)
        return result

    return app
