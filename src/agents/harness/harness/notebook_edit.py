"""Deterministic editor for one safe ratio in a configured Silver notebook."""

from __future__ import annotations

import json

from .contracts import RatioSpec, SafeRatioStrategy


def _target_cell(notebook: dict, strategy: SafeRatioStrategy) -> dict:
    matches = [
        cell for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
        and strategy.table in "".join(cell.get("source", []))
        and "def derive(" in "".join(cell.get("source", []))
    ]
    if len(matches) != 1:
        raise ValueError("Se esperaba exactamente una celda de derivación Silver")
    return matches[0]


def extract_target_source(notebook_text: str, strategy: SafeRatioStrategy) -> str:
    return "".join(_target_cell(json.loads(notebook_text), strategy)["source"])


def apply_safe_ratio(notebook_text: str, strategy: SafeRatioStrategy, spec: RatioSpec) -> str:
    notebook = json.loads(notebook_text)
    cell = _target_cell(notebook, strategy)
    source = cell["source"]
    full_source = "".join(source)
    expected = f".withColumn('{spec.output_column}', {spec.expression})"
    if spec.output_column in full_source:
        if full_source.count(expected) != 1:
            raise ValueError("La medida ya existe con una definición diferente")
        return notebook_text
    if "def safe_divide(" not in full_source:
        raise ValueError("No se encontró safe_divide")
    anchors = [i for i, line in enumerate(source) if f".withColumn('{strategy.anchor_column}'," in line]
    if len(anchors) != 1:
        raise ValueError("No se encontró una columna ancla única")
    index = anchors[0]
    if strategy.table not in "".join(source[max(0, index - 6):index]):
        raise ValueError("La columna ancla está fuera de la tabla configurada")
    next_line = source[index + 1] if index + 1 < len(source) else ""
    indent = next_line[: len(next_line) - len(next_line.lstrip())] or "                "
    source.insert(index + 1, f"{indent}{expected}\n")
    newline = "\r\n" if "\r\n" in notebook_text else "\n"
    indent_json = 1 if newline + " \"cells\"" in notebook_text else None
    serialized = json.dumps(notebook, indent=indent_json, ensure_ascii=False)
    return serialized.replace("\n", newline)
