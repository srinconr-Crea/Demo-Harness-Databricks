from decimal import Decimal

import pytest
from harness.contracts import ClientProfile, Story, estimate_cost


def valid_story():
    return {
        "id": "NP-001",
        "title": "Margen sobre costo en Silver comercial",
        "architecture": "Silver comercial en notebook existente",
        "source_target": "fact_ventas_cabecera -> misma tabla Silver",
        "business_rules": "margen_bruto / costo_total; NULL si costo es cero o nulo",
        "nonfunctional": "No modificar jobs ni datos actuales",
        "validation": "Probar costo positivo, cero y nulo",
    }


def test_story_requires_all_five_manual_sections():
    data = valid_story()
    data["validation"] = " "
    with pytest.raises(ValueError):
        Story.model_validate(data)


def test_profile_restricts_path_and_branch():
    profile = ClientProfile(
        repository="srinconr-Crea/Naturapet_DLH",
        base_branch="develop",
        allowed_paths=["notebooks/comercial/silver/"],
    )
    assert profile.allows("notebooks/comercial/silver/04_business_derivations.ipynb")
    assert not profile.allows(".github/workflows/databricks-cicd.yml")
    assert profile.feature_branch(Story.model_validate(valid_story())) == "feature/np-001-margen-sobre-costo-en-silver-comercial"


def test_cost_uses_independent_input_and_output_rates():
    assert estimate_cost(1000, 200, Decimal("0.000001"), Decimal("0.000005")) == Decimal("0.002000")


def test_cost_missing_usage_stays_unknown():
    assert estimate_cost(None, 200, Decimal("0.001"), Decimal("0.005")) is None
