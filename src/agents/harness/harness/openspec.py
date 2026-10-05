"""OpenSpec CLI adapter for isolated client repository workspaces."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

import yaml

from .contracts import ClientProfile, RatioSpec, Story, StoryRequest, parse_agent_output
from .skills import SkillCatalog, checked_file


class OpenSpecCLI:
    """Run the pinned CLI installed with the Databricks App, without a shell."""

    def __init__(self, *, app_root: Path | None = None, timeout_seconds: int = 45):
        self.app_root = app_root or Path(__file__).resolve().parents[1]
        self.entry = self.app_root / "node_modules" / "@fission-ai" / "openspec" / "bin" / "openspec.js"
        self.timeout_seconds = timeout_seconds

    def _run(self, args: list[str], root: Path) -> str:
        node = shutil.which("node")
        if not node or not self.entry.is_file():
            raise ValueError("OpenSpec CLI o Node no está instalado en la App")
        if not root.is_dir():
            raise ValueError("El workspace OpenSpec no existe")
        env = os.environ.copy()
        env["OPENSPEC_TELEMETRY"] = "0"
        try:
            completed = subprocess.run(
                [node, str(self.entry), *args], cwd=root, env=env,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("OpenSpec excedió el tiempo límite") from error
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:2000]
            raise ValueError(f"OpenSpec falló ({completed.returncode}): {detail}")
        if len(completed.stdout) > 1_000_000 or len(completed.stderr) > 100_000:
            raise ValueError("La salida OpenSpec excede el límite")
        return completed.stdout

    def _json(self, args: list[str], root: Path) -> dict:
        try:
            result = json.loads(self._run(args, root))
        except json.JSONDecodeError as error:
            raise ValueError("OpenSpec devolvió JSON inválido") from error
        if not isinstance(result, dict):
            raise ValueError("OpenSpec devolvió un contrato inesperado")  # noqa: TRY004 - invalid external JSON contract
        return result

    def version(self) -> str:
        return self._run(["--version"], self.app_root).strip()

    def status(self, root: Path, change: str) -> dict:
        return self._json(['status', '--change', change, '--json'], root)

    def inventory(self, root: Path) -> dict:
        return self._json(['list', '--specs', '--json'], root)

    def new_change(self, root: Path, name: str) -> None:
        self._run(["new", "change", name], root)

    def instructions(self, root: Path, artifact: str, change: str) -> dict:
        return self._json(["instructions", artifact, "--change", change, "--json"], root)

    def validate(self, root: Path, change: str) -> None:
        self._run(["validate", change, "--strict"], root)

    def archive(self, root: Path, change: str) -> None:
        self._run(["archive", change, "--yes"], root)


def mark_tasks_complete(root: Path, change: str) -> None:
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}", change) is None:
        raise ValueError("Identificador OpenSpec no válido")
    path = root / "openspec" / "changes" / change / "tasks.md"
    content = path.read_text(encoding="utf-8")
    if "- [ ]" not in content:
        raise ValueError("El cambio OpenSpec no contiene tareas pendientes")
    path.write_text(content.replace("- [ ]", "- [x]"), encoding="utf-8")


def collect_changed_openspec(
    root: Path, profile: ClientProfile, base_files: dict[str, tuple[str, str | None]],
) -> dict[str, tuple[str, str | None]]:
    openspec_root = root / profile.openspec_root
    result: dict[str, tuple[str, str | None]] = {}
    for path in openspec_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not profile.allows_openspec(relative) or not path.resolve().is_relative_to(openspec_root.resolve()):
            raise ValueError("Archivo OpenSpec fuera del prefijo autorizado")
        if not relative.endswith((".md", ".yaml", ".yml", ".gitkeep")):
            raise ValueError("Archivo OpenSpec no admitido para publicación")
        content = path.read_text(encoding="utf-8")
        before = base_files.get(relative)
        if before is None or content != before[0]:
            result[relative] = (content, before[1] if before else None)
    if len(result) > 300 or sum(len(content.encode("utf-8")) for content, _ in result.values()) > 4_000_000:
        raise ValueError("Los artefactos OpenSpec exceden el límite")
    return result


def prepare_client_workspace(
    root: Path,
    profile: ClientProfile,
    base_files: dict[str, tuple[str, str | None]] | None = None,
    cli: OpenSpecCLI | None = None,
) -> SkillCatalog:
    """Require the client's approved OpenSpec tree; a HU never initializes it."""
    if not root.is_dir():
        raise ValueError("El workspace cliente no existe")
    if any(not profile.allows_openspec(path) for path in (base_files or {})):
        raise ValueError("Archivo OpenSpec fuera del prefijo autorizado")
    openspec_root = root / profile.openspec_root
    config_path = openspec_root / "config.yaml"
    if not config_path.is_file() or not (openspec_root / "specs").is_dir() or not (openspec_root / "changes").is_dir():
        raise ValueError("El cliente requiere el PR de preparación OpenSpec integrado en la rama base")
    if config_path.is_symlink() or not config_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Configuración OpenSpec fuera del checkout cliente")
    config = yaml.safe_load(checked_file(root, 'openspec/config.yaml', 131072).decode('utf-8'))
    if not isinstance(config, dict) or config.get("schema") != "spec-driven" or not isinstance(config.get("context"), str) or "store" in config or "references" in config:
        raise ValueError("La configuración OpenSpec cliente no es compatible con el workspace aislado")
    return SkillCatalog(root, profile, (cli or OpenSpecCLI()).version())


