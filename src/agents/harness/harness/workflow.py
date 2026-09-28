"""Fail-closed workflow for configured, deterministic edit strategies."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from .contracts import ClientProfile, Story, parse_agent_output
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


def run_story(story: Story, profile: ClientProfile, github, models, sandbox_verify, *, control=None, agent_config: dict | None = None) -> RunReport:
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
    branch = profile.feature_branch(story)
    base_sha = github.base_sha(profile.base_branch)
    original, source_sha = github.read_file(path, ref=base_sha)
    control.check_cancel()
    original_source = editor.source(original, profile)
    analyst = _json_response(models, "analyst", json.dumps({"task": agent_config["tasks"]["analyst"], "story": story.model_dump(), "path": path, "source_excerpt": original_source[:agent_config["limits"]["source_excerpt_chars"]]}, ensure_ascii=False))
    control.record_event("analyst", "passed" if analyst.get("valid") is True else "rejected")
    if analyst.get("valid") is not True:
        raise ValueError("El analista no aprobó el alcance de la HU")
    control.check_cancel()
    developer = _json_response(models, "developer", json.dumps({"task": agent_config["tasks"]["developer"], "story": story.model_dump(), "expected_expression": spec.expression, "source_excerpt": original_source[:agent_config["limits"]["source_excerpt_chars"]]}, ensure_ascii=False))
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
    verifier = _json_response(models, "verifier", json.dumps({"task": agent_config["tasks"]["verifier"], "story": story.model_dump(), "diff": diff, "remote_check": "three synthetic SQL rows: positive, zero, NULL passed"}, ensure_ascii=False))
    control.record_event("verifier", "passed" if verifier.get("approved") is True else "rejected")
    if verifier.get("approved") is not True:
        raise ValueError("El verificador rechazó el cambio")
    control.check_cancel()
    costs = [getattr(call, "cost_usd", None) for call in getattr(models, "calls", [])]
    model_cost = sum(costs, Decimal(0)) if costs and all(cost is not None for cost in costs) else None
    body = (
        f"## HU {story.id}\n{story.title}\n\n"
        f"- Rama base: `{profile.base_branch}` @ `{base_sha}`\n"
        f"- Cambio: `{spec.output_column} = {spec.numerator} / {spec.denominator}`, NULL para denominador cero o NULL.\n"
        "- Gates: sintaxis Python, expresión exacta, prueba remota con tres filas sintéticas y revisión de modelo.\n"
        "- Límite: la prueba SQL no ejecuta el notebook PySpark completo.\n"
        f"- Costo estimado de modelos: {model_cost if model_cost is not None else 'uso no reportado'} USD.\n"
        "- Validación humana pendiente; sin merge ni despliegue del cliente.\n"
    )
    control.begin_publication()
    pr_url = github.create_feature_pr(profile.repository, branch, profile.base_branch, story.title, body, base_sha, {path: (updated, source_sha)}, on_progress=control.record_publication)
    pr_checks = github.pr_check_status(profile.repository, branch) if hasattr(github, "pr_check_status") else "unavailable"
    return RunReport(story.id, base_sha, branch, pr_url, [path], diff, model_cost, "passed", pr_checks)
