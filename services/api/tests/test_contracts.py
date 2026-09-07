import json
from pathlib import Path

from pydantic import TypeAdapter

from smart_basket import schemas

ROOT = Path(__file__).resolve().parents[3]


def test_all_fixtures_validate_against_executable_models():
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {
        "user-context.json", "planning-request.json", "run-queued.json",
        "planning-result.json", "product-candidates.json", "run-failed.json",
        "validation-error.json", "cart-preview.json", "cart-success.json",
        "cart-partial.json", "cart-failed.json", "fatsecret-preview.json",
        "fatsecret-success.json", "fatsecret-partial.json", "fatsecret-failed.json",
        "fatsecret-unmatched.json",
    }
    for fixture, contract in manifest.items():
        data = json.loads((ROOT / "fixtures" / fixture).read_text(encoding="utf-8"))
        model = getattr(schemas, contract["model"])
        TypeAdapter(list[model] if contract["many"] else model).validate_python(data)


def test_http_schema_uses_camel_case_and_400_validation(client):
    schema = client.get("/openapi.json").json()
    properties = schema["components"]["schemas"]["PlanningRequest"]["properties"]
    assert "budgetMinor" in properties and "budget_minor" not in properties
    assert "400" in schema["paths"]["/api/plans"]["post"]["responses"]
    assert "422" not in schema["paths"]["/api/plans"]["post"]["responses"]