def instruction_context(cli, root, change, artifact, profile):
    """Validate concrete CLI paths and deliver dependency bytes, never path authority."""
    change_root = root / 'openspec' / 'changes' / change
    status = cli.status(root, change)
    info = cli.instructions(root, artifact, change)
    for result in (status, info) if artifact != 'archive' else (status,):
        if result.get('schemaName') != 'spec-driven':
            raise ValueError('OpenSpec resolvió un esquema no soportado')
        directory = result.get('changeDir', result.get('changeRoot'))
        if not isinstance(directory, str) or Path(directory).resolve() != change_root.resolve():
            raise ValueError('OpenSpec resolvió una raíz fuera del cliente')
    if artifact in {'apply', 'archive'}:
        if artifact == 'archive' and Path(info.get('root', {}).get('path', '')).resolve() != root.resolve():
            raise ValueError('OpenSpec archive resolvió una raíz fuera del cliente')
        if info.get('state') == 'blocked' or info.get('missingArtifacts'):
            raise ValueError('OpenSpec bloqueado por prerrequisitos ausentes')
        if artifact == 'apply' and info.get('state') != 'ready':
            raise ValueError('OpenSpec apply no está listo')
        paths = [p for group in info.get('contextFiles', {}).values() for p in group]
    else:
        state = next((a for a in status.get('artifacts', []) if a['id'] == artifact), None)
        if not state or state.get('status') not in {'ready', 'done'} or info.get('skipped'):
            raise ValueError('Artefacto OpenSpec bloqueado o no soportado')
        paths = []
        for dep in info.get('dependencies', []):
            if not dep.get('done'):
                raise ValueError('Dependencia OpenSpec ausente')
            pattern = dep['path']
            if Path(pattern).is_absolute() or '..' in Path(pattern).parts or ':' in pattern:
                raise ValueError('Dependencia OpenSpec fuera del cambio')
            paths.extend(str(p) for p in change_root.glob(pattern) if p.is_file())
        output = info.get('resolvedOutputPath', '')
        expected = change_root / ({'proposal': 'proposal.md', 'design': 'design.md',
                                 'tasks': 'tasks.md'}.get(artifact, 'specs/**/*.md'))
        if Path(output).resolve() != expected.resolve():
            raise ValueError('Artefacto OpenSpec fuera del cambio')
    files = {}
    limit = profile.openspec_skills.max_prompt_bytes if profile else 524288
    for raw in paths:
        candidate = Path(raw)
        if not candidate.is_absolute() or not candidate.resolve().is_relative_to(change_root.resolve()):
            raise ValueError('Contexto OpenSpec fuera del cambio')
        if candidate.is_relative_to(root):
            relative = candidate.relative_to(root).as_posix()
        elif candidate.is_relative_to(root.resolve()):
            relative = candidate.relative_to(root.resolve()).as_posix()
        else:
            raise ValueError('Ruta de contexto OpenSpec no canónica')
        if profile and not profile.allows_read(relative):
            raise ValueError('Lectura OpenSpec no autorizada')
        try:
            files[relative] = checked_file(root, relative, limit).decode('utf-8')
        except OSError as error:
            raise ValueError('Dependencia OpenSpec ausente') from error
    if sum(len(v.encode('utf-8')) for v in files.values()) > limit:
        raise ValueError('Dependencias OpenSpec exceden presupuesto')
    return {**info, 'command': ['instructions', artifact, '--change', change, '--json'],
            'dependency_content': files}


