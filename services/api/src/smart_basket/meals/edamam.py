"""Edamam Meal Planner adapter boundary.

The live request shape must be verified against the team's actual Edamam account
before enabling production use. This module keeps credentials and provider data
behind Sofiia's Python boundary and never stores raw recipe payloads as fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import json
import os
from urllib import error, parse, request

from smart_basket.schemas import IngredientAmount, IngredientRequirement, Meal

from .nutrition import (
    ACCURACY_WARNINGS,
    CALORIE_TOLERANCE_PCT,
    build_nutrition_summary,
    calorie_target_for_slot,
    calorie_target_warnings,
)


class EdamamUnavailable(RuntimeError):
    """Raised when Edamam cannot be used for this run."""


@dataclass(frozen=True)
class EdamamSettings:
    app_id: str
    app_key: str
    account_user: str
    base_url: str = "https://api.edamam.com"
    timeout_seconds: float = 8.0

    @classmethod
    def from_env(cls) -> "EdamamSettings | None":
        app_id = os.getenv("EDAMAM_MEAL_PLANNER_APP_ID")
        app_key = os.getenv("EDAMAM_MEAL_PLANNER_APP_KEY")
        account_user = os.getenv("EDAMAM_ACCOUNT_USER")
        if not app_id or not app_key or not account_user:
            return None
        return cls(
            app_id=app_id,
            app_key=app_key,
            account_user=account_user,
            base_url=os.getenv("EDAMAM_MEAL_PLANNER_BASE_URL", "https://api.edamam.com"),
            timeout_seconds=_timeout_from_env(),
        )


def build_edamam_payload(request_model, filters) -> dict:
    payload: dict = {
        "size": request_model.days,
        "plan": {
            "sections": {
                "Breakfast": {},
                "Lunch": {},
                "Dinner": {},
            },
        },
    }
    if filters.edamam_health_labels:
        payload["plan"]["accept"] = {
            "all": [
                {"health": list(filters.edamam_health_labels)},
            ],
        }
    if request_model.calories_per_person_per_day is not None:
        target = request_model.calories_per_person_per_day
        payload["plan"]["fit"] = {
            "ENERC_KCAL": {
                "min": int(target * (1 - CALORIE_TOLERANCE_PCT)),
                "max": int(target * (1 + CALORIE_TOLERANCE_PCT)),
            }
        }
    return payload


def _timeout_from_env() -> float:
    raw = os.getenv("EDAMAM_TIMEOUT_SECONDS", "8")
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise EdamamUnavailable("EDAMAM_TIMEOUT_SECONDS must be a number.") from exc
    if timeout <= 0:
        raise EdamamUnavailable("EDAMAM_TIMEOUT_SECONDS must be positive.")
    return timeout


class EdamamMealPlannerClient:
    def __init__(self, settings: EdamamSettings):
        self.settings = settings

    def request_plan(self, payload: dict) -> dict:
        url = (
            f"{self.settings.base_url.rstrip('/')}/api/meal-planner/v1/"
            f"{self.settings.account_user}/select"
            f"?{parse.urlencode({'app_id': self.settings.app_id, 'app_key': self.settings.app_key})}"
        )
        data = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Edamam-Account-User": self.settings.account_user,
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429:
                raise EdamamUnavailable("Edamam rate limit was reached.") from exc
            raise EdamamUnavailable(f"Edamam returned HTTP {exc.code}.") from exc
        except (TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise EdamamUnavailable("Edamam meal planner is unavailable or returned invalid data.") from exc

    def request_recipe(self, href: str, uri: str) -> dict:
        url = _with_credentials(href, self.settings)
        http_request = request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Edamam-Account-User": self.settings.account_user,
            },
            method="GET",
        )
        try:
            with request.urlopen(http_request, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429:
                raise EdamamUnavailable("Edamam recipe lookup rate limit was reached.") from exc
            raise EdamamUnavailable(f"Edamam recipe lookup for {uri} returned HTTP {exc.code}.") from exc
        except (TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise EdamamUnavailable("Edamam recipe lookup is unavailable or returned invalid data.") from exc


@dataclass(frozen=True)
class EdamamAssignment:
    day: int
    slot: str
    uri: str
    href: str
    link_title: str | None


def collect_assignments(response: dict) -> list[EdamamAssignment]:
    selection = response.get("selection")
    if not isinstance(selection, list):
        raise EdamamUnavailable("Edamam response does not contain a selection list.")

    assignments: list[EdamamAssignment] = []
    for day_index, day in enumerate(selection, start=1):
        sections = day.get("sections") if isinstance(day, dict) else None
        if not isinstance(sections, dict):
            raise EdamamUnavailable("Edamam selection day is missing sections.")
        for section_name, slot in (
            ("Breakfast", "breakfast"),
            ("Lunch", "lunch"),
            ("Dinner", "dinner"),
        ):
            section = sections.get(section_name)
            assignment = _first_assignment(section)
            if assignment is None:
                raise EdamamUnavailable(f"Edamam response is missing {section_name} for day {day_index}.")
            uri, href, title = assignment
            assignments.append(
                EdamamAssignment(
                    day=day_index,
                    slot=slot,
                    uri=uri,
                    href=href,
                    link_title=title,
                )
            )
    return assignments


def map_edamam_plan_response(
    *,
    response: dict,
    recipe_details: dict[str, dict],
    request_model,
    filters,
) -> dict:
    assignments = collect_assignments(response)
    if len(assignments) != request_model.days * 3:
        raise EdamamUnavailable("Edamam response did not cover every requested meal slot.")

    meals: list[Meal] = []
    ingredient_totals: dict[str, dict] = {}
    warnings: list[str] = []

    for assignment in assignments:
        recipe = _extract_recipe(recipe_details[assignment.uri])
        yield_count = _positive_float(recipe.get("yield")) or request_model.people
        if recipe.get("yield") is None:
            warnings.append(
                f"Recipe servings missing for {assignment.uri}; used requested people as serving basis."
            )
        scale = request_model.people / yield_count
        meal_id = f"edamam-day-{assignment.day}-{assignment.slot}-{_short_hash(assignment.uri)}"
        amounts: list[IngredientAmount] = []
        ingredient_ids: list[str] = []

        ingredients = recipe.get("ingredients")
        if not isinstance(ingredients, list) or not ingredients:
            raise EdamamUnavailable(f"Recipe {assignment.uri} has no ingredient list.")
        for index, ingredient in enumerate(ingredients, start=1):
            amount = _ingredient_amount(ingredient, scale)
            ingredient_id = _ingredient_id(ingredient, index)
            ingredient_name = _ingredient_name(ingredient)
            ingredient_ids.append(ingredient_id)
            amounts.append(
                IngredientAmount(
                    ingredient_id=ingredient_id,
                    name=ingredient_name,
                    quantity=amount,
                    unit="g",
                )
            )
            total = ingredient_totals.setdefault(
                ingredient_id,
                {
                    "name": ingredient_name,
                    "search_terms": _search_terms(ingredient),
                    "quantity": 0.0,
                    "meal_ids": [],
                },
            )
            total["quantity"] += amount
            total["meal_ids"].append(meal_id)

        calories = _positive_float(recipe.get("calories"))
        meals.append(
            Meal(
                id=meal_id,
                day=assignment.day,
                slot=assignment.slot,
                title=str(recipe.get("label") or assignment.link_title or "Edamam recipe"),
                servings=request_model.people,
                kcal_per_serving=(calories / yield_count) if calories is not None else None,
                calorie_target=calorie_target_for_slot(
                    request_model.calories_per_person_per_day,
                    assignment.slot,
                ),
                ingredient_ids=ingredient_ids,
                ingredient_amounts=amounts,
                source="edamam",
                source_url=recipe.get("url") or assignment.href,
                attribution="Recipe data powered by Edamam.",
            )
        )

    requirements = [
        IngredientRequirement(
            id=ingredient_id,
            name=data["name"],
            search_terms=data["search_terms"],
            quantity=data["quantity"],
            unit="g",
            meal_ids=data["meal_ids"],
            restrictions=list(filters.restrictions),
        )
        for ingredient_id, data in ingredient_totals.items()
    ]
    nutrition_summary = build_nutrition_summary(request_model, meals)
    warnings.extend(ACCURACY_WARNINGS)
    warnings.extend(calorie_target_warnings(nutrition_summary))

    return {
        "meals": meals,
        "nutrition_summary": nutrition_summary,
        "ingredients": requirements,
        "warnings": warnings,
        "source": "edamam",
    }


def _first_assignment(section: dict | None) -> tuple[str, str, str | None] | None:
    if not isinstance(section, dict):
        return None
    assigned = section.get("assigned")
    link = section.get("_links", {}).get("self", {}) if isinstance(section.get("_links"), dict) else {}
    href = link.get("href")
    if isinstance(assigned, str) and isinstance(href, str):
        return assigned, href, link.get("title")
    subsections = section.get("sections")
    if isinstance(subsections, dict):
        for value in subsections.values():
            found = _first_assignment(value)
            if found is not None:
                return found
    return None


def _extract_recipe(detail: dict) -> dict:
    if isinstance(detail.get("recipe"), dict):
        return detail["recipe"]
    hits = detail.get("hits")
    if isinstance(hits, list) and hits and isinstance(hits[0], dict) and isinstance(hits[0].get("recipe"), dict):
        return hits[0]["recipe"]
    raise EdamamUnavailable("Edamam recipe detail did not contain a recipe object.")


def _ingredient_amount(ingredient: dict, scale: float) -> float:
    weight = _positive_float(ingredient.get("weight"))
    if weight is None:
        raise EdamamUnavailable("Edamam ingredient is missing gram weight; conversion is unresolved.")
    return weight * scale


def _ingredient_id(ingredient: dict, index: int) -> str:
    food_id = ingredient.get("foodId")
    basis = food_id if isinstance(food_id, str) and food_id else _ingredient_name(ingredient)
    return f"edamam-{_slug(basis) or index}-{_short_hash(basis)}"


def _ingredient_name(ingredient: dict) -> str:
    food = ingredient.get("food")
    if isinstance(food, dict):
        label = food.get("label")
        if isinstance(label, str) and label:
            return label
    for key in ("food", "text"):
        value = ingredient.get(key)
        if isinstance(value, str) and value:
            return value
    return "Ingredient"


def _search_terms(ingredient: dict) -> list[str]:
    terms = []
    for value in (_ingredient_name(ingredient), ingredient.get("foodCategory")):
        if isinstance(value, str) and value and value not in terms:
            terms.append(value)
    return terms


def _positive_float(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _with_credentials(href: str, settings: EdamamSettings) -> str:
    parsed = parse.urlparse(href)
    query = dict(parse.parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("app_id", settings.app_id)
    query.setdefault("app_key", settings.app_key)
    return parse.urlunparse(parsed._replace(query=parse.urlencode(query)))


def _slug(value: str) -> str:
    cleaned = []
    for character in value.casefold():
        if character.isalnum():
            cleaned.append(character)
        elif cleaned and cleaned[-1] != "-":
            cleaned.append("-")
    return "".join(cleaned).strip("-")[:32]


def _short_hash(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()[:10]
