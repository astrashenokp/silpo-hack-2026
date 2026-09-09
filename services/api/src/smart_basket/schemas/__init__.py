"""Executable contract v0.2; public serialization always uses camelCase."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

PositiveInt = Annotated[int, Field(strict=True, gt=0)]
Money = Annotated[int, Field(strict=True, ge=0)]
PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Unit = Literal["g", "ml", "piece"]
Source = Literal["silpo", "synthetic"]
Stage = Literal["context", "history", "meals", "matching", "optimization", "ready"]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True,
                              serialize_by_alias=True, extra="forbid", strict=True)


class Pet(Model):
    species: Literal["cat", "dog"]
    count: PositiveInt


class PlanningRequest(Model):
    budget_minor: PositiveInt
    currency: Literal["UAH"]
    days: Annotated[int, Field(ge=1, le=7)]
    people: Annotated[int, Field(ge=1, le=6)]
    calories_per_person_per_day: PositiveInt | None
    preferences: list[str]
    restrictions: list[str]
    pets: list[Pet]
    include_recurring: bool
    notes: Annotated[str, Field(max_length=2000)]

    @field_validator("preferences", "restrictions")
    @classmethod
    def supported_labels(cls, value, info):
        allowed = {"preferences": {"vegetarian"}, "restrictions": {"peanut-free"}}
        unknown = set(value) - allowed[info.field_name]
        if unknown:
            raise ValueError(f"Unsupported {info.field_name}: {', '.join(sorted(unknown))}")
        return list(dict.fromkeys(value))


class Error(Model):
    code: str
    message: str
    retryable: bool


class ErrorEnvelope(Model):
    error: Error


class Health(Model):
    status: Literal["ok"] = "ok"
    mode: Literal["demo"] = "demo"


class UserContext(Model):
    preferences: list[str]
    restrictions: list[str]
    pets: list[Pet]
    history_available: bool
    cart_context_ready: bool
    warnings: list[str]


class Purchase(Model):
    receipt_id: str
    purchased_at: str
    channel: Literal["online", "offline"]
    product_id: str
    name: str
    category: str
    quantity: PositiveNumber
    unit: str
    unit_price_minor: Money | None = None


class IngredientRequirement(Model):
    id: str
    name: str
    search_terms: list[str]
    quantity: PositiveNumber
    unit: Unit
    meal_ids: list[str]
    restrictions: list[str]


class IngredientAmount(Model):
    ingredient_id: str
    name: str
    quantity: PositiveNumber
    unit: Unit


class Meal(Model):
    id: str
    day: PositiveInt
    slot: Literal["breakfast", "lunch", "dinner"]
    title: str
    servings: PositiveInt
    kcal_per_serving: PositiveNumber | None
    ingredient_ids: list[str]
    ingredient_amounts: list[IngredientAmount]
    source: Literal["edamam", "synthetic"]
    source_url: str | None
    attribution: str | None


class ProductCandidate(Model):
    id: str
    name: str
    requirement_ids: list[str]
    price_minor: Money
    selling_unit: str
    quantity_step: PositiveNumber
    content_quantity: PositiveNumber | None
    content_unit: Unit | None
    available: bool
    restriction_check: Literal["pass", "fail", "unknown"]
    regular_price_minor: Money | None
    source: Source
    checked_at: str


class UnresolvedRequirement(Model):
    requirement_id: str
    reason: str


class CandidateResult(Model):
    candidates: list[ProductCandidate]
    unresolved_requirements: list[UnresolvedRequirement]


class RecurringSuggestion(Model):
    id: str
    product_name: str
    product_id: str | None
    category: str
    species: Literal["cat", "dog"] | None
    suggested_quantity: PositiveNumber
    unit: str
    average_interval_days: PositiveNumber
    days_since_last_purchase: Annotated[int, Field(ge=0)]
    confidence: Annotated[float, Field(ge=0, le=1)]
    reason: str
    selected: bool


class ProductSelection(Model):
    product_id: str
    name: str
    requirement_ids: list[str]
    recurring_suggestion_ids: list[str]
    quantity: PositiveNumber
    selling_unit: str
    unit_price_minor: Money
    line_total_minor: Money
    source: Source
    reason: str
    restriction_check: Literal["pass", "fail", "unknown"]


class Substitution(Model):
    requirement_ids: list[str]
    from_product_id: str
    to_product_id: str
    reason: str
    delta_minor: int


class PlanningResult(Model):
    run_id: str
    version: PositiveInt
    data_mode: Literal["live", "demo", "mixed"]
    effective_request: PlanningRequest
    meal_plan: list[Meal]
    ingredients: list[IngredientRequirement]
    recurring_items: list[RecurringSuggestion]
    selected_products: list[ProductSelection]
    substitutions: list[Substitution]
    budget_minor: Money
    basket_total_minor: Money
    budget_remaining_minor: int
    savings_minor: int | None
    budget_status: Literal["within_budget", "over_budget", "incomplete"]
    unresolved_requirements: list[UnresolvedRequirement]
    warnings: list[str]
    can_confirm_cart: bool


class ProgressEvent(Model):
    stage: Stage
    message: str
    at: str


class RunSnapshot(Model):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: Stage
    events: list[ProgressEvent]
    result: PlanningResult | None
    error: Error | None


class PlanReference(Model):
    run_id: str
    version: PositiveInt


class RecalculateRequest(Model):
    version: PositiveInt
    selected_recurring_ids: list[str]


class Confirmation(Model):
    preview_id: str
    idempotency_key: Annotated[str, Field(min_length=1, max_length=128)]


class CartChange(Model):
    product_id: str
    name: str
    before_quantity: Annotated[float, Field(ge=0)]
    after_quantity: PositiveNumber
    unit_price_minor: Money


class CartPreview(Model):
    preview_id: str
    run_id: str
    version: PositiveInt
    expires_at: str
    existing_cart_total_minor: Money
    added_goods_total_minor: Money
    projected_goods_total_minor: Money
    changes: list[CartChange]
    warnings: list[str]


class CartItemOutcome(Model):
    product_id: str
    status: Literal["success", "failed"]
    requested_quantity: PositiveNumber
    actual_quantity: Annotated[float, Field(ge=0)]
    message: str


class CartReceipt(Model):
    preview_id: str
    status: Literal["success", "partial", "failed"]
    items: list[CartItemOutcome]
    verified_cart_total_minor: Money | None
    warnings: list[str]


class FatSecretStatus(Model):
    connected: bool
    account_label: str | None
    export_available: bool
    reason: str | None


class FatSecretPreviewRequest(PlanReference):
    meal_ids: Annotated[list[str], Field(min_length=1)]


class FatSecretItem(Model):
    ingredient_id: str
    food_id: str
    serving_id: str
    matched_name: str
    number_of_units: PositiveNumber
    source_quantity: PositiveNumber
    source_unit: Unit


class UnresolvedFood(Model):
    ingredient_id: str
    reason: str


class FatSecretPreviewMeal(Model):
    meal_id: str
    title: str
    source_kcal_per_serving: PositiveNumber | None
    fatsecret_kcal_per_serving: PositiveNumber | None
    items: list[FatSecretItem]
    unresolved: list[UnresolvedFood]


class FatSecretPreview(Model):
    preview_id: str
    run_id: str
    version: PositiveInt
    account_label: str
    expires_at: str
    destination: Literal["saved_meals"] = "saved_meals"
    portion_basis: Literal["one_person"] = "one_person"
    can_confirm: bool
    meals: list[FatSecretPreviewMeal]
    warnings: list[str]


class ExportMealOutcome(Model):
    meal_id: str
    status: Literal["pending", "saved", "already_saved", "partial", "failed"]
    saved_meal_id: str | None
    message: str


class FatSecretExport(Model):
    export_id: str
    status: Literal["queued", "running", "success", "partial", "failed"]
    meals: list[ExportMealOutcome]
    error: Error | None
    warnings: list[str]


class ExportAccepted(Model):
    export_id: str
