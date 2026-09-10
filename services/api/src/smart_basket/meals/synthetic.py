"""Original synthetic meals for local development and demo fallback."""

from __future__ import annotations

from .normalization import IngredientSpec, MealTemplate, aggregate_ingredients, build_meal_from_template
from .nutrition import ACCURACY_WARNINGS, calorie_target_for_slot, calorie_target_warnings, build_nutrition_summary
from smart_basket.schemas import MealMacros


def _macros(protein: float, fat: float, carbs: float) -> MealMacros:
    return MealMacros(protein_g=protein, fat_g=fat, carbs_g=carbs)

INGREDIENTS: dict[str, IngredientSpec] = {
    "oats": IngredientSpec(
        id="oats",
        name="Dry oats",
        search_terms=("oats",),
        quantity_per_serving=50.0,
        unit="g",
    ),
    "rice": IngredientSpec(
        id="rice",
        name="Dry rice",
        search_terms=("rice",),
        quantity_per_serving=80.0,
        unit="g",
    ),
    "lentils": IngredientSpec(
        id="lentils",
        name="Dry lentils",
        search_terms=("lentils",),
        quantity_per_serving=70.0,
        unit="g",
    ),
}


DAY_TEMPLATES: tuple[tuple[MealTemplate, MealTemplate, MealTemplate], ...] = (
    (
        MealTemplate(
            slot="breakfast",
            title="Oatmeal breakfast bowl",
            kcal_per_serving=420.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.5, 7.0, 69.0),
            cooking_time_minutes=12,
        ),
        MealTemplate(
            slot="lunch",
            title="Rice and lentil lunch bowl",
            kcal_per_serving=680.0,
            ingredients=(
                INGREDIENTS["rice"],
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=30.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(23.0, 3.5, 126.0),
            cooking_time_minutes=30,
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil dinner stew",
            kcal_per_serving=760.0,
            ingredients=(
                INGREDIENTS["lentils"],
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=40.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(30.0, 4.0, 130.0),
            cooking_time_minutes=35,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Warm oat porridge with fruit",
            kcal_per_serving=430.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.0, 7.5, 71.0),
            cooking_time_minutes=14,
        ),
        MealTemplate(
            slot="lunch",
            title="Rice pilaf with lentils",
            kcal_per_serving=670.0,
            ingredients=(
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=70.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=40.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(24.0, 4.0, 123.0),
            cooking_time_minutes=32,
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil and rice soup",
            kcal_per_serving=730.0,
            ingredients=(
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=60.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=50.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(28.0, 4.5, 124.0),
            cooking_time_minutes=34,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Oat breakfast cup",
            kcal_per_serving=410.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(12.5, 6.5, 67.0),
            cooking_time_minutes=10,
        ),
        MealTemplate(
            slot="lunch",
            title="Rice bowl with lentil topping",
            kcal_per_serving=690.0,
            ingredients=(
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=90.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=20.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(22.0, 3.0, 129.0),
            cooking_time_minutes=28,
        ),
        MealTemplate(
            slot="dinner",
            title="Hearty lentil skillet",
            kcal_per_serving=780.0,
            ingredients=(
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=80.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=30.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(32.0, 4.0, 131.0),
            cooking_time_minutes=36,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Simple overnight oats",
            kcal_per_serving=420.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.5, 7.0, 69.0),
            cooking_time_minutes=8,
        ),
        MealTemplate(
            slot="lunch",
            title="Balanced rice and lentils",
            kcal_per_serving=700.0,
            ingredients=(
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=60.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=50.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(25.0, 4.0, 125.0),
            cooking_time_minutes=30,
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil rice supper bowl",
            kcal_per_serving=740.0,
            ingredients=(
                IngredientSpec(
                    id="lentils",
                    name="Dry lentils",
                    search_terms=("lentils",),
                    quantity_per_serving=50.0,
                    unit="g",
                ),
                IngredientSpec(
                    id="rice",
                    name="Dry rice",
                    search_terms=("rice",),
                    quantity_per_serving=60.0,
                    unit="g",
                ),
            ),
            macros_per_serving=_macros(27.0, 4.0, 126.0),
            cooking_time_minutes=33,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Cinnamon oat bowl",
            kcal_per_serving=425.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.2, 7.2, 70.0),
            cooking_time_minutes=12,
        ),
        MealTemplate(
            slot="lunch",
            title="Lentil rice power bowl",
            kcal_per_serving=685.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 75.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 35.0, "g"),
            ),
            macros_per_serving=_macros(24.5, 3.5, 126.0),
            cooking_time_minutes=31,
        ),
        MealTemplate(
            slot="dinner",
            title="Savory lentil dinner bowl",
            kcal_per_serving=750.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 65.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 45.0, "g"),
            ),
            macros_per_serving=_macros(29.5, 4.0, 127.0),
            cooking_time_minutes=35,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Quick oat breakfast",
            kcal_per_serving=415.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.0, 6.8, 68.0),
            cooking_time_minutes=9,
        ),
        MealTemplate(
            slot="lunch",
            title="Rice lunch plate with lentils",
            kcal_per_serving=695.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 85.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 25.0, "g"),
            ),
            macros_per_serving=_macros(22.8, 3.3, 130.0),
            cooking_time_minutes=29,
        ),
        MealTemplate(
            slot="dinner",
            title="Comfort lentil rice pot",
            kcal_per_serving=745.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 55.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 55.0, "g"),
            ),
            macros_per_serving=_macros(28.0, 4.0, 126.0),
            cooking_time_minutes=34,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Soft oat morning bowl",
            kcal_per_serving=420.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.4, 7.0, 69.5),
            cooking_time_minutes=11,
        ),
        MealTemplate(
            slot="lunch",
            title="Lentil pilaf lunch",
            kcal_per_serving=675.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 65.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 45.0, "g"),
            ),
            macros_per_serving=_macros(25.5, 3.8, 122.0),
            cooking_time_minutes=32,
        ),
        MealTemplate(
            slot="dinner",
            title="Rice and lentil evening stew",
            kcal_per_serving=755.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 70.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 40.0, "g"),
            ),
            macros_per_serving=_macros(30.5, 4.2, 128.0),
            cooking_time_minutes=36,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Classic oat breakfast",
            kcal_per_serving=430.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.6, 7.4, 71.0),
            cooking_time_minutes=13,
        ),
        MealTemplate(
            slot="lunch",
            title="Balanced lentil rice lunch",
            kcal_per_serving=700.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 80.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 30.0, "g"),
            ),
            macros_per_serving=_macros(23.4, 3.6, 128.0),
            cooking_time_minutes=30,
        ),
        MealTemplate(
            slot="dinner",
            title="Hearty lentil supper",
            kcal_per_serving=735.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 60.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 50.0, "g"),
            ),
            macros_per_serving=_macros(28.8, 4.1, 125.0),
            cooking_time_minutes=34,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Oat bowl with warm spices",
            kcal_per_serving=418.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.1, 6.9, 68.5),
            cooking_time_minutes=12,
        ),
        MealTemplate(
            slot="lunch",
            title="Rice and lentil meal prep bowl",
            kcal_per_serving=690.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 90.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 20.0, "g"),
            ),
            macros_per_serving=_macros(22.0, 3.1, 130.0),
            cooking_time_minutes=28,
        ),
        MealTemplate(
            slot="dinner",
            title="Thick lentil dinner soup",
            kcal_per_serving=765.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 75.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 35.0, "g"),
            ),
            macros_per_serving=_macros(31.2, 4.2, 129.0),
            cooking_time_minutes=36,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Creamy oat breakfast bowl",
            kcal_per_serving=422.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.3, 7.1, 69.0),
            cooking_time_minutes=12,
        ),
        MealTemplate(
            slot="lunch",
            title="Simple rice and lentil bowl",
            kcal_per_serving=680.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 70.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 40.0, "g"),
            ),
            macros_per_serving=_macros(24.0, 3.7, 124.0),
            cooking_time_minutes=31,
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil skillet with rice",
            kcal_per_serving=750.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 50.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 60.0, "g"),
            ),
            macros_per_serving=_macros(27.3, 4.0, 127.0),
            cooking_time_minutes=33,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Prepared oat breakfast jar",
            kcal_per_serving=410.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(12.8, 6.7, 67.0),
            cooking_time_minutes=8,
        ),
        MealTemplate(
            slot="lunch",
            title="Lentil rice lunch stew",
            kcal_per_serving=705.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 60.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 50.0, "g"),
            ),
            macros_per_serving=_macros(26.0, 3.9, 125.0),
            cooking_time_minutes=33,
        ),
        MealTemplate(
            slot="dinner",
            title="Rice lentil dinner plate",
            kcal_per_serving=740.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 80.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 30.0, "g"),
            ),
            macros_per_serving=_macros(32.0, 4.2, 124.0),
            cooking_time_minutes=36,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Gentle oat porridge",
            kcal_per_serving=428.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.5, 7.2, 70.5),
            cooking_time_minutes=13,
        ),
        MealTemplate(
            slot="lunch",
            title="Warm rice lentil lunch",
            kcal_per_serving=685.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 75.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 35.0, "g"),
            ),
            macros_per_serving=_macros(24.2, 3.6, 126.0),
            cooking_time_minutes=31,
        ),
        MealTemplate(
            slot="dinner",
            title="Lentil pot with rice",
            kcal_per_serving=758.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 65.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 45.0, "g"),
            ),
            macros_per_serving=_macros(29.7, 4.1, 128.0),
            cooking_time_minutes=35,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Everyday oat bowl",
            kcal_per_serving=416.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.0, 6.8, 68.0),
            cooking_time_minutes=11,
        ),
        MealTemplate(
            slot="lunch",
            title="Rice bowl with soft lentils",
            kcal_per_serving=692.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 85.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 25.0, "g"),
            ),
            macros_per_serving=_macros(22.7, 3.4, 129.0),
            cooking_time_minutes=29,
        ),
        MealTemplate(
            slot="dinner",
            title="Filling lentil rice dinner",
            kcal_per_serving=748.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 55.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 55.0, "g"),
            ),
            macros_per_serving=_macros(28.2, 4.0, 126.5),
            cooking_time_minutes=34,
        ),
    ),
    (
        MealTemplate(
            slot="breakfast",
            title="Steady oat breakfast bowl",
            kcal_per_serving=424.0,
            ingredients=(INGREDIENTS["oats"],),
            macros_per_serving=_macros(13.4, 7.1, 69.8),
            cooking_time_minutes=12,
        ),
        MealTemplate(
            slot="lunch",
            title="Lentil rice midday bowl",
            kcal_per_serving=678.0,
            ingredients=(
                IngredientSpec("rice", "Dry rice", ("rice",), 65.0, "g"),
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 45.0, "g"),
            ),
            macros_per_serving=_macros(25.4, 3.8, 123.0),
            cooking_time_minutes=32,
        ),
        MealTemplate(
            slot="dinner",
            title="Slow simmer lentil dinner",
            kcal_per_serving=752.0,
            ingredients=(
                IngredientSpec("lentils", "Dry lentils", ("lentils",), 70.0, "g"),
                IngredientSpec("rice", "Dry rice", ("rice",), 40.0, "g"),
            ),
            macros_per_serving=_macros(30.4, 4.1, 127.5),
            cooking_time_minutes=36,
        ),
    ),
)


