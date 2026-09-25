import json

import pytest
from harness.notebook_edit import apply_pilot_measure, extract_pilot_source


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
    updated = apply_pilot_measure(original)
    source = extract_pilot_source(updated)
    assert ".withColumn('margen_sobre_costo_pct', safe_divide(F.col('margen_bruto'), F.col('costo_total')))" in source
    assert source.count("margen_sobre_costo_pct") == 1
    assert "tiene_campana" in source
    assert apply_pilot_measure(updated) == updated


def test_missing_target_fails_closed():
    with pytest.raises(ValueError):
        apply_pilot_measure(fixture_notebook().replace("fact_ventas_cabecera", "other"))


def test_pilot_source_compiles():
    source = extract_pilot_source(apply_pilot_measure(fixture_notebook()))
    compile(source, "pilot_notebook", "exec")
