"""Temporary substitutes for Arina, Sofiia, Vika and Uliana. No network access."""

from collections import defaultdict
from typing import Callable, Protocol

from smart_basket.catalog.matching import MatchingContext, find_product_candidates, line_total, purchase_quantity
from smart_basket.core import DEMO_WARNING, now
from smart_basket.meals.nutrition import build_nutrition_summary
from smart_basket.schemas import (
    IngredientAmount, IngredientRequirement, Meal, PlanningRequest, PlanningResult,
    ProductCandidate, ProductSelection, UserContext,
)


class Planner(Protocol):
    def run_planner(self, request: PlanningRequest, session: object,
                    emit_progress: Callable[[str, str], None]) -> PlanningResult: ...
    def recalculate_plan(self, previous_result: PlanningResult, selected_recurring_ids: list[str],
                         session: object, emit_progress: Callable[[str, str], None]) -> PlanningResult: ...


# Edamam tags each ingredient with a `foodCategory` (see meals/edamam.py:_search_terms), a
# bounded taxonomy of ~25 values, unlike the ingredient names themselves which are effectively
# unlimited. Measured live across 145 real ingredients (4 recipe-sourced plans, run 20): 140
# carried a category, spread over exactly these values (case varies in Edamam's own data, e.g.
# both "Condiments and sauces" and "condiments and sauces" were observed — search_products()
# already casefolds, so that is handled for free). Matching a generic bucket by category, instead
# of trying to name every ingredient a recipe could ever contain, is what makes coverage of
# arbitrary live recipes tractable at all.
CATEGORY_PRODUCTS = [
    # (bucket key, display name, package grams, price in kopiykas, category aliases)
    ("vegetables", "Demo mixed vegetables", 500, 4500, ["vegetables", "canned vegetables"]),
    ("condiments", "Demo condiments and sauces", 200, 3500, ["condiments and sauces"]),
    ("grains", "Demo grains", 500, 5500, ["grains", "cooked grains"]),
    ("bread", "Demo bread and pastries", 400, 4000,
     ["bread, rolls and tortillas", "quick breads and pastries"]),
    ("fruit", "Demo fruit", 500, 5000, ["fruit", "canned fruit"]),
    ("sugars", "Demo sugar", 500, 3000, ["sugars", "sugar syrups"]),
    ("dairy", "Demo dairy", 500, 5500, ["dairy"]),
    ("milk", "Demo milk", 500, 3200, ["milk"]),
    ("cheese", "Demo cheese", 250, 6500, ["cheese"]),
    ("oils", "Demo cooking oil", 250, 4500, ["oils"]),
    ("eggs", "Demo eggs", 300, 4000, ["eggs"]),
    ("poultry", "Demo poultry", 500, 9000, ["poultry"]),
    ("meats", "Demo meat", 500, 11000, ["meats", "cured meats"]),
    ("seafood", "Demo seafood", 400, 12000, ["seafood"]),
    ("plant-protein", "Demo plant-based protein", 300, 6000, ["plant-based protein", "vegan products"]),
    ("soup", "Demo canned soup", 400, 3800, ["canned soup"]),
    ("beverages", "Demo beverages", 500, 3000, ["non-dairy beverages", "100% juice", "wines"]),
    ("chocolate", "Demo chocolate", 200, 5200, ["chocolate"]),
    ("water", "Demo water", 1000, 1500, ["water"]),
]


class DemoCatalog:
    """Normalized invented catalog. Known composition labels are fixture evidence only."""
    SUPPORTED_RESTRICTIONS = {
        "peanut-free", "gluten-free", "dairy-free", "tree-nut-free",
        "shellfish-free", "soy-free", "egg-free", "pork-free", "fish-free",
        "red-meat-free",
    }

    def __init__(self):
        self.products = {}
        self.terms = {}
        # Explicit labels on synthetic fixtures, never guesses from product names. The oats
        # fixture represents a certified gluten-free product so every demo restriction has a
        # verifiable candidate while the UI continues to label the result as synthetic.
        self.restriction_labels = {}
        for key, name, size, price in [
            ("oats", "Demo dry oats, 500 g", 500, 6000),
            ("rice", "Demo dry rice, 1000 g", 1000, 8000),
            ("lentils", "Demo dry lentils, 500 g", 500, 7000),
        ]:
            product = ProductCandidate(id=f"demo-{key}", name=name, requirement_ids=[],
                price_minor=price, selling_unit="package", quantity_step=1.0,
                content_quantity=float(size), content_unit="g", available=True,
                restriction_check="pass", regular_price_minor=None, source="synthetic", checked_at=now())
            self.products[product.id] = product
            self.terms[key] = [product.id]
            self.restriction_labels[product.id] = set(self.SUPPORTED_RESTRICTIONS)
        for suffix, changes in [
            ("unavailable", {"available": False}),
            ("unknown", {"restriction_check": "unknown"}),
            ("no-size", {"content_quantity": None, "content_unit": None}),
        ]:
            product = self.products["demo-oats"].model_copy(update={"id": f"demo-oats-{suffix}", **changes})
            self.products[product.id] = product
            self.terms["oats"].append(product.id)
            self.restriction_labels[product.id] = set(self.SUPPORTED_RESTRICTIONS)
        # Category buckets for live Edamam recipes: no composition evidence exists for a generic
        # placeholder, so — unlike oats/rice/lentils above — these are deliberately left out of
        # restriction_labels. check_restrictions() below then answers "unknown" for any requested
        # restriction, the same fail-closed behaviour as every other unverified candidate (see
        # BUG-021); only an unrestricted requirement can select one.
        for key, name, size, price, aliases in CATEGORY_PRODUCTS:
            product = ProductCandidate(id=f"demo-cat-{key}", name=f"{name}, {size} g", requirement_ids=[],
                price_minor=price, selling_unit="package", quantity_step=1.0,
                content_quantity=float(size), content_unit="g", available=True,
                restriction_check="pass", regular_price_minor=None, source="synthetic", checked_at=now())
            self.products[product.id] = product
            for alias in aliases:
                self.terms.setdefault(alias.casefold(), []).append(product.id)

    def search_products(self, session, query):
        return [self.products[id].model_copy(deep=True) for id in self.terms.get(query.casefold(), [])]

    def get_product_details(self, session, id):
        return self.products[id].model_copy(deep=True)

    def get_user_context(self, session):
        return UserContext(preferences=[], restrictions=[], pets=[], history_available=False,
            cart_context_ready=True, warnings=[DEMO_WARNING, "Purchase history is empty; coverage unavailable."])

    def get_purchase_history(self, session):
        return []

    def check_restrictions(self, product, restrictions):
        if product.restriction_check != "pass":
            return product.restriction_check
        if not set(restrictions).issubset(self.restriction_labels.get(product.id, set())):
            return "unknown"
        return "pass"


