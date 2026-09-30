"""Static validators and trusted impact selection, never model-selected commands."""

import json
from pathlib import Path

import tomllib
import yaml

from .repository_policy import matches, safe_target

ADAPTERS = {
    ".py": "python_compile",
    ".sql": "sql_lint",
    ".ipynb": "notebook_validate",
    ".yaml": "yaml_validate",
    ".yml": "yaml_validate",
    ".json": "json_validate",
    ".toml": "toml_validate",
    ".md": "markdown_structure",
    ".txt": "text_validate",
}


def validation_plan(profile, paths):
    policy = profile.general_patch
    if policy is None:
        raise ValueError("Falta política general de pruebas")
    selected, targets = [], set(policy.test_paths)
    executable = False
    for path in paths:
        if not profile.allows_code(path):
            raise ValueError("Ruta de prueba fuera del perfil")
        suffix = Path(path).suffix.lower()
        adapter = ADAPTERS.get(suffix)
        # Existing bounded profiles used python_compile for notebooks.
        if (
            suffix == ".ipynb"
            and adapter not in policy.test_adapters
            and profile.repository_policy.scope == "prefixes"
        ):
            adapter = "python_compile"
        if adapter is None or adapter not in policy.test_adapters:
            raise ValueError("El tipo de archivo no tiene un validador obligatorio")
        selected.append(
            {
                "adapter": adapter,
                "path": path,
                "reason": "tipo de archivo o eliminación",
            }
        )
        executable |= suffix not in {".md", ".txt"}
        for rule in policy.impact_rules:
            if any(matches(path, prefix) for prefix in rule.paths):
                targets.update(rule.test_paths)
                executable |= bool(rule.test_paths)
                selected.extend(
                    {"adapter": a, "path": path, "reason": "impacto configurado"}
                    for a in rule.adapters
                )
    bundle = any(
        any(matches(p, prefix) for prefix in policy.bundle_paths) for p in paths
    )
    if bundle and (
        "databricks_bundle_validate" in policy.test_adapters
        or profile.repository_policy.scope == "repository"
    ):
        if (
            "databricks_bundle_validate" not in policy.test_adapters
            or not policy.bundle_target
        ):
            raise ValueError("Falta validación obligatoria de bundle")
        selected.append(
            {
                "adapter": "databricks_bundle_validate",
                "reason": "bundle o recursos afectados",
            }
        )
    if executable:
        if "pytest_sandbox" not in policy.test_adapters or not targets:
            raise ValueError(
                "Los cambios de código requieren un Job sandbox dedicado con pruebas funcionales"
            )
        selected.append(
            {"adapter": "pytest_sandbox", "reason": "comportamiento del componente"}
        )
    return {
        "checks": selected,
        "test_paths": sorted(targets),
        "bundle_target": policy.bundle_target if bundle else None,
        "requires_job": executable
        or any(c["adapter"] == "databricks_bundle_validate" for c in selected),
    }


def sql_validate(content):
    import sqlglot
    from sqlglot import exp

    statements = sqlglot.parse(
        content, read="databricks", error_level=sqlglot.ErrorLevel.RAISE
    )
    if not any(s is not None for s in statements) or any(
        isinstance(s, exp.Command) for s in statements
    ):
        raise ValueError("SQL vacío o construcción sin cobertura del parser Databricks")


def notebook_validate(content):
    import nbformat

    raw = json.loads(content)
    if (
        not isinstance(raw, dict)
        or raw.get("nbformat") != 4
        or not isinstance(raw.get("nbformat_minor"), int)
        or not isinstance(raw.get("metadata"), dict)
        or not isinstance(raw.get("cells"), list)
    ):
        raise ValueError("Notebook sin formato, versión, metadata o celdas válidas")
    notebook = nbformat.reads(content, as_version=4)
    nbformat.validate(notebook)
    default = notebook.metadata.get("language_info", {}).get("name", "python").lower()
    for cell in notebook.cells:
        if cell.cell_type != "code" or not cell.source.strip():
            continue
        source = cell.source
        lines = source.splitlines()
        language = default
        if lines[0].startswith("%"):
            language = lines.pop(0).strip().lstrip("%").lower()
            if language in {"md", "markdown"}:
                continue
            source = "\n".join(lines)
        if language == "python":
            if any(
                line.lstrip().startswith(("%", "!")) for line in source.splitlines()
            ):
                raise ValueError("Magia de notebook sin cobertura obligatoria")
            compile(source, "<notebook>", "exec")
        elif language == "sql":
            sql_validate(source)
        else:
            raise ValueError("Lenguaje de notebook sin cobertura obligatoria")


def validate_file(root, path, adapter, schemas):
    target = safe_target(root, path)
    if not target.exists():
        return f"Archivo eliminado: {path}"
    raw = target.read_bytes()
    if b"\0" in raw:
        raise ValueError("Contenido binario no admitido")
    content = raw.decode("utf-8")
    parsed = None
    if adapter == "python_compile" and target.suffix != ".ipynb":
        compile(content, path, "exec")
    elif adapter == "notebook_validate" or target.suffix == ".ipynb":
        notebook_validate(content)
    elif adapter == "sql_lint":
        sql_validate(content)
    elif adapter == "yaml_validate":
        parsed = yaml.safe_load(content)
    elif adapter == "json_validate":
        parsed = json.loads(content)
    elif adapter == "toml_validate":
        parsed = tomllib.loads(content)
    elif adapter == "markdown_structure":
        if not any(line.startswith("# ") for line in content.splitlines()):
            raise ValueError("Markdown sin título principal")
    elif adapter != "text_validate":
        raise ValueError("Adaptador estático desconocido")
    if path in schemas:
        import jsonschema

        schema = schemas[path]

        # Do not let untrusted schemas cause HTTP or filesystem reference resolution.
        def check_refs(value):
            if isinstance(value, dict):
                if any(
                    key in value and not str(value[key]).startswith("#")
                    for key in ("$ref", "$dynamicRef", "$recursiveRef")
                ):
                    raise ValueError("Referencia de esquema externa no admitida")
                for child in value.values():
                    check_refs(child)
            elif isinstance(value, list):
                for child in value:
                    check_refs(child)

        check_refs(schema)
        jsonschema.validate(parsed, schema)
    return f"{adapter}: válido: {path}"
