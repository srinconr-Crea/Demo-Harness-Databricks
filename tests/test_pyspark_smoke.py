"""Execute the edited target cell against synthetic Spark rows in CI."""

import pytest
from harness.notebook_edit import apply_safe_ratio, extract_target_source
from test_notebook_edit import fixture_notebook, measure, strategy

pyspark = pytest.importorskip("pyspark")
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def test_transformed_derive_positive_zero_and_null():
    source = extract_target_source(apply_safe_ratio(fixture_notebook(), strategy(), measure()), strategy())
    namespace = {"F": F}
    exec(compile(source, "synthetic_notebook", "exec"), namespace)  # noqa: S102 - static fixture and deterministic editor
    spark = SparkSession.builder.master("local[1]").appName("harness-safe-ratio-test").getOrCreate()
    try:
        frame = spark.createDataFrame([
            (20.0, 10.0, 5.0, "campaign"),
            (20.0, 10.0, 0.0, None),
            (20.0, 10.0, None, None),
        ], ["margen_bruto", "costo_total", "base_neta_sin_iva", "campana_id"])
        rows = namespace["derive"]("fact_ventas_cabecera", frame).select("costo_sobre_venta_pct").collect()
        assert [row[0] for row in rows] == [2.0, None, None]
    finally:
        spark.stop()
