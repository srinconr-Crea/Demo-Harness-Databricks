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
from .client_config import profile_bytes, provenance
from .context_manager import (
    ContextManager,
    DecisionConflict,
    SourceCache,
    load_context_policy,
)
from .contracts import RunAttempt, RunContract, Story, StoryRequest
from .models import ModelInvocationError, sanitize_log_value
from .openspec import (
    OpenSpecCLI,
    exploration_context,
    instruction_context,
    mark_tasks_complete,
    prepare_client_workspace,
    propose_client_change,
)
from .patch import FileOperation, apply_file_operations
from .prompt_contracts import PromptContracts, ArtifactPresentationError
from .repo_context import ContextResponseError, RepoContext, contextual_answer
from .repository_policy import safe_target
from .skills import SkillCatalog, digest
from .strategies import get_editor

_WAITS = {"awaiting_clarification", "awaiting_plan_review", "awaiting_diff_review"}
_FINAL = {"complete", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_answer(models, role: str, prompt: dict, *, stage: str, revision: int, approved_hash: str | None = None, repo_context=None) -> dict:
    return contextual_answer(models, role, prompt, repo_context, stage=stage, revision=revision, approved_sha256=approved_hash)
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
    for prefix in (profile.allowed_paths or ['']):
        directory = root / prefix
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if not profile.allows_read(relative) or path.stat().st_size > 20_000:
                continue
            safe_target(root, relative)
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
                 cli: OpenSpecCLI, test_runner, *, publication_mode='approved_plan', context_policy=None):
        self.profile = profile
        self.store = store
        self.coordinator = coordinator
        self.github_factory = github_factory
        self.models_factory = models_factory
        self.cli = cli
        self.test_runner = test_runner
        if publication_mode not in {'approved_plan', 'diff_review'}:
            raise ValueError('Modalidad de publicación inválida')
        self.publication_mode = publication_mode
        self.context_policy = context_policy or load_context_policy()
        self._context_caches = {}

    def _context_settings(self):
        return {'engine': self.context_policy.version,
                'policy_sha256': digest(self.context_policy.model_dump()),
                'catalog_sha256': PromptContracts().sha256}

    def context_matches(self, record):
        pinned = record['attempts'][-1].get('context', {}).get('context_management')
        return pinned is None or pinned == self._context_settings()

    def _new_context(self):
        state = {'instruction_engine': 'client-skills-v1'}
        if self.context_policy.enabled:
            state['context_management'] = self._context_settings()
        return state

    def _save(self, record: dict) -> None:
        self.store.save(record["run_id"], RunContract.model_validate(record).model_dump(mode="json"))

    @property
    def profile_identity(self):
        return provenance(self.profile)

    def _profile_ref(self):
        digest = self.store.save_profile_snapshot(profile_bytes(self.profile))
        return {**self.profile_identity, 'snapshot_sha256': digest}

    def profile_matches(self, record):
        ref = record['attempts'][-1].get('profile_provenance') or {}
        return record.get('repository') == self.profile.repository and all(
            ref.get(k) == self.profile_identity[k] for k in ('sha256', 'repository'))

    def _require_profile(self, record):
        if not self.profile_matches(record):
            raise ValueError('El perfil del intento cambió o no tiene procedencia; requiere reintento explícito')
        ref = record['attempts'][-1]['profile_provenance']
        if self.store.load_profile_snapshot(ref['snapshot_sha256']) != profile_bytes(self.profile):
            raise ValueError('El snapshot del perfil no coincide')
        if not self.context_matches(record):
            raise ValueError('Política/prompts de contexto incompatibles; requiere retry humano')

    def submit(self, story: StoryRequest, *, actor: str) -> str:
        if not actor:
            raise ValueError("Falta identidad de quien envía la HU")
        if self.profile.strategy is None and self.profile.general_patch is None:
            raise ValueError("El perfil no ofrece una estrategia de edición")
        run_id, attempt_id = uuid.uuid4().hex, uuid.uuid4().hex
        timestamp = _now()
        attempt = RunAttempt(
            attempt_id=attempt_id, state="queued", stage="exploring",
            profile_provenance=self._profile_ref(),
            publication_mode=self.publication_mode,
            context=self._new_context(),
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
            record['finished_at'] = recovered.get('finished_at')
            record["updated_at"] = _now()
            self._save(record)
        elif row and row["stage"] != attempt.get("stage"):
            raise ValueError("La coordinación avanzó sin un checkpoint recuperable")
        from .progress import checklist
        record['checklist'] = checklist(record['attempts'][-1])
        return record

    def retry_legacy(self, run_id: str):
        record = self.get(run_id)
        old = record['attempts'][-1]
        if record.get('repository') != self.profile.repository:
            raise ValueError('El repositorio del intento no corresponde a esta instalación')
        if (old.get('context', {}).get('instruction_engine') == 'client-skills-v1'
                and self.profile_matches(record) and self.context_matches(record)):
            return
        if old.get('publication', {}).get('pr_url'):
            raise ValueError('El intento ya tiene un PR; revisar publicación existente')
        identifier = uuid.uuid4().hex
        attempt = RunAttempt(attempt_id=identifier, state='queued', stage='exploring',
            profile_provenance=self._profile_ref(),
            publication_mode=old.get('publication_mode', 'diff_review'), queued_at=_now(),
            context={**self._new_context(), 'previous_attempt_id': old['attempt_id']},
            messages=[m for m in old.get('messages', []) if m.get('kind') in {'story', 'clarification', 'change'}]).model_dump(mode='json')
        clarifications = [m['text'] for m in attempt['messages'] if m.get('kind') == 'clarification']
        if clarifications:
            attempt['context'].update(clarifications=clarifications, clarification='\n'.join(clarifications))
        record['attempts'].append(attempt)
        record['attempt_id'], record['state'] = identifier, 'queued'
        self.coordinator.create(run_id, identifier, 'exploring')
        self._save(record)

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
        if action != 'cancel':
            self._require_profile(record)
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
                cancelling = action and action['kind'] == 'cancel'
                if cancelling:
                    self._event(attempt, 'cancel', actor=action['actor'])
                    attempt['stage'] = attempt['state'] = record['state'] = 'cancelled'
                    attempt['finished_at'] = record['finished_at'] = record['updated_at'] = _now()
                    attempt.setdefault('context', {}).setdefault('action_keys', []).append(action['key'])
                    if self.coordinator.finish(run_id, attempt['attempt_id'], expected_version=claimed['version'],
                        owner=owner, key=f'finish:{transition_key}', stage='cancelled',
                        checkpoint_id=previous_checkpoint, now=time.time()) is None:
                        raise ValueError('La cancelación perdió su lease')
                    self._save(record)
                    return record
                self._require_profile(record)
                if not cancelling and attempt.get('context', {}).get('instruction_engine') != 'client-skills-v1':
                    raise ValueError('Intento histórico sin procedencia: requiere reintento explícito con cliente preparado')
                github = self.github_factory()
                models = self.models_factory(run_id, attempt["attempt_id"])
                with tempfile.TemporaryDirectory(prefix="harness-client-run-") as directory:
                    root = Path(directory) / "client"
                    base_sha = attempt.get("base_sha") or github.base_sha(self.profile.base_branch)
                    attempt['base_sha'] = base_sha
                    github.checkout(root, base_sha)
                    catalog = None if cancelling else prepare_client_workspace(root, self.profile, cli=self.cli)
                    restore_id = (
                        attempt.get("context", {}).get("prearchive_checkpoint_id")
                        if stage == "updating" and attempt.get("context", {}).get("restore_prearchive")
                        else previous_checkpoint
                    )
                    if restore_id:
                        checkpoint = self.store.load_checkpoint(run_id, attempt["attempt_id"], restore_id)
                        restore_checkpoint(root, checkpoint, base_sha, self._allows)
                    if catalog:
                        identity = SkillCatalog(root, self.profile, self.cli.version()).identity()
                        previous = attempt['context'].get('instruction_catalog')
                        if previous and previous != identity:
                            raise ValueError('Las skills o el runtime cambiaron; requiere reintento explícito')
                        attempt['context']['instruction_catalog'] = identity
                    if restore_id != previous_checkpoint:
                        attempt["context"].pop("restore_prearchive", None)
                        attempt["context"].pop("candidate_hash", None)
                        attempt["context"].pop("diff_sha256", None)
                    attempt["base_sha"] = base_sha
                    step_error = None
                    try:
                        next_stage = self._step(root, record, attempt, github, models, action)
                    except DecisionConflict:
                        attempt['context']['questions'] = ['Hay decisiones incompatibles: aclara cuál sustituye a cuál y su alcance.']
                        self._event(attempt, 'context_conflict', questions=attempt['context']['questions'])
                        next_stage = 'awaiting_clarification'
                    except (ValueError, RuntimeError, TimeoutError) as error:
                        step_error = error
                        category = getattr(error, 'category', 'model_invocation' if isinstance(error, ModelInvocationError)
                            else 'invalid_contract' if isinstance(error, ValueError) else 'stage_error')
                        message = sanitize_log_value(str(error), 1000)
                        self._event(attempt, 'error', message=message, category=category)
                        attempt['failure'] = {'id': uuid.uuid4().hex, 'category': category,
                            'failed_stage': stage, 'revision': attempt['revision'],
                            'retryable': isinstance(error, (ContextResponseError, ArtifactPresentationError, ModelInvocationError, TimeoutError, RuntimeError))}
                        attempt['error'] = record['error'] = message
                        next_stage = 'failed'
                    attempt["stage"] = next_stage
                    attempt["state"] = self._state(next_stage)
                    if next_stage in _FINAL:
                        attempt['finished_at'] = record['finished_at'] = _now()
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
                    self._save(record)
                    if step_error is not None and not isinstance(step_error, (ContextResponseError, ArtifactPresentationError)):
                        raise step_error
            except Exception as error:
                # Release a claimed lease on a failed operation. The prior checkpoint
                # remains canonical and can be retried after an operator correction.
                current = self.coordinator.get(run_id, attempt['attempt_id'])
                if (isinstance(error, (ValueError, RuntimeError, TimeoutError))
                        and current and current['lease_owner'] == owner and current['version'] == claimed['version']):
                    message = sanitize_log_value(str(error), 1000)
                    self._event(attempt, 'error', message=message, category='preparation_error')
                    attempt['failure'] = {'id': uuid.uuid4().hex, 'category': 'preparation_error',
                        'failed_stage': stage, 'revision': attempt['revision'],
                        'retryable': bool(attempt.get('base_sha')) and isinstance(error, (RuntimeError, TimeoutError))}
                    attempt['stage'] = attempt['state'] = record['state'] = 'failed'
                    attempt['error'] = record['error'] = message
                    attempt['finished_at'] = record['finished_at'] = record['updated_at'] = _now()
                    checkpoint_id = previous_checkpoint
                    if attempt.get('base_sha'):
                        previous_files = self.store.load_checkpoint(run_id, attempt['attempt_id'], previous_checkpoint)['files'] if previous_checkpoint else {}
                        checkpoint_id = self.store.save_checkpoint(run_id, attempt['attempt_id'], max(1, attempt['revision']),
                            attempt['base_sha'], previous_files, metadata={'attempt': attempt})
                    finished = self.coordinator.finish(run_id, attempt['attempt_id'], expected_version=claimed['version'],
                        owner=owner, key=f'failure:{transition_key}', stage='failed', checkpoint_id=checkpoint_id, now=time.time())
                    if finished is None:
                        raise ValueError('La persistencia del fallo perdió su lease') from error
                    attempt['checkpoint_id'] = checkpoint_id
                    self._save(record)
                    raise
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

    def retry(self, run_id, *, expected_revision, actor, failure_id=None):
        record = self.get(run_id)
        attempt = record['attempts'][-1]
        failure = attempt.get('failure') or {}
        if (not actor or record['state'] != 'failed' or not failure.get('retryable')
                or attempt['revision'] != expected_revision or failure.get('id') != failure_id):
            raise ValueError('No hay una etapa fallida vigente para reintentar')
        self._require_profile(record)
        row = self.coordinator.get(run_id, attempt['attempt_id'])
        if not row or row['stage'] != 'failed' or row['checkpoint_id'] != attempt.get('checkpoint_id'):
            raise ValueError('El fallo ya fue reanudado o su checkpoint cambió')
        owner = uuid.uuid4().hex
        key = f"retry:{failure_id}"
        claimed = self.coordinator.claim(run_id, attempt['attempt_id'], expected_version=row['version'],
            owner=owner, key=key, now=time.time(), ttl_seconds=1800)
        if claimed is None:
            raise ValueError('El intento ya está siendo procesado')
        try:
            stage = failure['failed_stage']
            # Restore the exact failure checkpoint and metadata before resuming.
            checkpoint = self.store.load_checkpoint(run_id, attempt['attempt_id'], row['checkpoint_id'])
            if (checkpoint['metadata']['attempt'].get('failure') or {}).get('id') != failure_id:
                raise ValueError('El fallo no coincide con el checkpoint')
            self._event(attempt, 'retry', actor=actor, failure_id=failure_id, failed_stage=stage)
            attempt['stage'], attempt['state'] = stage, 'queued'
            attempt['failure'] = None
            attempt['error'] = record['error'] = None
            attempt['finished_at'] = record['finished_at'] = None
            record['state'] = 'queued'
            checkpoint_id = self.store.save_checkpoint(run_id, attempt['attempt_id'], max(1, attempt['revision']),
                attempt['base_sha'], checkpoint['files'], metadata={'attempt': attempt})
            finished = self.coordinator.finish(run_id, attempt['attempt_id'], expected_version=claimed['version'],
                owner=owner, key=f'finish:{key}', stage=stage, checkpoint_id=checkpoint_id, now=time.time())
            if finished is None:
                raise ValueError('El reintento perdió su lease')
            attempt['checkpoint_id'] = checkpoint_id
            self._save(record)
        except Exception:
            self.coordinator.finish(run_id, attempt['attempt_id'], expected_version=claimed['version'],
                owner=owner, key=f'error:{key}', stage=row['stage'], checkpoint_id=row['checkpoint_id'], now=time.time())
            raise
        return self.advance(run_id)

    def _allows(self, path: str) -> bool:
        policy = self.profile.general_patch
        return self.profile.allows_openspec(path) or (self.profile.allows_code(path)
            and (policy is None or Path(path).suffix in policy.extensions))

    def _step(self, root: Path, record: dict, attempt: dict, github, models, action: dict | None) -> str:
        self._require_profile(record)
        stage = attempt["stage"]
        story = StoryRequest.model_validate(record["story"])
        context = attempt.setdefault("context", {})
        revision = attempt["revision"]
        if action and action['kind'] == 'cancel':
            self._event(attempt, 'cancel', actor=action['actor'])
            return 'cancelled'
        catalog = SkillCatalog(root, self.profile, self.cli.version())
        snapshot = lambda value: self.store.save_instruction_snapshot(record['run_id'], attempt['attempt_id'], value)
        manager = None
        if context.get('context_management'):
            previous = None
            ref = context.get('memory_sha256')
            if ref:
                try:
                    previous = self.store.load_context_snapshot(record['run_id'], attempt['attempt_id'], ref)
                except (ValueError, FileNotFoundError):
                    self._event(attempt, 'context_rebuilt', reason='invalid_derivation')
            identity = {'run_id': record['run_id'], 'attempt_id': attempt['attempt_id'],
                        'repository': self.profile.repository, 'profile_sha256': self.profile_identity['sha256'],
                        'base_sha': attempt['base_sha'], 'revision': revision, 'stage': stage,
                        'checkpoint_id': attempt.get('checkpoint_id')}
            key = (record['run_id'], attempt['attempt_id'])
            if key not in self._context_caches:
                if len(self._context_caches) >= 100:
                    self._context_caches.pop(next(iter(self._context_caches)))
                self._context_caches[key] = SourceCache(self.context_policy)

            def context_event(metadata):
                context['context_snapshot_sha256'] = metadata['snapshot_sha256']
                context['memory_sha256'] = self.store.save_context_snapshot(record['run_id'], attempt['attempt_id'], manager.memory_snapshot())
                self._event(attempt, 'context_selection', **metadata)

            manager = ContextManager(root, self.profile, self.context_policy, identity,
                attempt['messages'], context.get('questions', []), cache=self._context_caches[key], previous=previous,
                on_snapshot=lambda value: self.store.save_context_snapshot(record['run_id'], attempt['attempt_id'], value),
                on_event=context_event)

        def repository_context():
            return RepoContext(root, self.profile, cache=manager.cache if manager else None,
                               identity=manager.identity if manager else None)

        def answer(role, phase, prompt, *, instructions=None, repo_context=None, approved_hash=None):
            payload, extras = catalog.compose(phase, prompt, instructions=instructions,
                base_sha=attempt['base_sha'], on_snapshot=snapshot)
            provenance = extras['instruction_provenance']
            self._event(attempt, 'instructions', **provenance)
            return contextual_answer(models, role, payload, repo_context, stage=stage,
                revision=revision, approved_sha256=approved_hash, context_manager=manager, phase=phase, **extras)
        if stage == "exploring":
            result = answer("explorer", 'explore', {
                "task": "Explorar la HU, resumirla y preguntar solo lo necesario. JSON: summary, questions[]",
                "story": story.model_dump(), "source_summary": _source_summary(root, self.profile),
                "policy": self.profile.model_dump(),
                "clarifications": context.get('clarifications', []),
                'source_summary_truncated': True,
            }, instructions=exploration_context(self.cli, root, self.profile), repo_context=repository_context())
            questions = result.get("questions")
            if not isinstance(result.get("summary"), str) or not isinstance(questions, list) or any(not isinstance(question, str) for question in questions) or len(questions) > 5:
                raise ValueError("Explore devolvió un contrato inválido")
            attempt["messages"].append({"kind": "explore", "actor": "explorer", "text": result["summary"], "at": _now()})
            self._event(attempt, "explore", summary=result["summary"], questions=questions)
            if questions:
                context["questions"] = questions
                return "awaiting_clarification"
            context.pop('questions', None)
            return "proposing"
        if stage == "awaiting_clarification":
            if action["kind"] == "cancel":
                self._event(attempt, "cancel", actor=action["actor"])
                return "cancelled"
            attempt["messages"].append({"kind": "clarification", "actor": action["actor"], "text": action["text"], "at": _now(), 'revision': revision})
            context.setdefault('clarifications', []).append(action['text'])
            context['clarification'] = '\n'.join(context['clarifications'])
            self._event(attempt, "clarification", actor=action["actor"])
            return "exploring"
        if stage in {"proposing", "updating"}:
            change_id = context.get("change_id")
            if not change_id:
                slug = re.sub(r"[^a-z0-9-]+", "-", story.hu.lower()).strip("-")[:40] or "story"
                change_id = f"{slug}-{attempt['attempt_id'][:8]}"
                context["change_id"] = change_id
            feedback = context.get("feedback")
            plan = propose_client_change(
                self.cli, root, change_id, story, models,
                source_summary=_source_summary(root, self.profile) + "\n" + context.get("clarification", ""),
                feedback=feedback,
                revision=revision + 1,
                profile=self.profile,
                skill_catalog=catalog, base_sha=attempt['base_sha'], on_snapshot=snapshot,
                context_manager=manager,
                on_artifact=lambda path, content, digest: self._save_artifact(record, attempt, path, content, digest),
            )
            attempt["revision"] += 1
            context.pop('feedback', None)
            context['plan_metadata'] = plan.metadata
            context['plan_metadata']['instruction_catalog'] = context['instruction_catalog']
            context['plan_paths'] = sorted(plan.artifacts)
            context["plan_hash"] = self._current_plan_hash(root, attempt)
            context.pop("candidate_hash", None)
            self._event(attempt, "update" if stage == "updating" else "propose", plan_hash=context["plan_hash"], artifact_paths=sorted(plan.artifacts))
            return "awaiting_plan_review"
        if stage == "awaiting_plan_review":
            if action["kind"] == "cancel":
                self._event(attempt, "cancel", actor=action["actor"])
                return "cancelled"
            if action["kind"] == "changes":
                context["feedback"] = action["text"]
                attempt['messages'].append({'kind': 'change', 'actor': action['actor'], 'text': action['text'], 'at': _now(), 'revision': revision})
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
            if context['plan_hash'] != self._current_plan_hash(root, attempt):
                raise ValueError('Los bytes del plan ya no coinciden con la aprobación')
            change_root = root / "openspec" / "changes" / context["change_id"]
            apply_context = instruction_context(self.cli, root, context['change_id'], 'apply', self.profile)
            artifacts = {path.relative_to(change_root).as_posix(): path.read_text(encoding='utf-8')
                         for path in change_root.rglob('*.md')}
            if self.profile.general_patch:
                proposal = answer("developer", 'apply', {
                    "task": "Aplicar las tareas aprobadas. Responder JSON operations[] con op/path/content/expected_sha256 y notes.",
                    "story": story.model_dump(), "artifacts": artifacts,
                    "source_summary": (json.dumps([repository_context().request({'op': 'read_file', 'path': item['path']})
                        for item in context['plan_metadata']['manifest'] if item['op'] != 'create'], ensure_ascii=False)
                        if manager else _source_summary(root, self.profile)),
                    "allowed_paths": self.profile.general_patch.allowed_paths,
                    "policy": self.profile.model_dump(),
                    'approved_manifest': context['plan_metadata']['manifest'],
                }, instructions=apply_context, approved_hash=approved["sha256"], repo_context=repository_context())
                raw = proposal.get("operations")
                if not isinstance(raw, list):
                    raise ValueError("El desarrollador no devolvió operaciones tipadas")
                operations = [FileOperation.model_validate(item) for item in raw]
                allowed = {(item['op'], item['path']) for item in context['plan_metadata']['manifest']}
                if {(item.op, item.path) for item in operations} != allowed:
                    context['feedback'] = 'El desarrollador requiere archivos u operaciones fuera del manifiesto aprobado; revisar alcance.'
                    self._event(attempt, 'scope_changed')
                    return 'updating'
                paths = apply_file_operations(root, self.profile, operations)
            else:
                paths = self._apply_ratio(root, story, models, attempt, approved, answer, apply_context)
            context["changed_code_paths"] = paths
            self._event(attempt, "apply", paths=paths)
            return "verifying"
        if stage == "verifying":
            paths = context.get("changed_code_paths") or []
            evidence = self.test_runner(root, self.profile, paths, record, attempt)
            context["tests"] = evidence
            context['verified_code_hash'] = _hash_files(attempt['base_sha'], {
                p: (safe_target(root, p).read_bytes() if safe_target(root, p).exists() else None) for p in paths})
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
            spec_root = root / "openspec" / "changes" / context["change_id"] / "specs"
            specs = {path.relative_to(spec_root).as_posix(): path.read_text(encoding='utf-8')
                     for path in spec_root.rglob('*.md')}
            check = answer("openspec_verifier", 'verify', {
                "task": "Contrastar especificaciones, tareas, pruebas y diff. JSON approved, findings[]",
                "story": story.model_dump(), "specs": specs, "tasks": plan,
                "test_evidence": evidence, "diff": diff,
            }, instructions=self.cli.status(root, context['change_id']), approved_hash=context["plan_hash"])
            try:
                independent = contextual_answer(models, 'verifier', {
                    'task': 'Revisión asesora independiente. JSON approved, findings[]. Nunca decide la publicación.',
                    'story': story.model_dump(), 'test_evidence': evidence, 'diff': diff[:20000],
                    'diff_truncated': len(diff) > 20000,
                }, stage=stage, revision=revision, approved_sha256=context['plan_hash'],
                    context_manager=manager, phase='verify')
                if not isinstance(independent.get('approved'), bool) or not isinstance(independent.get('findings'), list):
                    raise ContextResponseError('Contrato de asesor inválido')
                context['advisory'] = {'status': 'complete', **independent}
            except (ModelInvocationError, TimeoutError, ContextResponseError) as error:
                context['advisory'] = {'status': 'unavailable', 'error': type(error).__name__, 'findings': []}
            calls = getattr(models, 'calls', [])
            context['advisory']['call_id'] = getattr(calls[-1], 'call_id', None) if calls else None
            self._event(attempt, 'advisory', **context['advisory'])
            if check.get("approved") is not True:
                findings = list(check.get("findings") or [])
                context["correction_count"] = context.get("correction_count", 0) + 1
                if context["correction_count"] > 2:
                    raise ValueError("La verificación agotó el límite de correcciones")
                context["feedback"] = json.dumps(findings, ensure_ascii=False)
                self._event(attempt, "verify_findings", findings=findings)
                return "updating"
            self._event(attempt, "verify", evidence=evidence)
            return "preparing_final_diff"
        if stage == "preparing_final_diff":
            current_code = _hash_files(attempt['base_sha'], {
                p: (safe_target(root, p).read_bytes() if safe_target(root, p).exists() else None)
                for p in context['changed_code_paths']})
            if current_code != context.get('verified_code_hash') or context['plan_hash'] != self._current_plan_hash(root, attempt):
                raise ValueError('El candidato o plan cambió después de verify')
            prearchive_files = snapshot_changes(root, attempt["base_sha"], self._allows)
            context["prearchive_checkpoint_id"] = self.store.save_checkpoint(
                record["run_id"], attempt["attempt_id"], revision,
                attempt["base_sha"], prearchive_files, metadata={"attempt": attempt},
            )
            mark_tasks_complete(root, context["change_id"])
            archive_context = instruction_context(self.cli, root, context['change_id'], 'archive', self.profile)
            for phase in ('sync', 'archive'):
                _payload, extras = catalog.compose(phase, {'execution': 'deterministic_archive'},
                    instructions=archive_context, base_sha=attempt['base_sha'], on_snapshot=snapshot)
                self._event(attempt, 'instructions', **extras['instruction_provenance'])
            self.cli.archive(root, context["change_id"])
            files = snapshot_changes(root, attempt["base_sha"], self._allows)
            diff = _diff(root, attempt["base_sha"], files)
            context["candidate_hash"] = _hash_files(attempt["base_sha"], files)
            context['verified_candidate_hash'] = context['candidate_hash']
            context['publication_authorization'] = {'plan_hash': context['plan_hash'], 'base_sha': attempt['base_sha'],
                'revision': revision, 'candidate_hash': context['candidate_hash']}
            context["diff_sha256"] = self.store.save_review_diff(record["run_id"], attempt["attempt_id"], revision, diff)
            attempt["changed_files"] = sorted(files)
            synced = {p: hashlib.sha256(c).hexdigest() for p, c in files.items() if p.startswith('openspec/specs/') and c is not None}
            archived = {p: hashlib.sha256(c).hexdigest() for p, c in files.items() if p.startswith('openspec/changes/archive/') and c is not None}
            if not archived:
                raise ValueError('Archive no produjo artefactos archivados verificables')
            self._event(attempt, 'sync', files=sorted(files), spec_hashes=synced)
            self._event(attempt, 'archive', change_id=context['change_id'], archive_hashes=archived)
            self._event(attempt, "diff_ready", candidate_hash=context["candidate_hash"], diff_sha256=context["diff_sha256"])
            return 'publishing' if attempt.get('publication_mode', 'diff_review') == 'approved_plan' else 'awaiting_diff_review'
        if stage == "awaiting_diff_review":
            if action["kind"] == "cancel":
                self._event(attempt, "cancel", actor=action["actor"])
                return "cancelled"
            if action["kind"] == "changes":
                context["feedback"] = action["text"]
                attempt['messages'].append({'kind': 'change', 'actor': action['actor'], 'text': action['text'], 'at': _now(), 'revision': revision})
                context["restore_prearchive"] = True
                self._event(attempt, "diff_changes", actor=action["actor"], text=action["text"])
                return "updating"
            attempt.setdefault("approvals", []).append({"kind": "diff", "revision": revision,
                                                         "sha256": context["candidate_hash"], "actor": action["actor"], "at": _now()})
            self._event(attempt, "diff_approved", actor=action["actor"], hash=context["candidate_hash"])
            return "publishing"
        if stage == "publishing":
            files = snapshot_changes(root, attempt["base_sha"], self._allows)
            automatic = attempt.get('publication_mode', 'diff_review') == 'approved_plan'
            approved = next((item for item in reversed(attempt['approvals']) if item['kind'] == ('plan' if automatic else 'diff') and item['revision'] == revision), None)
            candidate_hash = _hash_files(attempt['base_sha'], files)
            authorization = context.get('publication_authorization', {})
            valid = approved and (approved['sha256'] == context.get('plan_hash') and authorization == {
                'plan_hash': approved['sha256'], 'base_sha': attempt['base_sha'], 'revision': revision,
                'candidate_hash': candidate_hash} and context.get('tests', {}).get('passed') is True
                and context.get('verified_candidate_hash') == candidate_hash if automatic else approved['sha256'] == candidate_hash)
            if not valid:
                raise ValueError('El candidato ya no coincide con la autorización y verificación vigentes')
            remote_sha = github.base_sha(self.profile.base_branch)
            if remote_sha != attempt["base_sha"]:
                attempt["base_sha"] = remote_sha
                attempt["revision"] += 1
                attempt["openspec"] = {}
                attempt["context"] = self._new_context()
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
                story.hu[:160], f"## HU\n{story.description}\n\nOpenSpec y candidato verificados; publicación autorizada en la App. Merge manual pendiente.",
                attempt["base_sha"], publish_files,
                on_progress=publication_progress,
            )
            checks = github.pr_check_status(self.profile.repository, branch)
            attempt["publication"] = {**attempt["publication"], "stage": "pr_created", "branch": branch, "pr_url": url}
            attempt["result"] = {"pr_url": url, "branch": branch, "pr_checks": checks,
                                 "changed_files": sorted(files), "candidate_hash": candidate_hash}
            record["result"] = attempt["result"]
            record["changed_files"] = sorted(files)
            self._event(attempt, "publication_complete", pr_url=url, checks=checks)
            return "complete"
        raise ValueError("Etapa conversacional no reconocida")

    def _current_plan_hash(self, root, attempt):
        context = attempt['context']
        files = {p: safe_target(root, p).read_bytes() for p in context['plan_paths']}
        files['__plan_metadata__.json'] = json.dumps(context['plan_metadata'], sort_keys=True, ensure_ascii=False).encode('utf-8')
        return _hash_files(attempt['base_sha'], files)

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

    def _apply_ratio(self, root: Path, request: StoryRequest, models, attempt: dict, approved: dict, answer, apply_context) -> list[str]:
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
        proposal = answer("developer", 'apply', {
            "task": "Confirmar la expresión del plan aprobado para la razón Silver.",
            "story": request.model_dump(), "expected_expression": spec.expression,
            "source_excerpt": editor.source(original, self.profile)[:12000],
        }, instructions=apply_context, approved_hash=approved["sha256"])
        if proposal.get("expression") != spec.expression:
            raise ValueError("El desarrollador propuso otra expresión")
        updated = editor.edit(original, self.profile, spec)
        editor.validate(updated, self.profile, spec)
        target.write_text(updated, encoding="utf-8")
        return [path]
