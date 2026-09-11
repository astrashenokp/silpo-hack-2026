"""Sofiia's meal planning boundary."""

from .filters import PREFERENCE_LABELS, RESTRICTION_LABELS, display_label_map
from .planner import build_meal_plan, replan_meal_plan


def supported_labels() -> dict:
    """Return supported machine labels for preferences and restrictions.

    Uliana and Ksiusha can use this to render the UI list or validate
    programmatically without importing internal filter constants.
    """
    return {
        "preferences": sorted(PREFERENCE_LABELS),
        "restrictions": sorted(RESTRICTION_LABELS),
    }


def label_display_map() -> dict:
    """Return {label: display_name} dicts for all supported labels."""
    return display_label_map()


__all__ = ["build_meal_plan", "label_display_map", "replan_meal_plan", "supported_labels"]
