"""A narrow, idempotent edit for the approved Silver pilot."""

from __future__ import annotations

import json

MEASURE = "margen_sobre_costo_pct"
EXPRESSION = "safe_divide(F.col('margen_bruto'), F.col('costo_total'))"


def _target_cell(notebook: dict) -> dict:
    matches = [
        cell
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
        and "fact_ventas_cabecera" in "".join(cell.get("source", []))
        and "def derive(" in "".join(cell.get("source", []))
    ]
    if len(matches) != 1:
        raise ValueError("Se esperaba exactamente una celda de derivación Silver comercial")
    return matches[0]


def extract_pilot_source(notebook_text: str) -> str:
    return "".join(_target_cell(json.loads(notebook_text))["source"])


def apply_pilot_measure(notebook_text: str) -> str:
    notebook = json.loads(notebook_text)
    cell = _target_cell(notebook)
    source = cell["source"]
    full_source = "".join(source)
    if MEASURE in full_source:
        expected = f".withColumn('{MEASURE}', {EXPRESSION})"
        if full_source.count(expected) != 1:
            raise ValueError("La medida ya existe con una definición diferente")
        return notebook_text
    if "def safe_divide(" not in full_source:
        raise ValueError("No se encontró safe_divide")
    anchors = [i for i, line in enumerate(source) if ".withColumn('margen_pct'," in line]
    if len(anchors) != 1:
        raise ValueError("No se encontró un único margen_pct")
    index = anchors[0]
    if "fact_ventas_cabecera" not in "".join(source[max(0, index - 4):index]):
        raise ValueError("margen_pct fuera de fact_ventas_cabecera")
    next_line = source[index + 1] if index + 1 < len(source) else ""
    indent = next_line[: len(next_line) - len(next_line.lstrip())] or "                "
    source.insert(index + 1, f"{indent}.withColumn('{MEASURE}', {EXPRESSION})\n")
    newline = "\r\n" if "\r\n" in notebook_text else "\n"
    indent_json = 1 if newline + " \"cells\"" in notebook_text else None
    serialized = json.dumps(notebook, indent=indent_json, ensure_ascii=False)
    return serialized.replace("\n", newline)
