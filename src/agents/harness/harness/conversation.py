"""Resumable client OpenSpec conversation with durable human review gates."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .checkout import GitCheckout, restore_checkpoint, snapshot_changes
from .contracts import RunAttempt, RunContract, Story, StoryRequest
from .models import sanitize_log_value
from .openspec import OpenSpecCLI, mark_tasks_complete, prepare_client_workspace, propose_client_change
from .patch import FileOperation, apply_file_operations
from .strategies import get_editor


_WAITS = {"awaiting_clarification", "awaiting_plan_review", "awaiting_diff_review"}
_FINAL = {"complete", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_answer(models, role: str, prompt: dict, *, stage: str, revision: int, approved_hash: str | None = None) -> dict:
    response = models.complete(
        role, json.dumps(prompt, ensure_ascii=False), stage=stage,
        revision=revision, approved_sha256=approved_hash,
    )
    body = response.text.strip()
    if body.startswith("```json") and body.endswith("```"):
        body = body[7:-3].strip()
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError(f"El rol {role} devolvió JSON inválido") from error
    if not isinstance(value, dict):
        raise ValueError(f"El rol {role} devolvió un contrato inválido")
    return value


def _hash_files(base_sha: str, files: dict[str, bytes | None]) -> str:
    digest = hashlib.sha256(bytes.fromhex(base_sha))
    for path, contents in sorted(files.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(b"D" if contents is None else b"F")
        if contents is not None:
            digest.update(len(contents).to_bytes(8, "big"))
            digest.update(contents)
    return digest.hexdigest()


def _source_summary(root: Path, profile) -> str:
    selected = []
    total = 0
    for prefix in profile.allowed_paths:
        directory = root / prefix
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if not profile.allows(relative) or path.stat().st_size > 20_000:
                continue
            try:
                contents = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            excerpt = f"\n### {relative}\n{contents[:4000]}"
            if total + len(excerpt) > 16000:
                return "".join(selected)
            selected.append(excerpt)
            total += len(excerpt)
    return "".join(selected)


def _diff(root: Path, base_sha: str, files: dict[str, bytes | None]) -> str:
    tracked = {
        value.decode("utf-8") for value in
        GitCheckout._git(["ls-files", "-z"], cwd=root, env=os.environ.copy()).split(b"\0")
        if value
    }
    chunks = []
    for path, contents in sorted(files.items()):
        before = (
            GitCheckout._git(["show", f"{base_sha}:{path}"], cwd=root, env=os.environ.copy())
            if path in tracked else b""
        )
        if b"\0" in before or (contents is not None and b"\0" in contents):
            raise ValueError("El diff contiene un archivo binario no revisable")
        old = before.decode("utf-8").splitlines(keepends=True)
        new = (contents or b"").decode("utf-8").splitlines(keepends=True)
        chunks.extend(difflib.unified_diff(old, new, fromfile=f"a/{path}", tofile=f"b/{path}"))
    result = "".join(chunks)
    if not result or len(result.encode("utf-8")) > 1_000_000:
        raise ValueError("El candidato no tiene un diff completo revisable")
    return result


class ConversationEngine:
    def __init__(self, profile, store, coordinator, github_factory, models_factory,
                 cli: OpenSpecCLI, test_runner):
        self.profile = profile
        self.store = store
        self.coordinator = coordinator
        self.github_factory = github_factory
        self.models_factory = models_factory
        self.cli = cli
        self.test_runner = test_runner

    def _save(self, record: dict) -> None:
        self.store.save(record["run_id"], RunContract.model_validate(record).model_dump(mode="json"))

    def submit(self, story: StoryRequest, *, actor: str) -> str:
        if not actor:
            raise ValueError("Falta identidad de quien envía la HU")
        if self.profile.strategy is None and self.profile.general_patch is None:
            raise ValueError("El perfil no ofrece una estrategia de edición")
        run_id, attempt_id = uuid.uuid4().hex, uuid.uuid4().hex
        timestamp = _now()
        attempt = RunAttempt(
            attempt_id=attempt_id, state="queued", stage="exploring",
            queued_at=timestamp, messages=[{"kind": "story", "actor": actor, "text": story.description, "at": timestamp}],
        )
        record = RunContract(
            run_id=run_id, story_id=story.hu, story=story,
            client_profile=self.profile.name, client_profile_version=self.profile.version,
            repository=self.profile.repository, state="queued", attempt_id=attempt_id,
            attempts=[attempt], created_at=timestamp, updated_at=timestamp,
        ).model_dump(mode="json")
        self.store.save(run_id, record)
        self.coordinator.create(run_id, attempt_id, "exploring")
        return run_id

    def get(self, run_id: str) -> dict:
        record = self.store.load(run_id)
        if not record or not record.get("attempts"):
            raise ValueError("Ejecución no encontrada")
        attempt = record["attempts"][-1]
        row = self.coordinator.get(run_id, attempt["attempt_id"])
        if row and row.get("checkpoint_id") and (row["checkpoint_id"] != attempt.get("checkpoint_id") or row["stage"] != attempt.get("stage")):
            checkpoint = self.store.load_checkpoint(run_id, attempt["attempt_id"], row["checkpoint_id"])
            recovered = checkpoint.get("metadata", {}).get("attempt")
            if not isinstance(recovered, dict) or recovered.get("stage") != row["stage"]:
                raise ValueError("El estado de coordinación no coincide con el checkpoint")
            record["attempts"][-1] = recovered
            record["attempts"][-1]["checkpoint_id"] = row["checkpoint_id"]
            record["state"] = self._state(row["stage"])
            record["updated_at"] = _now()
            self._save(record)
        elif row and row["stage"] != attempt.get("stage"):
            raise ValueError("La coordinación avanzó sin un checkpoint recuperable")
        return record

    @staticmethod
    def _state(stage: str) -> str:
        return stage if stage in _WAITS | _FINAL else "running"

    @staticmethod
    def _event(attempt: dict, kind: str, **details) -> None:
        timeline = attempt.setdefault("timeline", [])
        timeline.append({"seq": len(timeline) + 1, "stage": attempt.get("stage"),
                         "kind": kind, "revision": attempt.get("revision", 0),
                         "at": _now(), "details": sanitize_log_value(details, 4000)})

    def act(self, run_id: str, action: str, *, actor: str, expected_revision: int,
            key: str, expected_hash: str | None = None, text: str | None = None) -> dict:
        record = self.check_action(run_id, action, actor=actor, expected_revision=expected_revision,
                                   key=key, expected_hash=expected_hash, text=text)
        if key in record["attempts"][-1].get("context", {}).get("action_keys", []):
            return record
        return self.advance(run_id, action={"kind": action, "actor": actor, "key": key,
                                            "text": text.strip() if text else None,
                                            "expected_hash": expected_hash})

    def check_action(self, run_id: str, action: str, *, actor: str, expected_revision: int,
                     key: str, expected_hash: str | None = None, text: str | None = None) -> dict:
        record = self.get(run_id)
        attempt = record["attempts"][-1]
        if key in attempt.get("context", {}).get("action_keys", []):
            return record
        stage = attempt.get("stage")
        valid = {
            "awaiting_clarification": {"answer", "cancel"},
            "awaiting_plan_review": {"approve", "changes", "cancel"},
            "awaiting_diff_review": {"approve", "changes", "cancel"},
        }
        if not actor or not key or len(key) > 100 or action not in valid.get(stage, set()):
            raise ValueError("Acción no válida para el estado actual")
        if attempt["revision"] != expected_revision:
            raise ValueError("La revisión de la decisión está obsoleta")
        required_hash = (attempt.get("context") or {}).get(
            "candidate_hash" if stage == "awaiting_diff_review" else "plan_hash"
        )
        if stage != "awaiting_clarification" and action == "approve" and expected_hash != required_hash:
            raise ValueError("La aprobación corresponde a un hash obsoleto")
        if action in {"answer", "changes"} and (not text or not text.strip() or len(text) > 10000):
            raise ValueError("La respuesta humana no puede estar vacía")
        return record

    def advance(self, run_id: str, *, action: dict | None = None) -> dict:
        for _ in range(12):
            record = self.get(run_id)
            attempt = record["attempts"][-1]
            stage = attempt.get("stage")
            if stage in _FINAL or (stage in _WAITS and action is None):
                return record
            row = self.coordinator.get(run_id, attempt["attempt_id"])
            if row is None or row["stage"] != stage:
                raise ValueError("Estado de coordinación inconsistente")
            owner = uuid.uuid4().hex
            transition_key = (action or {}).get("key") or uuid.uuid4().hex
            claimed = self.coordinator.claim(
                run_id, attempt["attempt_id"], expected_version=row["version"],
                owner=owner, key=f"claim:{transition_key}", now=time.time(), ttl_seconds=1800,
            )
            if claimed is None:
                raise ValueError("El intento ya está siendo procesado")
            previous_checkpoint = row.get("checkpoint_id")
            try:
                github = self.github_factory()
                models = self.models_factory(run_id, attempt["attempt_id"])
                with tempfile.TemporaryDirectory(prefix="harness-client-run-") as directory:
                    root = Path(directory) / "client"
                    base_sha = attempt.get("base_sha") or github.base_sha(self.profile.base_branch)
                    github.checkout(root, base_sha)
                    prepare_client_workspace(root, self.profile)
                    restore_id = (
                        attempt.get("context", {}).get("prearchive_checkpoint_id")
                        if stage == "updating" and attempt.get("context", {}).get("restore_prearchive")
                        else previous_checkpoint
                    )
                    if restore_id:
                        checkpoint = self.store.load_checkpoint(run_id, attempt["attempt_id"], restore_id)
                        restore_checkpoint(root, checkpoint, base_sha, self._allows)
                    if restore_id != previous_checkpoint:
                        attempt["context"].pop("restore_prearchive", None)
                        attempt["context"].pop("candidate_hash", None)
                        attempt["context"].pop("diff_sha256", None)
                    attempt["base_sha"] = base_sha
                    next_stage = self._step(root, record, attempt, github, models, action)
                    attempt["stage"] = next_stage
                    attempt["state"] = self._state(next_stage)
                    if action:
                        attempt.setdefault("context", {}).setdefault("action_keys", []).append(action["key"])
                    if next_stage == "exploring" and attempt.get("base_sha") != base_sha:
                        checkpoint_id = self.store.save_checkpoint(
                            run_id, attempt["attempt_id"], max(1, attempt["revision"]),
                            attempt["base_sha"], {}, metadata={"attempt": attempt},
                        )
                    else:
                        files = snapshot_changes(root, base_sha, self._allows)
                        checkpoint_id = self.store.save_checkpoint(
                            run_id, attempt["attempt_id"], max(1, attempt["revision"]),
                            base_sha, files, metadata={"attempt": attempt},
                        )
                    finished = self.coordinator.finish(
                        run_id, attempt["attempt_id"], expected_version=claimed["version"],
                        owner=owner, key=f"finish:{transition_key}", stage=next_stage,
                        checkpoint_id=checkpoint_id, now=time.time(),
                    )
                    if finished is None:
                        raise ValueError("La transición perdió su lease de coordinación")
                    attempt["checkpoint_id"] = checkpoint_id
                    record["state"] = attempt["state"]
                    record["updated_at"] = _now()
                    if next_stage in _FINAL:
                        record["finished_at"] = _now()
                        attempt["finished_at"] = record["finished_at"]
                    self._save(record)
            except Exception:
                # Release a claimed lease on a failed operation. The prior checkpoint
                # remains canonical and can be retried after an operator correction.
                self.coordinator.finish(
                    run_id, attempt["attempt_id"], expected_version=claimed["version"],
                    owner=owner, key=f"error:{transition_key}", stage=stage,
                    checkpoint_id=previous_checkpoint, now=time.time(),
                )
                raise
            action = None
            if next_stage in _WAITS | _FINAL:
                return record
        raise RuntimeError("El flujo excedió el número de transiciones consecutivas")

    def _allows(self, path: str) -> bool:
        return self.profile.allows(path) or self.profile.allows_openspec(path)

    def _step(self, root: Path, record: dict, attempt: dict, github, models, action: dict | None) -> str:
        stage = attempt["stage"]
        story = StoryRequest.model_validate(record["story"])
        context = attempt.setdefault("context", {})
        revision = attempt["revision"]
        if stage == "exploring":
            result = _json_answer(models, "explorer", {
                "task": "Explorar la HU, resumirla y preguntar solo lo necesario. JSON: summary, questions[]",
                "story": story.model_dump(), "source_summary": _source_summary(root, self.profile),
            }, stage=stage, revision=revision)
            questions = result.get("questions")
            if not isinstance(result.get("summary"), str) or not isinstance(questions, list) or any(not isinstance(question, str) for question in questions) or len(questions) > 5:
                raise ValueError("Explore devolvió un contrato inválido")
            attempt["messages"].append({"kind": "explore", "actor": "explorer", "text": result["summary"], "at": _now()})
            self._event(attempt, "explore", summary=result["summary"], questions=questions)
            if questions:
                context["questions"] = questions
                return "awaiting_clarification"
            return "proposing"
        if stage == "awaiting_clarification":
            if action["kind"] == "cancel":
                self._event(attempt, "cancel", actor=action["actor"])
                return "cancelled"
            attempt["messages"].append({"kind": "clarification", "actor": action["actor"], "text": action["text"], "at": _now()})
            context["clarification"] = action["text"]
            self._event(attempt, "clarification", actor=action["actor"])
            return "proposing"
        if stage in {"proposing", "updating"}:
            change_id = context.get("change_id")
            if not change_id:
                slug = re.sub(r"[^a-z0-9-]+", "-", story.hu.lower()).strip("-")[:40] or "story"
                change_id = f"{slug}-{attempt['attempt_id'][:8]}"
                context["change_id"] = change_id
            feedback = context.pop("feedback", None)
            plan = propose_client_change(
                self.cli, root, change_id, story, models,
                source_summary=_source_summary(root, self.profile) + "\n" + context.get("clarification", ""),
                feedback=feedback,
                revision=revision + 1,
                on_artifact=lambda path, content, digest: self._save_artifact(record, attempt, path, content, digest),
            )
            attempt["revision"] += 1
            context["plan_hash"] = _hash_files(attempt["base_sha"], {path: content.encode("utf-8") for path, content in plan.artifacts.items()})
            context.pop("candidate_hash", None)
            self._event(attempt, "update" if stage == "updating" else "propose", plan_hash=context["plan_hash"], artifact_paths=sorted(plan.artifacts))
            return "awaiting_plan_review"
        if stage == "awaiting_plan_review":
            if action["kind"] == "cancel":
                self._event(attempt, "cancel", actor=action["actor"])
                return "cancelled"
            if action["kind"] == "changes":
                context["feedback"] = action["text"]
                self._event(attempt, "plan_changes", actor=action["actor"], text=action["text"])
                return "updating"
            attempt.setdefault("approvals", []).append({"kind": "plan", "revision": revision,
                                                         "sha256": context["plan_hash"], "actor": action["actor"], "at": _now()})
            self._event(attempt, "plan_approved", actor=action["actor"], hash=context["plan_hash"])
            return "applying"
        if stage == "applying":
            approved = next((item for item in reversed(attempt["approvals"]) if item["kind"] == "plan" and item["revision"] == revision), None)
            if not approved or approved["sha256"] != context["plan_hash"]:
                raise ValueError("Apply requiere un plan aprobado vigente")
            change_root = root / "openspec" / "changes" / context["change_id"]
            artifacts = {path.name: path.read_text(encoding="utf-8")[:50000] for path in change_root.glob("*.md")}
            if self.profile.general_patch:
                proposal = _json_answer(models, "developer", {
                    "task": "Aplicar las tareas aprobadas. Responder JSON operations[] con op/path/content/expected_sha256 y notes.",
                    "story": story.model_dump(), "artifacts": artifacts,
                    "source_summary": _source_summary(root, self.profile),
                    "allowed_paths": self.profile.general_patch.allowed_paths,
                }, stage=stage, revision=revision, approved_hash=approved["sha256"])
                raw = proposal.get("operations")
                if not isinstance(raw, list):
                    raise ValueError("El desarrollador no devolvió operaciones tipadas")
                paths = apply_file_operations(root, self.profile, [FileOperation.model_validate(item) for item in raw])
            else:
                paths = self._apply_ratio(root, story, models, attempt, approved)
            context["changed_code_paths"] = paths
            self._event(attempt, "apply", paths=paths)
            return "verifying"
        if stage == "verifying":
            paths = context.get("changed_code_paths") or []
            evidence = self.test_runner(root, self.profile, paths, record, attempt)
            context["tests"] = evidence
            if not isinstance(evidence, dict) or evidence.get("passed") is not True:
                self._event(attempt, "verify_failed", evidence=evidence)
                context["correction_count"] = context.get("correction_count", 0) + 1
                if context["correction_count"] > 2:
                    raise ValueError("Las pruebas obligatorias agotaron el límite de correcciones")
                context["feedback"] = json.dumps({"test_evidence": evidence}, ensure_ascii=False)
                return "updating"
            changed = snapshot_changes(root, attempt["base_sha"], self._allows)
            diff = _diff(root, attempt["base_sha"], changed)
            plan = (root / "openspec" / "changes" / context["change_id"] / "tasks.md").read_text(encoding="utf-8")
            spec_path = root / "openspec" / "changes" / context["change_id"] / "specs" / context["change_id"] / "spec.md"
            specs = spec_path.read_text(encoding="utf-8")
            check = _json_answer(models, "openspec_verifier", {
                "task": "Contrastar especificaciones, tareas, pruebas y diff. JSON approved, findings[]",
                "story": story.model_dump(), "specs": specs[:20000], "tasks": plan[:20000],
                "test_evidence": evidence, "diff": diff[:20000],
            }, stage=stage, revision=revision, approved_hash=context["plan_hash"])
            independent = _json_answer(models, "verifier", {
                "task": "Revisión independiente del diff y las pruebas. JSON approved, findings[]",
                "story": story.model_dump(), "test_evidence": evidence, "diff": diff[:20000],
            }, stage=stage, revision=revision, approved_hash=context["plan_hash"])
            if check.get("approved") is not True or independent.get("approved") is not True:
                findings = list(check.get("findings") or []) + list(independent.get("findings") or [])
                context["correction_count"] = context.get("correction_count", 0) + 1
                if context["correction_count"] > 2:
                    raise ValueError("La verificación agotó el límite de correcciones")
                context["feedback"] = json.dumps(findings, ensure_ascii=False)
                self._event(attempt, "verify_findings", findings=findings)
                return "updating"
            self._event(attempt, "verify", evidence=evidence)
            return "preparing_final_diff"
        if stage == "preparing_final_diff":
            prearchive_files = snapshot_changes(root, attempt["base_sha"], self._allows)
            context["prearchive_checkpoint_id"] = self.store.save_checkpoint(
                record["run_id"], attempt["attempt_id"], revision,
                attempt["base_sha"], prearchive_files, metadata={"attempt": attempt},
            )
            mark_tasks_complete(root, context["change_id"])
            self.cli.archive(root, context["change_id"])
            files = snapshot_changes(root, attempt["base_sha"], self._allows)
            diff = _diff(root, attempt["base_sha"], files)
            context["candidate_hash"] = _hash_files(attempt["base_sha"], files)
            context["diff_sha256"] = self.store.save_review_diff(record["run_id"], attempt["attempt_id"], revision, diff)
            attempt["changed_files"] = sorted(files)
            self._event(attempt, "sync", files=sorted(files))
            self._event(attempt, "archive", change_id=context["change_id"])
            self._event(attempt, "diff_ready", candidate_hash=context["candidate_hash"], diff_sha256=context["diff_sha256"])
            return "awaiting_diff_review"
        if stage == "awaiting_diff_review":
            if action["kind"] == "cancel":
                self._event(attempt, "cancel", actor=action["actor"])
                return "cancelled"
            if action["kind"] == "changes":
                context["feedback"] = action["text"]
                context["restore_prearchive"] = True
                self._event(attempt, "diff_changes", actor=action["actor"], text=action["text"])
                return "updating"
            attempt.setdefault("approvals", []).append({"kind": "diff", "revision": revision,
                                                         "sha256": context["candidate_hash"], "actor": action["actor"], "at": _now()})
            self._event(attempt, "diff_approved", actor=action["actor"], hash=context["candidate_hash"])
            return "publishing"
        if stage == "publishing":
            files = snapshot_changes(root, attempt["base_sha"], self._allows)
            approved = next((item for item in reversed(attempt["approvals"]) if item["kind"] == "diff" and item["revision"] == revision), None)
            if not approved or approved["sha256"] != _hash_files(attempt["base_sha"], files):
                raise ValueError("El candidato ya no coincide con el diff aprobado")
            remote_sha = github.base_sha(self.profile.base_branch)
            if remote_sha != attempt["base_sha"]:
                attempt["base_sha"] = remote_sha
                attempt["revision"] += 1
                attempt["openspec"] = {}
                attempt["context"] = {}
                self._event(attempt, "base_advanced", new_base_sha=remote_sha)
                return "exploring"
            branch = f"feature/{re.sub(r'[^a-z0-9-]+', '-', story.hu.lower()).strip('-')[:60]}-{attempt['attempt_id'][:8]}"
            publish_files = {path: (contents.decode("utf-8") if contents is not None else None, None) for path, contents in files.items()}
            attempt["publication"] = {**attempt.get("publication", {}), "stage": "publishing", "branch": branch}

            def publication_progress(stage: str, **details) -> None:
                attempt["publication"] = {**attempt["publication"], "stage": stage,
                                           **sanitize_log_value(details, 1000)}
                self._event(attempt, stage, **details)
                record["updated_at"] = _now()
                self._save(record)

            url = github.create_feature_pr(
                self.profile.repository, branch, self.profile.base_branch,
                story.hu[:160], f"## HU\n{story.description}\n\nOpenSpec validado y diff aprobado en la App. Merge manual pendiente.",
                attempt["base_sha"], publish_files,
                on_progress=publication_progress,
            )
            checks = github.pr_check_status(self.profile.repository, branch)
            attempt["publication"] = {**attempt["publication"], "stage": "pr_created", "branch": branch, "pr_url": url}
            attempt["result"] = {"pr_url": url, "branch": branch, "pr_checks": checks,
                                 "changed_files": sorted(files), "candidate_hash": approved["sha256"]}
            record["result"] = attempt["result"]
            record["changed_files"] = sorted(files)
            self._event(attempt, "publication_complete", pr_url=url, checks=checks)
            return "complete"
        raise ValueError("Etapa conversacional no reconocida")

    def _save_artifact(self, record: dict, attempt: dict, path: str, content: str, digest: str) -> None:
        artifact_id = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
        safe_content = sanitize_log_value(content, len(content))
        self.store.save_openspec_artifact(record["run_id"], attempt["attempt_id"], artifact_id, {
            "run_id": record["run_id"], "attempt_id": attempt["attempt_id"], "path": path,
            "sha256": digest, "content": safe_content,
        })
        attempt.setdefault("openspec", {}).setdefault("artifacts", {})[path] = {"artifact_id": artifact_id, "sha256": digest}
        self._event(attempt, "artifact_ready", path=path, sha256=digest)
        record["updated_at"] = _now()
        self._save(record)

    def _apply_ratio(self, root: Path, request: StoryRequest, models, attempt: dict, approved: dict) -> list[str]:
        story = Story(
            id=request.hu[:64], title=request.hu[:160], architecture=request.description,
            source_target=request.description, business_rules=request.description,
            nonfunctional=request.description, validation=request.description,
        )
        editor = get_editor("silver_safe_ratio")
        spec = editor.parse(story, self.profile)
        attempt.setdefault("context", {})["ratio_spec"] = spec.model_dump()
        path = self.profile.strategy.notebook
        target = root / path
        original = target.read_text(encoding="utf-8")
        proposal = _json_answer(models, "developer", {
            "task": "Confirmar la expresión del plan aprobado para la razón Silver.",
            "story": request.model_dump(), "expected_expression": spec.expression,
            "source_excerpt": editor.source(original, self.profile)[:12000],
        }, stage="applying", revision=attempt["revision"], approved_hash=approved["sha256"])
        if proposal.get("expression") != spec.expression:
            raise ValueError("El desarrollador propuso otra expresión")
        updated = editor.edit(original, self.profile, spec)
        editor.validate(updated, self.profile, spec)
        target.write_text(updated, encoding="utf-8")
        return [path]
