"""Meal preference and hard-restriction mappings owned by Sofiia."""

from __future__ import annotations

from dataclasses import dataclass


class UnsupportedMealFilter(ValueError):
    """Raised when a hard food constraint cannot be represented safely."""


@dataclass(frozen=True)
class MealFilters:
    preferences: tuple[str, ...]
    restrictions: tuple[str, ...]
    edamam_health_labels: tuple[str, ...]


PREFERENCE_LABELS = {
    "vegetarian": {
        "display": "Vegetarian",
        "edamam_health": ("vegetarian",),
    },
}

RESTRICTION_LABELS = {
    "peanut-free": {
        "display": "Peanut-free",
        "edamam_health": ("peanut-free",),
    },
}


def resolve_meal_filters(request, effective_context) -> MealFilters:
    """Merge explicit request labels with trusted context labels.

    Explicit UI values and saved context can both contribute constraints. Unknown
    hard restrictions fail closed because pretending a provider filter exists is
    unsafe. Preferences also fail closed here so UI/backend mappings drift loudly.
    """

    preferences = _dedupe([
        *(getattr(effective_context, "preferences", []) or []),
        *request.preferences,
    ])
    restrictions = _dedupe([
        *(getattr(effective_context, "restrictions", []) or []),
        *request.restrictions,
    ])

    unsupported_preferences = sorted(set(preferences) - set(PREFERENCE_LABELS))
    unsupported_restrictions = sorted(set(restrictions) - set(RESTRICTION_LABELS))
    if unsupported_preferences:
        raise UnsupportedMealFilter(
            "Unsupported meal preferences: " + ", ".join(unsupported_preferences)
        )
    if unsupported_restrictions:
        raise UnsupportedMealFilter(
            "Unsupported hard restrictions: " + ", ".join(unsupported_restrictions)
        )

    health_labels: list[str] = []
    for label in preferences:
        health_labels.extend(PREFERENCE_LABELS[label]["edamam_health"])
    for label in restrictions:
        health_labels.extend(RESTRICTION_LABELS[label]["edamam_health"])

    return MealFilters(
        preferences=tuple(preferences),
        restrictions=tuple(restrictions),
        edamam_health_labels=tuple(_dedupe(health_labels)),
    )


def _dedupe(labels: list[str]) -> list[str]:
    return list(dict.fromkeys(label for label in labels if label))
