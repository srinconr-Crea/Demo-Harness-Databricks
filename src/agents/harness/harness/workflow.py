"""Fail-closed workflow for configured, deterministic edit strategies."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from decimal import Decimal

from .contracts import ClientProfile, Story, parse_ratio_story
from .notebook_edit import apply_safe_ratio, extract_target_source


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


def _json_response(models, role: str, prompt: str) -> dict:
    response = models.complete(role, prompt)
    body = response.text.strip()
    if body.startswith("```json\n") and body.endswith("```"):
        body = body[len("```json\n"):-3].strip()
    elif body.startswith("```\n") and body.endswith("```"):
        body = body[len("```\n"):-3].strip()
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError(f"Salida no JSON del rol {role}") from error
    if not isinstance(value, dict):
        raise TypeError(f"Salida inesperada del rol {role}")
    return value


def run_story(story: Story, profile: ClientProfile, github, models, sandbox_verify) -> RunReport:
    strategy = profile.strategy
    if strategy is None or strategy.kind != "silver_safe_ratio":
        raise ValueError("No existe un editor validado para este perfil")
    path = strategy.notebook
    if not profile.allows(path):
        raise ValueError("El notebook queda fuera de las rutas permitidas")
    spec = parse_ratio_story(story, profile)
    branch = profile.feature_branch(story)
    base_sha = github.base_sha(profile.base_branch)
    original, source_sha = github.read_file(path, ref=base_sha)
    original_source = extract_target_source(original, strategy)
    analyst = _json_response(models, "analyst", json.dumps({"task": "Confirma que la HU pide una sola razón segura en el notebook configurado; responde valid y notes", "story": story.model_dump(), "path": path, "source_excerpt": original_source[:12000]}, ensure_ascii=False))
    if analyst.get("valid") is not True:
        raise ValueError("El analista no aprobó el alcance de la HU")
    developer = _json_response(models, "developer", json.dumps({"task": "Confirma la expresión Python exacta como expression; no cambies otros campos", "story": story.model_dump(), "expected_expression": spec.expression, "source_excerpt": original_source[:12000]}, ensure_ascii=False))
    if developer.get("expression") != spec.expression:
        raise ValueError("La expresión propuesta no coincide con la regla validada")
    updated = apply_safe_ratio(original, strategy, spec)
    updated_source = extract_target_source(updated, strategy)
    compile(updated_source, path, "exec")
    if updated_source.count(f".withColumn('{spec.output_column}', {spec.expression})") != 1:
        raise ValueError("La edición no cumple el contrato Silver")
    if not sandbox_verify(spec):
        raise ValueError("Falló la validación remota en sandbox")
    diff = "\n".join(difflib.unified_diff(original.splitlines(), updated.splitlines(), fromfile=path, tofile=path, lineterm=""))
    if not diff:
        raise ValueError("La HU no produjo un cambio nuevo frente a la rama base")
    verifier = _json_response(models, "verifier", json.dumps({"task": "Revisa el diff y las pruebas. Responde approved boolean y notes", "story": story.model_dump(), "diff": diff, "remote_check": "three synthetic SQL rows: positive, zero, NULL passed"}, ensure_ascii=False))
    if verifier.get("approved") is not True:
        raise ValueError("El verificador rechazó el cambio")
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
    pr_url = github.create_feature_pr(profile.repository, branch, profile.base_branch, story.title, body, base_sha, {path: (updated, source_sha)})
    return RunReport(story.id, base_sha, branch, pr_url, [path], diff, model_cost, "passed")