def exploration_context(cli, root, profile):
    inventory = cli.inventory(root)
    if Path(inventory.get('root', {}).get('path', '')).resolve() != root.resolve():
        raise ValueError('Inventario OpenSpec fuera del checkout')
    from .repository_policy import valid_relative
    limit = profile.openspec_skills.max_prompt_bytes
    config = checked_file(root, 'openspec/config.yaml', limit).decode('utf-8')
    specs = {}
    for spec in inventory.get('specs', []):
        identifier = spec.get('id', '')
        if not isinstance(identifier, str) or not valid_relative(identifier):
            raise ValueError('Identificador de spec inválido')
        relative = f'openspec/specs/{identifier}/spec.md'
        if not profile.allows_read(relative):
            raise ValueError('Spec sin acceso por perfil')
        specs[relative] = checked_file(root, relative, limit).decode('utf-8')
    if sum(len(v.encode('utf-8')) for v in specs.values()) + len(config.encode('utf-8')) > limit:
        raise ValueError('Contexto OpenSpec excede presupuesto')
    return {**inventory, 'command': ['list', '--specs', '--json'],
            'project_config': config, 'existing_specs': specs}


@dataclass(frozen=True)
class PlanResult:
    change_id: str
    artifacts: dict[str, str]
    hashes: dict[str, str]
    metadata: dict = field(default_factory=dict)


def _planner_validation(function):
    @wraps(function)
    def checked(*args, **kwargs):
        models = inspect.signature(function).bind(*args, **kwargs).arguments['models']
        start = len(getattr(models, 'calls', []))
        try:
            result = function(*args, **kwargs)
        except ValueError as error:
            if hasattr(models, 'mark_response') and len(models.calls) > start:
                call = models.calls[-1]
                category = getattr(error, 'category', 'invalid_contract')
                models.mark_response('planner', call, category)
            raise
        if hasattr(models, 'mark_response'):
            for call in list(models.calls[start:]):
                if call.acceptance in {'parsed', 'normalized'}:
                    models.mark_response('planner', call, 'accepted')
        return result
    return checked


