"""Public meal-plan function consumed by Uliana's orchestrator."""

from __future__ import annotations

import os

from .edamam import EdamamMealPlannerClient, EdamamSettings, EdamamUnavailable, build_edamam_payload
from .filters import resolve_meal_filters
from .synthetic import build_synthetic_meal_plan


def build_meal_plan(request, effective_context):
    filters = resolve_meal_filters(request, effective_context)
    settings = EdamamSettings.from_env()
    source = os.getenv("SMART_BASKET_MEALS_SOURCE", "synthetic")
    fallback_enabled = os.getenv("EDAMAM_SYNTHETIC_FALLBACK", "true").casefold() in {
        "1",
        "true",
        "yes",
    }

    if source == "edamam" and settings is None:
        if not fallback_enabled:
            raise EdamamUnavailable("Edamam meal source requested but credentials are incomplete.")
        result = build_synthetic_meal_plan(request, filters)
        result["warnings"] = [
            "Edamam meal source was requested, but credentials are incomplete; synthetic fallback was used.",
            *result["warnings"],
        ]
        return result

    if source == "edamam" and settings is not None:
        client = EdamamMealPlannerClient(settings)
        payload = build_edamam_payload(request, filters)
        try:
            client.request_plan(payload)
        except EdamamUnavailable as exc:
            if not fallback_enabled:
                raise
            result = build_synthetic_meal_plan(request, filters)
            result["warnings"] = [
                f"Edamam meal source failed ({exc}); synthetic fallback was used.",
                *result["warnings"],
            ]
            return result
        result = build_synthetic_meal_plan(request, filters)
        result["warnings"] = [
            "Edamam credentials are configured, but provider response mapping is not enabled until account fields are verified.",
            *result["warnings"],
        ]
        result["source"] = "mixed"
        return result

    return build_synthetic_meal_plan(request, filters)
