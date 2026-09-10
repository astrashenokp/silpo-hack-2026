"""Sofiia's meal planning boundary."""

from .filters import PREFERENCE_LABELS, RESTRICTION_LABELS
from .planner import build_meal_plan


def supported_labels() -> dict:
    """Return the currently supported preference and restriction machine labels.

    Uliana and Ksiusha can use this to render the UI list or validate
    programmatically without importing internal filter constants.
    """
    return {
        "preferences": sorted(PREFERENCE_LABELS),
        "restrictions": sorted(RESTRICTION_LABELS),
    }


__all__ = ["build_meal_plan", "supported_labels"]
