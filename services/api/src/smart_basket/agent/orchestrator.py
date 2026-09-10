from datetime import (
    datetime,
    timezone,
)

from smart_basket.catalog.matching import (
    MatchingContext,
    find_product_candidates,
)

from smart_basket.optimization.optimizer import (
    optimize_basket,
)

from smart_basket.optimization.recurrence import (
    analyze_recurring,
)

from smart_basket.meals import (
    build_meal_plan,
)

from smart_basket.schemas import (
    PlanningResult,
)


class UlianaPlanner:
    """
    Smart Basket orchestration.

    Responsibilities:
    - control execution order;
    - load context and history;
    - call meal planning;
    - call product matching;
    - call recurring purchase analysis;
    - call budget optimization;
    - assemble PlanningResult.

    HTTP, runId, run status and storage
    are handled by Rina's FastAPI layer.
    """

    def __init__(self, catalog):
        self.catalog = catalog


    def run_planner(
        self,
        request,
        session,
        emit_progress,
    ):

        warnings = []

        # ====================================================
        # STAGE 1 — CONTEXT
        # Current source: Rina DemoCatalog
        # Later source: Arina
        # ====================================================

        context = self.catalog.get_user_context(
            session
        )

        warnings.extend(
            context.warnings
        )

        emit_progress(
            "context",
            "User context loaded.",
        )


        # ====================================================
        # STAGE 2 — HISTORY + RECURRING
        # History source: DemoCatalog for now
        # Recurrence logic: real Vika module
        # ====================================================

        purchases = []
        recurring_items = []

        if request.include_recurring:

            purchases = (
                self.catalog
                .get_purchase_history(
                    session
                )
            )

            emit_progress(
                "history",
                "Purchase history loaded.",
            )

            recurring_items = (
                analyze_recurring(
                    purchases=purchases,
                    pets=request.pets,
                    as_of=datetime.now(
                        timezone.utc
                    ).date(),
                )
            )

            emit_progress(
                "history",
                (
                    "Recurring purchases analyzed: "
                    f"{len(recurring_items)} suggestions."
                ),
            )

        else:

            emit_progress(
                "history",
                "Recurring purchases disabled.",
            )


        # ====================================================
        # STAGE 3 — MEALS
        # Sofiia owns Edamam/fallback meal planning.
        # ====================================================

        meal_result = build_meal_plan(
            request=request,
            effective_context=context,
        )

        meals = meal_result[
            "meals"
        ]

        ingredients = meal_result[
            "ingredients"
        ]

        warnings.extend(
            meal_result.get(
                "warnings",
                [],
            )
        )

        emit_progress(
            "meals",
            (
                f"Meal plan generated: "
                f"{len(meals)} meals."
            ),
        )


        # ====================================================
        # STAGE 4 — PRODUCT MATCHING
        # Real Rina matching
        # ====================================================

        selected_recurring = [
            item
            for item in recurring_items
            if item.selected
        ]

        matching_context = MatchingContext(
            session=session,
            catalog=self.catalog,
            check_restrictions=(
                self.catalog
                .check_restrictions
            ),
        )

        matching_result = (
            find_product_candidates(
                ingredients,
                selected_recurring,
                matching_context,
            )
        )

        emit_progress(
            "matching",
            (
                "Product matching completed: "
                f"{len(matching_result.candidates)} "
                "candidates."
            ),
        )


        # ====================================================
        # STAGE 5 — BUDGET OPTIMIZATION
        # Real Vika optimizer
        # ====================================================

        optimization = (
            optimize_basket(
                request=request,
                ingredients=ingredients,
                candidates=matching_result,
                selected_recurring=(
                    selected_recurring
                ),
            )
        )

        emit_progress(
            "optimization",
            (
                "Basket optimization completed. "
                f"Status: "
                f"{optimization.budget_status}."
            ),
        )


        # ====================================================
        # STAGE 6 — CAN CART BE CONFIRMED?
        # ====================================================

        can_confirm_cart = (
            optimization.budget_status
            == "within_budget"

            and len(
                optimization
                .unresolved_requirements
            )
            == 0

            and context
            .cart_context_ready
        )


        # ====================================================
        # STAGE 7 — FINAL RESULT
        # ====================================================

        result = PlanningResult(
            run_id="pending",

            version=1,

            data_mode="demo",

            effective_request=request,

            meal_plan=meals,

            ingredients=ingredients,

            recurring_items=(
                recurring_items
            ),

            selected_products=(
                optimization
                .selected_products
            ),

            substitutions=(
                optimization
                .substitutions
            ),

            budget_minor=(
                request.budget_minor
            ),

            basket_total_minor=(
                optimization
                .basket_total_minor
            ),

            budget_remaining_minor=(
                optimization
                .budget_remaining_minor
            ),

            savings_minor=(
                optimization
                .savings_minor
            ),

            budget_status=(
                optimization
                .budget_status
            ),

            unresolved_requirements=(
                optimization
                .unresolved_requirements
            ),

            warnings=warnings,

            can_confirm_cart=(
                can_confirm_cart
            ),
        )

        return result


    def recalculate_plan(
        self,
        previous_result,
        selected_recurring_ids,
        session,
        emit_progress,
    ):
        """
        Temporary recalculation implementation.

        Full recurring-item recalculation will be added
        when recurring candidates can be matched by
        Rina's catalog layer.
        """

        emit_progress(
            "context",
            "Starting plan recalculation.",
        )

        return self.run_planner(
            request=(
                previous_result
                .effective_request
            ),
            session=session,
            emit_progress=emit_progress,
        )
