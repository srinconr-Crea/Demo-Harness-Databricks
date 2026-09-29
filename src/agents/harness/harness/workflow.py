"""Fail-closed workflow for configured, deterministic edit strategies."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import tempfile
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from .contracts import ClientProfile, Story, parse_agent_output
from .openspec import OpenSpecCLI, collect_changed_openspec, mark_tasks_complete, plan_client_change, prepare_client_workspace
from .strategies import get_editor


@dataclass(frozen=True)
class RunReport:
    story_id: str
    base_sha: str
    branch: str
    pr_url: str
    changed_files: list[str]
    diff: str
    model_cost_usd: Decimal | None
    remote_check: str
    pr_checks: str = "unavailable"


def _json_response(models, role: str, prompt: str) -> dict:
    response = models.complete(role, prompt)
    return parse_agent_output(role, response.text)


class _NoopControl:
    def check_cancel(self):
        return None

    def begin_publication(self):
        return None

    def record_publication(self, _stage, **_details):
        return None

    def record_changed_files(self, _files):
        return None

    def record_event(self, _stage, _status, **_details):
        return None

    def record_openspec_artifact(self, _path, _content, _sha256):
        return None

    def record_openspec(self, **_details):
        return None


def run_story(story: Story, profile: ClientProfile, github, models, sandbox_verify, *, control=None, agent_config: dict | None = None, openspec_cli: OpenSpecCLI | None = None, attempt_id: str | None = None) -> RunReport:
    control = control or _NoopControl()
    agent_config = agent_config or yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "defaults" / "agents.yaml").read_text(encoding="utf-8"))
    control.check_cancel()
    strategy = profile.strategy
    if strategy is None:
        raise ValueError("No existe un editor validado para este perfil")
    editor = get_editor(strategy.kind)
    path = strategy.notebook
    if not profile.allows(path):
        raise ValueError("El notebook queda fuera de las rutas permitidas")
    spec = editor.parse(story, profile)
    attempt_token = (attempt_id or uuid.uuid4().hex)[:12]
    branch = f"{profile.feature_branch(story)[:90]}-{attempt_token}"
    base_sha = github.base_sha(profile.base_branch)
    original, source_sha = github.read_file(path, ref=base_sha)
    control.check_cancel()
    original_source = editor.source(original, profile)
    base_openspec = github.read_openspec_files(base_sha)
    cli = openspec_cli or OpenSpecCLI()
    change_id = re.sub(r"[^a-z0-9-]+", "-", story.id.lower()).strip("-")[:40] or "story"
    change_id = f"{change_id}-{attempt_token}"
    with tempfile.TemporaryDirectory(prefix="harness-openspec-") as directory:
        client_root = Path(directory)
        control.record_openspec(change_id=change_id, state="initializing", artifact_hashes={})
        prepare_client_workspace(client_root, profile, base_openspec, cli)
        control.record_event("openspec_init", "passed", change_id=change_id)
        control.record_openspec(change_id=change_id, state="planning")
        control.check_cancel()
        plan = plan_client_change(
            cli, client_root, change_id, story, profile, spec,
            original_source[:agent_config["limits"]["source_excerpt_chars"]], models,
            check_cancel=control.check_cancel,
            on_artifact=control.record_openspec_artifact,
        )
        control.record_openspec(change_id=change_id, state="validated", artifact_hashes=plan.hashes)
        control.record_event("openspec_validate", "passed", change_id=change_id)
        control.check_cancel()
        return _implement_planned_story(story, profile, github, models, sandbox_verify, control, agent_config, editor, path, spec, branch, base_sha, original, source_sha, original_source, plan, cli, client_root, base_openspec)


def _implement_planned_story(story, profile, github, models, sandbox_verify, control, agent_config, editor, path, spec, branch, base_sha, original, source_sha, original_source, plan, cli, client_root, base_openspec) -> RunReport:
    developer = _json_response(models, "developer", json.dumps({"task": agent_config["tasks"]["developer"], "story": story.model_dump(), "expected_expression": spec.expression, "source_excerpt": original_source[:agent_config["limits"]["source_excerpt_chars"]], "openspec_change": plan.change_id, "openspec_artifacts": plan.artifacts}, ensure_ascii=False))
    control.record_event("developer", "passed" if developer.get("expression") == spec.expression else "rejected")
    if developer.get("expression") != spec.expression:
        raise ValueError("La expresión propuesta no coincide con la regla validada")
    control.check_cancel()
    updated = editor.edit(original, profile, spec)
    editor.validate(updated, profile, spec)
    sandbox_passed = sandbox_verify(spec)
    control.record_event("sandbox", "passed" if sandbox_passed else "failed")
    if not sandbox_passed:
        raise ValueError("Falló la validación remota en sandbox")
    control.check_cancel()
    diff = "\n".join(difflib.unified_diff(original.splitlines(), updated.splitlines(), fromfile=path, tofile=path, lineterm=""))
    if not diff:
        raise ValueError("La HU no produjo un cambio nuevo frente a la rama base")
    control.record_changed_files([path])
    verifier = _json_response(models, "verifier", json.dumps({"task": agent_config["tasks"]["verifier"], "story": story.model_dump(), "diff": diff, "openspec_change": plan.change_id, "openspec_artifacts": plan.artifacts, "remote_check": "three synthetic SQL rows: positive, zero, NULL passed"}, ensure_ascii=False))
    control.record_event("verifier", "passed" if verifier.get("approved") is True else "rejected")
    if verifier.get("approved") is not True:
        raise ValueError("El verificador rechazó el cambio")
    control.check_cancel()
    mark_tasks_complete(client_root, plan.change_id)
    cli.archive(client_root, plan.change_id)
    openspec_files = collect_changed_openspec(client_root, profile, base_openspec)
    files = {path: (updated, source_sha), **openspec_files}
    control.record_changed_files(sorted(files))
    published_hashes = {name: hashlib.sha256(content.encode("utf-8")).hexdigest() for name, (content, _sha) in openspec_files.items()}
    control.record_openspec(change_id=plan.change_id, state="archived", artifact_hashes=plan.hashes, prepared_files=sorted(openspec_files), prepared_hashes=published_hashes)
    control.record_event("openspec_archive", "passed", change_id=plan.change_id)
    costs = [getattr(call, "cost_usd", None) for call in getattr(models, "calls", [])]
    model_cost = sum(costs, Decimal(0)) if costs and all(cost is not None for cost in costs) else None
    body = (
        f"## HU {story.id}\n{story.title}\n\n"
        f"- Rama base: `{profile.base_branch}` @ `{base_sha}`\n"
        f"- Cambio: `{spec.output_column} = {spec.numerator} / {spec.denominator}`, NULL para denominador cero o NULL.\n"
        f"- OpenSpec: `{plan.change_id}` inicializado, validado y archivado en el repositorio cliente.\n"
        "- Gates: sintaxis Python, expresión exacta, prueba remota con tres filas sintéticas y revisión de modelo.\n"
        "- Límite: la prueba SQL no ejecuta el notebook PySpark completo.\n"
        f"- Costo estimado de modelos: {model_cost if model_cost is not None else 'uso no reportado'} USD.\n"
        "- Validación humana pendiente; sin merge ni despliegue del cliente.\n"
    )
    control.begin_publication()
    pr_url = github.create_feature_pr(profile.repository, branch, profile.base_branch, story.title, body, base_sha, files, on_progress=control.record_publication)
    control.record_openspec(state="published", published_files=sorted(openspec_files), published_hashes=published_hashes)
    pr_checks = github.pr_check_status(profile.repository, branch) if hasattr(github, "pr_check_status") else "unavailable"
    return RunReport(story.id, base_sha, branch, pr_url, sorted(files), diff, model_cost, "passed", pr_checks)
