"""Submit a bounded client checkout to a dedicated Databricks test Job."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import zipfile
from pathlib import Path


class SandboxJobRunner:
    def __init__(self, api, files, *, job_id: int, volume_dir: str,
                 timeout_seconds: int = 900, poll_seconds: float = 2):
        if job_id <= 0 or not re.fullmatch(r"/Volumes/demo_harness_[A-Za-z0-9_]+/[A-Za-z0-9_]+/demo_harness_[A-Za-z0-9_]+", volume_dir.rstrip("/")):
            raise ValueError("Job o volumen sandbox fuera de política")
        self.api = api
        self.files = files
        self.job_id = job_id
        self.volume_dir = volume_dir.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds

    @staticmethod
    def _archive(root: Path, profile=None) -> bytes:
        buffer = io.BytesIO()
        count, size = 0, 0
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for directory, folders, files in os.walk(root, followlinks=False):
                current = Path(directory)
                from .repository_policy import denied
                folders[:] = [name for name in folders if not denied((current / name).relative_to(root).as_posix(),
                    profile.repository_policy.denied_paths if profile else ())]
                if any((current / name).is_symlink() for name in folders):
                    raise ValueError("El sandbox no admite enlaces en el checkout")
                for name in files:
                    path = current / name
                    if path.is_symlink() or not path.is_file():
                        raise ValueError("El sandbox no admite enlaces en el checkout")
                    relative = path.relative_to(root).as_posix()
                    if denied(relative, profile.repository_policy.denied_paths if profile else ()):
                        continue
                    data = path.read_bytes()
                    count += 1
                    size += len(data)
                    if count > 2000 or size > 50_000_000:
                        raise ValueError("El checkout excede el límite del sandbox")
                    archive.writestr(relative, data)
        return buffer.getvalue()

    def run(self, root: Path, *, run_id: str, attempt_id: str,
            revision: int, test_paths: list[str], profile=None, bundle_target: str | None = None) -> dict:
        if any(re.fullmatch(r"[a-f0-9]{32}", value) is None for value in (run_id, attempt_id)) or revision < 1:
            raise ValueError("Identidad de prueba inválida")
        if (not test_paths and not bundle_target) or any(
            not path or path.startswith(("/", ".")) or "\\" in path or ".." in path.split("/")
            for path in test_paths
        ):
            raise ValueError("Rutas de pruebas fuera del perfil")
        if bundle_target and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', bundle_target) is None:
            raise ValueError('Target bundle inválido')
        payload = self._archive(root, profile)
        archive_sha = hashlib.sha256(payload).hexdigest()
        prefix = f"{self.volume_dir}/{run_id}/{attempt_id}/{revision}-{archive_sha[:16]}"
        input_path, result_path = f"{prefix}/input.zip", f"{prefix}/result.json"
        self.files.create_directory(prefix)
        self.files.upload(input_path, io.BytesIO(payload), overwrite=True)
        request = self.api.do("POST", "/api/2.2/jobs/run-now", body={
            "job_id": self.job_id,
            "idempotency_token": hashlib.sha256(f"{run_id}:{attempt_id}:{revision}:{archive_sha}".encode()).hexdigest(),
            "job_parameters": {
                "input_path": input_path, "result_path": result_path,
                "archive_sha256": archive_sha, "test_paths": json.dumps(test_paths),
                "bundle_target": bundle_target or '',
            },
        })
        job_run_id = request.get("run_id")
        if not isinstance(job_run_id, int):
            raise ValueError("El Job sandbox no devolvió run_id")
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            status = self.api.do("GET", f"/api/2.2/jobs/runs/get?run_id={job_run_id}")
            state = status.get("state") or {}
            if state.get("life_cycle_state") in {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}:
                if state.get("result_state") != "SUCCESS":
                    raise ValueError("El Job sandbox falló o no terminó correctamente")
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("El Job sandbox excedió el tiempo límite")
            time.sleep(self.poll_seconds)
        response = self.files.download(result_path)
        with response.contents as stream:
            result = json.loads(stream.read().decode("utf-8"))
        if (not isinstance(result, dict) or result.get("archive_sha256") != archive_sha
                or result.get("run_id") != run_id or result.get("attempt_id") != attempt_id):
            raise ValueError("El resultado del Job sandbox no coincide con el candidato")
        return {"passed": result.get("passed") is True, "evidence": result.get("evidence") or [],
                "job_run_id": job_run_id, "archive_sha256": archive_sha}
