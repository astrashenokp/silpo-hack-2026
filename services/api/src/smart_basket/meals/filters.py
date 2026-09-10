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
    "vegan": {
        "display": "Vegan",
        "edamam_health": ("vegan",),
    },
    "paleo": {
        "display": "Paleo",
        "edamam_health": ("paleo",),
    },
    "high-protein": {
        "display": "High-protein",
        "edamam_health": ("high-protein",),
    },
    "high-fiber": {
        "display": "High-fiber",
        "edamam_health": ("high-fiber",),
    },
}

RESTRICTION_LABELS = {
    "peanut-free": {
        "display": "Peanut-free",
        "edamam_health": ("peanut-free",),
    },
    "gluten-free": {
        "display": "Gluten-free",
        "edamam_health": ("gluten-free",),
    },
    "dairy-free": {
        "display": "Dairy-free",
        "edamam_health": ("dairy-free",),
    },
    "tree-nut-free": {
        "display": "Tree-nut-free",
        "edamam_health": ("tree-nut-free",),
    },
    "shellfish-free": {
        "display": "Shellfish-free",
        "edamam_health": ("shellfish-free",),
    },
    "soy-free": {
        "display": "Soy-free",
        "edamam_health": ("soy-free",),
    },
    "egg-free": {
        "display": "Egg-free",
        "edamam_health": ("egg-free",),
    },
    "pork-free": {
        "display": "Pork-free",
        "edamam_health": ("pork-free",),
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
