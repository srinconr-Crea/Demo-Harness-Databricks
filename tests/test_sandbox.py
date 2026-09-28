import pytest
from harness.contracts import RatioSpec
from harness.sandbox import verify_safe_ratio


class FakeAPI:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def do(self, method, path, body=None):
        self.calls.append((method, path, body))
        return {"status": {"state": "SUCCEEDED"}, "result": {"data_array": self.rows}}


def test_remote_synthetic_rows_pass_without_ddl():
    api = FakeAPI([["1", "2.0"], ["2", None], ["3", None]])
    assert verify_safe_ratio(api, "sandbox-warehouse-id", RatioSpec(output_column="costo_sobre_venta_pct", numerator="costo_total", denominator="base_neta_sin_iva"))
    assert api.calls[0][1] == "/api/2.0/sql/statements"
    assert "CREATE" not in api.calls[0][2]["statement"].upper()
    assert "costo_sobre_venta_pct" in api.calls[0][2]["statement"]


def test_remote_wrong_result_fails():
    api = FakeAPI([["1", "2.0"], ["2", "0"], ["3", None]])
    with pytest.raises(ValueError):
        verify_safe_ratio(api, "sandbox-warehouse-id", RatioSpec(output_column="costo_sobre_venta_pct", numerator="costo_total", denominator="base_neta_sin_iva"))
