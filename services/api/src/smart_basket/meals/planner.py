"""Public meal-plan function consumed by Uliana's orchestrator."""

from __future__ import annotations

import os

from .edamam import (
    EdamamMealPlannerClient,
    EdamamSettings,
    EdamamUnavailable,
    build_edamam_payload,
    collect_assignments,
    map_edamam_plan_response,
)
from .filters import resolve_meal_filters
from .replanning import build_synthetic_replanned_meal_plan
from .synthetic import build_synthetic_meal_plan


def build_meal_plan(request, effective_context):
    filters = resolve_meal_filters(request, effective_context)
    source, settings, fallback_enabled = _meal_provider_settings()

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
        try:
            return _build_edamam_meal_plan(request, filters, settings)
        except EdamamUnavailable as exc:
            if not fallback_enabled:
                raise
            result = build_synthetic_meal_plan(request, filters)
            result["warnings"] = [
                f"Edamam meal source failed ({exc}); synthetic fallback was used.",
                *result["warnings"],
            ]
            return result

    return build_synthetic_meal_plan(request, filters)


def replan_meal_plan(
    request,
    effective_context,
    previous_meals,
    reason,
    preserve_meal_slots=None,
    replace_ingredient=None,
):
    filters = resolve_meal_filters(request, effective_context)
    source, _, fallback_enabled = _meal_provider_settings()

    if source == "edamam":
        if not fallback_enabled:
            raise EdamamUnavailable(
                "Edamam meal replanning is unavailable without synthetic fallback."
            )
        result = build_synthetic_replanned_meal_plan(
            request=request,
            filters=filters,
            previous_meals=previous_meals,
            reason=reason,
            preserve_meal_slots=preserve_meal_slots,
            replace_ingredient=replace_ingredient,
        )
        result["warnings"] = [
            (
                "Live Edamam provider-side replanning is not supported yet; "
                "local meal-level replan fallback was used."
            ),
            *result["warnings"],
        ]
        return result

    return build_synthetic_replanned_meal_plan(
        request=request,
        filters=filters,
        previous_meals=previous_meals,
        reason=reason,
        preserve_meal_slots=preserve_meal_slots,
        replace_ingredient=replace_ingredient,
    )


def _meal_provider_settings():
    settings = EdamamSettings.from_env()
    source = os.getenv("SMART_BASKET_MEALS_SOURCE", "synthetic")
    if source not in {"synthetic", "edamam"}:
        raise EdamamUnavailable("SMART_BASKET_MEALS_SOURCE must be 'synthetic' or 'edamam'.")
    fallback_enabled = os.getenv("EDAMAM_SYNTHETIC_FALLBACK", "true").casefold() in {
        "1",
        "true",
        "yes",
    }
    return source, settings, fallback_enabled


def _build_edamam_meal_plan(request, filters, settings):
    client = EdamamMealPlannerClient(settings)
    payload = build_edamam_payload(request, filters)
    response = client.request_plan(payload)
    assignments = collect_assignments(response)
    recipe_details = {
        assignment.uri: client.request_recipe(assignment.href, assignment.uri)
        for assignment in assignments
    }
    return map_edamam_plan_response(
        response=response,
        recipe_details=recipe_details,
        request_model=request,
        filters=filters,
    )
