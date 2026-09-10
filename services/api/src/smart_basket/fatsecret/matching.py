"""Conservative FatSecret food/serving matching for one personal portion."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Awaitable, Callable, Mapping

from smart_basket.schemas import (
    FatSecretCandidate,
    FatSecretItem,
    FatSecretPreviewMeal,
    UnresolvedFood,
)

DEMO_FOODS = {"oats": "Dry oats", "rice": "Dry rice", "lentils": "Dry lentils"}
DelegatedCall = Callable[[str, Mapping[str, object] | None], Awaitable[dict[str, Any]]]


def _objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _text(value: Any) -> str:
    return " ".join(re.findall(r"[\w]+", str(value).casefold(), flags=re.UNICODE))


def _basis(value: Any) -> str | None:
    tokens = set(_text(value).split())
    if tokens & {"cooked", "boiled", "steamed", "baked"}:
        return "cooked"
    if tokens & {"raw", "dry", "dried", "uncooked"}:
        return "uncooked"
    return None


def _food_results(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    root = payload.get("foods_search") or payload.get("foods") or {}
    if not isinstance(root, dict):
        return []
    results = root.get("results", root)
    if not isinstance(results, dict):
        return []
    return _objects(results.get("food"))


def _servings(food: Mapping[str, Any]) -> list[dict[str, Any]]:
    value = food.get("servings", {})
    if isinstance(value, dict):
        value = value.get("serving")
    return _objects(value)


def _candidate_score(source_name: str, food: Mapping[str, Any]) -> float:
    source = _text(source_name)
    candidate = _text(food.get("food_name", ""))
    if not source or not candidate:
        return 0
    source_basis, candidate_basis = _basis(source), _basis(candidate)
    if source_basis and candidate_basis and source_basis != candidate_basis:
        return 0
    preparation = {
        "raw", "dry", "dried", "uncooked", "cooked", "boiled", "steamed",
        "baked", "plain", "fresh",
    }
    source_core = " ".join(token for token in source.split() if token not in preparation)
    candidate_core = " ".join(token for token in candidate.split() if token not in preparation)
    if source_core == candidate_core:
        score = 1.0
    else:
        source_tokens, candidate_tokens = set(source_core.split()), set(candidate_core.split())
        if source_tokens and source_tokens <= candidate_tokens:
            score = max(0.82, 0.94 - 0.02 * len(candidate_tokens - source_tokens))
        else:
            score = SequenceMatcher(None, source_core, candidate_core).ratio()
    if source_basis and candidate_basis == source_basis:
        score += 0.04
    return score


def _select_food(source_name: str, foods: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    generic = [food for food in foods if str(food.get("food_type", "")).casefold() == "generic"]
    if generic:
        foods = generic
    ranked = sorted(
        ((_candidate_score(source_name, food), food) for food in foods),
        key=lambda pair: (pair[0], pair[1].get("food_type") == "Generic"),
        reverse=True,
    )
    if not ranked or ranked[0][0] < 0.82:
        return None, "No sufficiently close FatSecret food match was found."
    if (
        len(ranked) > 1
        and ranked[1][0] >= 0.82
        and ranked[0][0] - ranked[1][0] < 0.05
        and str(ranked[0][1].get("food_id")) != str(ranked[1][1].get("food_id"))
    ):
        names = ", ".join(str(pair[1].get("food_name", "unknown")) for pair in ranked[:3])
        return None, f"FatSecret returned ambiguous food matches: {names}."
    return ranked[0][1], None


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _select_serving(
    source_name: str,
    source_unit: str,
    source_quantity: float,
    servings: list[dict[str, Any]],
) -> tuple[dict[str, Any], float, float] | None:
    compatible: list[tuple[int, dict[str, Any], float, float]] = []
    source_basis = _basis(source_name)
    for serving in servings:
        serving_id = serving.get("serving_id")
        base_units = _float(serving.get("number_of_units")) or 1.0
        if serving_id in (None, ""):
            continue
        description = _text(serving.get("serving_description", ""))
        serving_basis = _basis(description)
        if source_basis and serving_basis and source_basis != serving_basis:
            continue
        if source_unit in {"g", "ml"}:
            metric_amount = _float(serving.get("metric_serving_amount"))
            metric_unit = str(serving.get("metric_serving_unit", "")).casefold()
            if metric_amount is None or metric_unit != source_unit:
                continue
            number_of_units = source_quantity / metric_amount * base_units
            direct_metric = _text(serving.get("measurement_description", "")) == source_unit
            score = (2 if direct_metric else 1) + (2 if source_basis and serving_basis == source_basis else 0)
            compatible.append((score, serving, number_of_units, base_units))
        elif source_unit == "piece":
            measurement = _text(serving.get("measurement_description", ""))
            if not (description.startswith("1 ") and measurement in {"piece", "item", "serving", "whole"}):
                continue
            compatible.append((1, serving, source_quantity, base_units))
    if not compatible:
        return None
    _, serving, number_of_units, base_units = max(compatible, key=lambda item: item[0])
    return serving, number_of_units, base_units


async def match_live_personal_portion(
    meal: Any,
    call: DelegatedCall,
    selections: Mapping[str, tuple[str, str]] | None = None,
) -> FatSecretPreviewMeal:
    items: list[FatSecretItem] = []
    unresolved: list[UnresolvedFood] = []
    total_kcal = 0.0
    kcal_complete = True

    for amount in meal.ingredient_amounts:
        personal_quantity = amount.quantity / meal.servings
        try:
            search = await call("foods.search.v5", {
                "search_expression": amount.name,
                "max_results": 10,
                "food_type": "generic",
            })
        except Exception:
            search = await call("foods.search", {
                "search_expression": amount.name,
                "max_results": 10,
            })
        compatible: list[tuple[dict[str, Any], dict[str, Any], float, float]] = []
        for candidate in _food_results(search)[:5]:
            if not _servings(candidate):
                details = await call("food.get.v5", {"food_id": candidate.get("food_id")})
                detailed = details.get("food")
                if isinstance(detailed, dict):
                    candidate = detailed
            if str(candidate.get("food_type", "")).casefold() == "brand":
                continue
            selected_serving = _select_serving(
                amount.name, amount.unit, personal_quantity, _servings(candidate),
            )
            if selected_serving:
                serving, number_of_units, base_units = selected_serving
                compatible.append((candidate, serving, number_of_units, base_units))

        candidate_models = []
        for candidate, serving, number_of_units, base_units in compatible:
            calories = _float(serving.get("calories"))
            candidate_models.append(FatSecretCandidate(
                food_id=str(candidate["food_id"]),
                serving_id=str(serving["serving_id"]),
                matched_name=str(candidate.get("food_name") or amount.name),
                number_of_units=number_of_units,
                calories=calories * number_of_units / base_units if calories else None,
            ))

        requested = (selections or {}).get(amount.ingredient_id)
        chosen = next((entry for entry in compatible if requested and (
            str(entry[0].get("food_id")), str(entry[1].get("serving_id"))
        ) == requested), None)
        if requested and chosen is None:
            unresolved.append(UnresolvedFood(
                ingredient_id=amount.ingredient_id,
                reason="The selected FatSecret food/serving is no longer available for this ingredient.",
                candidates=candidate_models,
            ))
            continue

        compatible_foods = [entry[0] for entry in compatible]
        food, reason = _select_food(amount.name, compatible_foods) if not requested else (chosen[0], None)
        if food is None:
            unresolved.append(UnresolvedFood(
                ingredient_id=amount.ingredient_id,
                reason=reason or "Food is unresolved.",
                candidates=candidate_models,
            ))
            continue
        selected = (
            (chosen[1], chosen[2], chosen[3])
            if requested and chosen
            else _select_serving(amount.name, amount.unit, personal_quantity, _servings(food))
        )
        if selected is None:
            unresolved.append(UnresolvedFood(
                ingredient_id=amount.ingredient_id,
                reason=f"No verified {amount.unit} serving is available for this FatSecret food.",
            ))
            continue
        serving, number_of_units, base_units = selected
        calories = _float(serving.get("calories"))
        if calories is None:
            kcal_complete = False
        else:
            total_kcal += calories * number_of_units / base_units
        items.append(FatSecretItem(
            ingredient_id=amount.ingredient_id,
            food_id=str(food["food_id"]),
            serving_id=str(serving["serving_id"]),
            matched_name=str(food.get("food_name") or amount.name),
            number_of_units=number_of_units,
            source_quantity=personal_quantity,
            source_unit=amount.unit,
        ))

    if not meal.ingredient_amounts:
        unresolved.append(UnresolvedFood(ingredient_id="unknown", reason="Meal has no ingredient quantities."))
    return FatSecretPreviewMeal(
        meal_id=meal.id,
        title=meal.title,
        source_kcal_per_serving=meal.kcal_per_serving,
        fatsecret_kcal_per_serving=total_kcal if kcal_complete and items else None,
        items=items,
        unresolved=unresolved,
    )


def match_personal_portion(meal: Any, *, force_unmatched: bool = False) -> FatSecretPreviewMeal:
    """Retain the explicitly labelled synthetic matcher for disconnected demos."""

    items, unresolved = [], []
    for amount in meal.ingredient_amounts:
        if (force_unmatched or meal.source != "synthetic" or amount.ingredient_id not in DEMO_FOODS
                or amount.unit != "g" or amount.name != DEMO_FOODS.get(amount.ingredient_id)):
            unresolved.append(UnresolvedFood(ingredient_id=amount.ingredient_id,
                reason="No verified compatible food/serving mapping in the demo catalog."))
            continue
        personal_quantity = amount.quantity / meal.servings
        items.append(FatSecretItem(ingredient_id=amount.ingredient_id,
            food_id=f"demo-food-{amount.ingredient_id}", serving_id="demo-serving-100g-dry",
            matched_name=amount.name, number_of_units=personal_quantity / 100,
            source_quantity=personal_quantity, source_unit=amount.unit))
    if not meal.ingredient_amounts:
        unresolved.append(UnresolvedFood(ingredient_id="unknown", reason="Meal has no ingredient quantities."))
    return FatSecretPreviewMeal(meal_id=meal.id, title=meal.title,
        source_kcal_per_serving=meal.kcal_per_serving, fatsecret_kcal_per_serving=None,
        items=items, unresolved=unresolved)