class DemoPlanner:
    def __init__(self, catalog):
        self.catalog = catalog

    def run_planner(self, request, session, emit_progress):
        context = self.catalog.get_user_context(session)
        emit_progress("context", "Loaded the synthetic profile.")
        self.catalog.get_purchase_history(session)
        emit_progress("history", "Demo history is empty; no recurring purchases inferred.")
        meals = []
        quantities = defaultdict(float)
        meal_ids = defaultdict(list)
        names = {"oats": "Dry oats", "rice": "Dry rice", "lentils": "Dry lentils"}
        for day in range(1, request.days + 1):
            for slot, key in [("breakfast", "oats"), ("lunch", "rice"), ("dinner", "lentils")]:
                meal_id = f"demo-day-{day}-{slot}"
                quantity = 50.0 * request.people
                quantities[key] += quantity
                meal_ids[key].append(meal_id)
                meals.append(Meal(id=meal_id, day=day, slot=slot, title=f"Demo {key} bowl",
                    servings=request.people, kcal_per_serving=None, macros_per_serving=None,
                    calorie_target=None, cooking_time_minutes=None, ingredient_ids=[key],
                    ingredient_amounts=[IngredientAmount(ingredient_id=key, name=names[key],
                        quantity=quantity, unit="g")], source="synthetic", source_url=None, attribution=None))
        ingredients = [IngredientRequirement(id=key, name=names[key], search_terms=[key],
            quantity=quantity, unit="g", meal_ids=meal_ids[key], restrictions=request.restrictions)
            for key, quantity in quantities.items()]
        nutrition_summary = build_nutrition_summary(request, meals)
        emit_progress("meals", "Created synthetic meal cards and scaled ingredient quantities.")
        matches = find_product_candidates(ingredients, [], MatchingContext(
            session, self.catalog, self.catalog.check_restrictions))
        emit_progress("matching", "Checked demo products, package sizes and composition flags.")
        # Temporary first-compatible selection, not Vika's budget optimizer.
        demand = defaultdict(float)
        product_requirements = defaultdict(list)
        chosen = {}
        for ingredient in ingredients:
            candidate = next((c for c in matches.candidates if ingredient.id in c.requirement_ids
                and c.available and c.restriction_check == "pass" and c.content_quantity is not None
                and c.content_unit == ingredient.unit), None)
            if candidate is not None:
                demand[candidate.id] += ingredient.quantity
                product_requirements[candidate.id].append(ingredient.id)
                chosen[candidate.id] = candidate
        selections = []
        for id, candidate in chosen.items():
            quantity = purchase_quantity(demand[id], candidate.content_unit, candidate)
            selections.append(ProductSelection(product_id=id, name=candidate.name,
                requirement_ids=product_requirements[id], recurring_suggestion_ids=[], quantity=quantity,
                selling_unit=candidate.selling_unit, unit_price_minor=candidate.price_minor,
                line_total_minor=line_total(quantity, candidate.price_minor), source=candidate.source,
                reason="Demo first compatible product; demand combined before package rounding.",
                restriction_check=candidate.restriction_check))
        total = sum(p.line_total_minor for p in selections)
        status = "incomplete" if matches.unresolved_requirements else (
            "within_budget" if total <= request.budget_minor else "over_budget")
        warnings = context.warnings + [
            "Synthetic menu for UI development; not a nutritionally complete meal plan.",
            "Calorie targeting, pet needs and free-text notes are not implemented by the mock planner.",
            "Recurring suggestions and budget optimization await Vika's module.",
        ]
        emit_progress("optimization", "Calculated demo package totals; no optimization performed.")
        return PlanningResult(run_id="pending", version=1, data_mode="demo", effective_request=request,
            meal_plan=meals, nutrition_summary=nutrition_summary, ingredients=ingredients,
            recurring_items=[], selected_products=selections, substitutions=[],
            budget_minor=request.budget_minor, basket_total_minor=total,
            budget_remaining_minor=request.budget_minor-total, savings_minor=None,
            budget_status=status, unresolved_requirements=matches.unresolved_requirements,
            warnings=warnings, can_confirm_cart=status == "within_budget")

    def recalculate_plan(self, previous_result, selected_recurring_ids, session, emit_progress):
        if selected_recurring_ids:
            raise ValueError("Demo history has no recurring suggestions.")
        return self.run_planner(previous_result.effective_request, session, emit_progress)