@_planner_validation
def propose_client_change(
    cli: OpenSpecCLI, root: Path, change_id: str, story: StoryRequest,
    models, *, source_summary: str = "", feedback: str | None = None,
    revision: int = 0,
    on_artifact: Callable[[str, str, str], None] | None = None,
    profile: ClientProfile | None = None,
    skill_catalog=None, base_sha=None, on_snapshot=None, context_manager=None,
) -> PlanResult:
    """Generate or revise the four schema artifacts with fixed paths and strict validation."""
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}", change_id) is None:
        raise ValueError("Identificador de cambio OpenSpec no válido")
    change_root = root / "openspec" / "changes" / change_id
    if not change_root.exists():
        cli.new_change(root, change_id)
    output_names = {
        "proposal": "proposal.md",
        "specs": f"specs/{change_id}/spec.md",
        "design": "design.md",
        "tasks": "tasks.md",
    }
    artifacts: dict[str, str] = {}
    hashes: dict[str, str] = {}
    metadata = {}
    from .repo_context import RepoContext, contextual_answer
    repo_context = RepoContext(root, profile, cache=context_manager.cache if context_manager else None,
                               identity=context_manager.identity if context_manager else None) if profile else None
    for artifact, suffix in output_names.items():
        instructions = instruction_context(cli, root, change_id, artifact, profile)
        if instructions.get("schemaName") != "spec-driven" or Path(instructions.get("changeDir", "")).resolve() != change_root.resolve():
            raise ValueError("OpenSpec resolvió un esquema o raíz fuera del cliente")
        target = change_root / Path(suffix)
        if artifact != "specs" and Path(instructions.get("resolvedOutputPath", "")).resolve() != target.resolve():
            raise ValueError("OpenSpec resolvió un artefacto fuera del cambio cliente")
        prompt = {
            "workflow": "update" if feedback else "propose",
            "artifact": artifact,
            "instructions": instructions.get("instruction"),
            "template": instructions.get("template"),
            "client_context": instructions.get("context"),
            "rules": instructions.get("rules"),
            "story": story.model_dump(),
            "source_summary": source_summary if context_manager else source_summary[:12000],
            "feedback": feedback,
            "existing_artifact": (target.read_text(encoding="utf-8") if context_manager else target.read_text(encoding="utf-8")[:50000]) if target.is_file() else None,
            "output_path": suffix,
            "response_format": {"content": "texto Markdown completo del artefacto",
                "summary": "Objetivo, comportamiento esperado y cambios previstos en español",
                "manifest": [{'op': 'create|modify|delete', 'path': 'ruta exacta de código prevista'}]},
            "policy": profile.model_dump() if profile else None,
            "approved_manifest_contract": 'Para proposal de general_patch, manifest y summary son obligatorios. No son el diff real. La aprobación autoriza crear el PR automáticamente después de verificar, sincronizar y archivar.',
        }
        catalog = skill_catalog or (SkillCatalog(root, profile, cli.version()) if profile else None)
        extras = {}
        if catalog:
            prompt, extras = catalog.compose('update' if feedback else 'propose', prompt,
                instructions=instructions, base_sha=base_sha, on_snapshot=on_snapshot)
        else:
            prompt['openspec_instructions'] = instructions
        parsed = contextual_answer(models, 'planner', prompt, repo_context,
            stage='updating' if feedback else 'proposing', revision=revision,
            context_manager=context_manager, phase='update' if feedback else 'propose', **extras)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("content"), str) or not 20 <= len(parsed["content"]) <= 50000:
            raise ValueError("El planner devolvió un artefacto OpenSpec inválido")
        content = parsed["content"].strip() + "\n"
        if artifact == 'proposal' and profile:
            if profile.general_patch:
                manifest, summary = parsed.get('manifest'), parsed.get('summary')
                policy = profile.general_patch
                if not isinstance(summary, str) or not 1 <= len(summary) <= 10000 or not isinstance(manifest, list) or not 1 <= len(manifest) <= policy.max_files:
                    raise ValueError('La propuesta requiere resumen y manifiesto explícitos')
                paths = set()
                for item in manifest:
                    if not isinstance(item, dict) or set(item) != {'op', 'path'} or item['op'] not in policy.operations or not isinstance(item['path'], str) or not profile.allows_code(item['path']) or Path(item['path']).suffix not in policy.extensions or item['path'] in paths:
                        raise ValueError('El manifiesto excede la política del cliente')
                    paths.add(item['path'])
                from .validation import validation_plan
                metadata = {'summary': summary, 'manifest': manifest, 'validation_plan': validation_plan(profile, sorted(paths))}
            else:
                metadata = {'summary': content, 'manifest': [{'op': 'modify', 'path': profile.strategy.notebook}],
                            'validation_plan': {'checks': [{'adapter': 'silver_safe_ratio', 'reason': 'tres filas sintéticas'}]}}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        path = target.relative_to(root).as_posix()
        artifacts[path] = content
        hashes[path] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if on_artifact:
            on_artifact(path, content, hashes[path])
    cli.validate(root, change_id)
    return PlanResult(change_id, artifacts, hashes, metadata)


