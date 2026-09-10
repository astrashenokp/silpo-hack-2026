"""Public meal-plan function consumed by Uliana's orchestrator."""

from __future__ import annotations

import os

from .edamam import EdamamMealPlannerClient, EdamamSettings, build_edamam_payload
from .filters import resolve_meal_filters
from .synthetic import build_synthetic_meal_plan


def build_meal_plan(request, effective_context):
    filters = resolve_meal_filters(request, effective_context)
    settings = EdamamSettings.from_env()

    if os.getenv("SMART_BASKET_MEALS_SOURCE", "synthetic") == "edamam" and settings is not None:
        client = EdamamMealPlannerClient(settings)
        payload = build_edamam_payload(request, filters)
        client.request_plan(payload)
        result = build_synthetic_meal_plan(request, filters)
        result["warnings"] = [
            "Edamam credentials are configured, but provider response mapping is not enabled until account fields are verified.",
            *result["warnings"],
        ]
        result["source"] = "mixed"
        return result

    return build_synthetic_meal_plan(request, filters)
