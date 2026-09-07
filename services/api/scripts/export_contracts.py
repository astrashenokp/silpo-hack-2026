"""Generate portable JSON schemas and synthetic HTTP examples from executable models.

Run from any directory using this service's virtual-environment Python.
Pass --check to detect stale generated contracts/fixtures without writing files.
"""

import argparse
import json
from pathlib import Path
import re

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from smart_basket import schemas
from smart_basket.app import create_app
from smart_basket.catalog.matching import MatchingContext, find_product_candidates
from smart_basket.demo import DemoCatalog

ROOT = Path(__file__).resolve().parents[3]
REQUEST = {"budgetMinor": 180000, "currency": "UAH", "days": 4, "people": 3,
           "caloriesPerPersonPerDay": 2000, "preferences": ["vegetarian"], "restrictions": [],
           "pets": [{"species": "cat", "count": 1}], "includeRecurring": True, "notes": ""}


def artifacts():
    output, manifest = {}, {}
    identities = {}

    def normalize(value):
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        if isinstance(value, str):
            if re.fullmatch(r"demo-.+-[a-f0-9]{32}", value):
                identities.setdefault(value, value.rsplit("-", 1)[0] + f"-{len(identities)+1:03}")
                return identities[value]
            if re.match(r"\d{4}-\d{2}-\d{2}T", value):
                return "2026-09-07T12:00:00+00:00"
        return value

    def add(name, model, value, *, model_name=None, many=False):
        adapter = TypeAdapter(model)
        adapter.validate_python(value)
        output[f"fixtures/{name}.json"] = normalize(value)
        manifest[f"{name}.json"] = {
            "model": model_name or model.__name__,
            "many": many,
        }

    with TestClient(create_app()) as client:
        add("user-context", schemas.UserContext, client.get("/api/context").json())
        add("planning-request", schemas.PlanningRequest, REQUEST)
        initial = client.post("/api/plans", json=REQUEST).json()
        add("run-queued", schemas.RunSnapshot, initial)
        completed = client.get(f"/api/plans/{initial['runId']}").json()
        plan = completed["result"]
        add("planning-result", schemas.PlanningResult, plan)
        requirements = [schemas.IngredientRequirement.model_validate(i) for i in plan["ingredients"]]
        matches = find_product_candidates(requirements, [], MatchingContext(None, DemoCatalog()))
        add("product-candidates", list[schemas.ProductCandidate],
            [c.model_dump() for c in matches.candidates], model_name="ProductCandidate", many=True)
        failed = client.post("/api/plans", json=REQUEST, headers={"X-Demo-Scenario": "failed"}).json()
        add("run-failed", schemas.RunSnapshot, client.get(f"/api/plans/{failed['runId']}").json())
        add("validation-error", schemas.ErrorEnvelope, client.post("/api/plans", json={**REQUEST, "days": 8}).json())
        for outcome in ("success", "partial", "failed"):
            initial = client.post("/api/plans", json=REQUEST).json()
            reference = {"runId": initial["runId"], "version": 1}
            preview = client.post("/api/cart/preview", json=reference, headers={"X-Demo-Scenario": outcome}).json()
            if outcome == "success":
                add("cart-preview", schemas.CartPreview, preview)
            add(f"cart-{outcome}", schemas.CartReceipt, client.post("/api/cart/confirm", json={
                "previewId": preview["previewId"], "idempotencyKey": f"cart-{outcome}"}).json())
            preview = client.post("/api/fatsecret/exports/preview", json={**reference,
                "mealIds": [m["id"] for m in plan["mealPlan"][:2]]}, headers={"X-Demo-Scenario": outcome}).json()
            if outcome == "success":
                add("fatsecret-preview", schemas.FatSecretPreview, preview)
            accepted = client.post("/api/fatsecret/exports/confirm", json={
                "previewId": preview["previewId"], "idempotencyKey": f"export-{outcome}"}).json()
            add(f"fatsecret-{outcome}", schemas.FatSecretExport,
                client.get(f"/api/fatsecret/exports/{accepted['exportId']}").json())
        preview = client.post("/api/fatsecret/exports/preview", json={**reference,
            "mealIds": [plan["mealPlan"][0]["id"]]}, headers={"X-Demo-Scenario": "unmatched"}).json()
        add("fatsecret-unmatched", schemas.FatSecretPreview, preview)
        output["packages/contracts/openapi.json"] = client.get("/openapi.json").json()
    output["fixtures/manifest.json"] = manifest
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    output = artifacts()
    for relative, value in output.items():
        path = ROOT / relative
        content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                mismatches.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if mismatches:
        raise SystemExit("Generated artifacts are stale: " + ", ".join(mismatches))
    print(f"{'Checked' if args.check else 'Generated'} {len(output)} contract and fixture files.")