def build_synthetic_meal_plan(request, filters):
    meals = []
    for day in range(1, request.days + 1):
        templates = DAY_TEMPLATES[(day - 1) % len(DAY_TEMPLATES)]
        for index, template in enumerate(templates, start=1):
            meals.append(
                build_meal_from_template(
                    day=day,
                    index=index,
                    servings=request.people,
                    template=template,
                    restrictions=filters.restrictions,
                    source="synthetic",
                    calorie_target=calorie_target_for_slot(
                        request.calories_per_person_per_day,
                        template.slot,
                    ),
                )
            )

    ingredients = aggregate_ingredients(meals, INGREDIENTS, filters.restrictions)
    nutrition_summary = build_nutrition_summary(request, meals)
    warnings = [
        "Meal plan uses Sofiia synthetic fallback; live Edamam credentials are not configured.",
        "Synthetic recipes are original demo data and are not provider recipe payloads.",
        *ACCURACY_WARNINGS,
        *calorie_target_warnings(nutrition_summary),
    ]
    if request.calories_per_person_per_day is not None:
        warnings.append(
            "Calorie target metadata uses a 25/35/40 breakfast/lunch/dinner split; synthetic fallback does not run ILP optimization."
        )

    return {
        "meals": meals,
        "nutrition_summary": nutrition_summary,
        "ingredients": ingredients,
        "warnings": warnings,
        "source": "synthetic",
    }
