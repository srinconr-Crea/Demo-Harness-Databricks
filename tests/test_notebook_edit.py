import json

import pytest
from harness.contracts import RatioSpec, SafeRatioStrategy
from harness.notebook_edit import apply_safe_ratio, extract_target_source


def strategy():
    return SafeRatioStrategy(kind="silver_safe_ratio", notebook="notebooks/a.ipynb", table="fact_ventas_cabecera", anchor_column="margen_pct", allowed_source_columns=["margen_bruto", "costo_total", "base_neta_sin_iva"])


def measure():
    return RatioSpec(output_column="costo_sobre_venta_pct", numerator="costo_total", denominator="base_neta_sin_iva")


def fixture_notebook():
    code = (
        "def safe_divide(numerator, denominator):\n"
        "    return F.when(denominator.isNull() | (denominator == 0), F.lit(None)).otherwise(numerator / denominator)\n"
        "def derive(table_name, df):\n"
        "    if table_name == 'fact_ventas_cabecera':\n"
        "        df = (df.withColumn('margen_pct', safe_divide(F.col('margen_bruto'), F.col('base_neta_sin_iva')))\n"
        "                .withColumn('tiene_campana', F.col('campana_id').isNotNull()))\n"
        "    return df\n"
    )
    return json.dumps({"cells": [{"cell_type": "code", "metadata": {}, "source": code.splitlines(keepends=True), "outputs": [], "execution_count": None}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5})


def test_adds_measure_once_without_changing_other_fields():
    original = fixture_notebook()
    updated = apply_safe_ratio(original, strategy(), measure())
    source = extract_target_source(updated, strategy())
    assert ".withColumn('costo_sobre_venta_pct', safe_divide(F.col('costo_total'), F.col('base_neta_sin_iva')))" in source
    assert source.count("costo_sobre_venta_pct") == 1
    assert "tiene_campana" in source
    assert apply_safe_ratio(updated, strategy(), measure()) == updated


def test_missing_target_fails_closed():
    with pytest.raises(ValueError):
        apply_safe_ratio(fixture_notebook().replace("fact_ventas_cabecera", "other"), strategy(), measure())


def test_pilot_source_compiles():
    source = extract_target_source(apply_safe_ratio(fixture_notebook(), strategy(), measure()), strategy())
    compile(source, "pilot_notebook", "exec")


def test_rejects_conflicting_existing_measure():
    notebook = fixture_notebook().replace("tiene_campana", "costo_sobre_venta_pct")
    with pytest.raises(ValueError, match="definición diferente"):
        apply_safe_ratio(notebook, strategy(), measure())