@_planner_validation
def plan_client_change(
    cli: OpenSpecCLI,
    root: Path,
    change_id: str,
    story: Story,
    profile: ClientProfile,
    spec: RatioSpec,
    source_excerpt: str,
    models,
    *,
    check_cancel: Callable[[], None] | None = None,
    on_artifact: Callable[[str, str, str], None] | None = None,
) -> PlanResult:
    """Ask Sonnet for OpenSpec artifacts, retaining deterministic edit authority."""
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{2,90}", change_id) is None:
        raise ValueError("Identificador de cambio OpenSpec no válido")
    if profile.strategy is None or profile.strategy.kind != "silver_safe_ratio":
        raise ValueError("Estrategia fuera de la política OpenSpec")
    cli.new_change(root, change_id)
    output_names = {
        "proposal": "proposal.md",
        "specs": "specs/silver-safe-ratio/spec.md",
        "design": "design.md",
        "tasks": "tasks.md",
    }
    change_root = root / profile.openspec_root / "changes" / change_id
    artifacts: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for artifact, suffix in output_names.items():
        if check_cancel:
            check_cancel()
        instructions = cli.instructions(root, artifact, change_id)
        if instructions.get("schemaName") != "spec-driven" or Path(instructions.get("changeDir", "")).resolve() != change_root.resolve():
            raise ValueError("OpenSpec resolvió un esquema o raíz fuera del cliente")
        target = change_root / Path(suffix)
        if artifact != "specs" and Path(instructions.get("resolvedOutputPath", "")).resolve() != target.resolve():
            raise ValueError("OpenSpec resolvió un artefacto fuera del cambio cliente")
        prompt = json.dumps({
            "artifact": artifact,
            "instructions": instructions.get("instruction"),
            "template": instructions.get("template"),
            "client_context": instructions.get("context"),
            "rules": instructions.get("rules"),
            "story": story.model_dump(),
            "strategy": profile.strategy.kind,
            "code_path": profile.strategy.notebook,
            "expected_expression": spec.expression,
            "source_excerpt": source_excerpt,
            "output_path": suffix,
            "response_format": {"content": "texto del artefacto", "strategy": profile.strategy.kind, "code_path": profile.strategy.notebook, "expression": spec.expression},
        }, ensure_ascii=False)
        from .repo_context import contextual_answer
        response = contextual_answer(models, 'planner', json.loads(prompt))
        response = parse_agent_output('planner', json.dumps(response, ensure_ascii=False))
        if response["strategy"] != profile.strategy.kind or response["code_path"] != profile.strategy.notebook or response["expression"] != spec.expression or not profile.allows(response["code_path"]):
            raise ValueError("El manifiesto del planner excede la política validada")
        content = response["content"].strip() + "\n"
        path = target.relative_to(root).as_posix()
        if not profile.allows_openspec(path) or not target.resolve().is_relative_to(change_root.resolve()):
            raise ValueError("Ruta de artefacto OpenSpec fuera de política")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        artifacts[path] = content
        hashes[path] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if on_artifact:
            on_artifact(path, content, hashes[path])
    cli.validate(root, change_id)
    return PlanResult(change_id, artifacts, hashes)
