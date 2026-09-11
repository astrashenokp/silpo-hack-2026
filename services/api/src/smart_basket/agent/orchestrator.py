from datetime import (
    datetime,
    timezone,
)

from smart_basket.core import (
    ApiError,
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

from smart_basket.meals.edamam import (
    EdamamUnavailable,
)

from smart_basket.meals.filters import (
    UnsupportedMealFilter,
)

from smart_basket.schemas import (
    PlanningResult,
)

from .llm import GeminiChatInterpreter

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

    def __init__(
        self,
        catalog,
        chat_interpreter=None,
        meal_replanner=None,
    ):
        self.catalog = catalog
        self.chat_interpreter = chat_interpreter
        self.meal_replanner = meal_replanner


    def _get_chat_interpreter(self):
        if self.chat_interpreter is None:
            self.chat_interpreter = (
                GeminiChatInterpreter()
            )

        return self.chat_interpreter

    def _request_meal_replan(
        self,
        request,
        context,
        previous_meals,
        reason,
        preserve_meal_slots=None,
        replace_ingredient=None,
        emit_progress=None,
    ):
        """
        Request exactly one revised meal plan.

        Uliana controls WHEN replanning happens.
        Sofiia controls HOW meals are changed.
        """

        # Sofiia replan boundary is not connected yet.
        if self.meal_replanner is None:
            return None

        preserve_meal_slots = (
            preserve_meal_slots or []
        )

        if emit_progress is not None:
            emit_progress(
                "meals",
                (
                    "Meal replan requested. "
                    f"Reason: {reason}."
                ),
            )

        try:
            meal_result = self.meal_replanner(
                request=request,
                effective_context=context,
                previous_meals=previous_meals,
                reason=reason,
                preserve_meal_slots=(
                    preserve_meal_slots
                ),
                replace_ingredient=(
                    replace_ingredient
                ),
            )

        except UnsupportedMealFilter as exc:
            raise ApiError(
                "VALIDATION_ERROR",
                str(exc),
                400,
                False,
            ) from exc

        except EdamamUnavailable as exc:
            raise ApiError(
                "UPSTREAM_UNAVAILABLE",
                str(exc),
                502,
                True,
            ) from exc

        if not isinstance(meal_result, dict):
            raise ValueError(
                "Meal replanner returned an invalid result."
            )

        required_fields = {
            "meals",
            "ingredients",
            "nutrition_summary",
        }

        missing_fields = (
            required_fields
            - set(meal_result.keys())
        )

        if missing_fields:
            raise ValueError(
                "Meal replanner returned "
                "an invalid result. Missing fields: "
                + ", ".join(
                    sorted(missing_fields)
                )
            )

        if emit_progress is not None:
            emit_progress(
                "meals",
                (
                    "Meal replan completed: "
                    f"{len(meal_result['meals'])} meals."
                ),
            )

        return meal_result

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

        try:
            meal_result = build_meal_plan(
                request=request,
                effective_context=context,
            )
        except UnsupportedMealFilter as exc:
            raise ApiError(
                "VALIDATION_ERROR",
                str(exc),
                400,
                False,
            ) from exc
        except EdamamUnavailable as exc:
            raise ApiError(
                "UPSTREAM_UNAVAILABLE",
                str(exc),
                502,
                True,
            ) from exc

        meals = meal_result[
            "meals"
        ]

        ingredients = meal_result[
            "ingredients"
        ]

        nutrition_summary = meal_result[
            "nutrition_summary"
        ]

        warnings.extend(
            meal_result.get(
                "warnings",
                [],
            )
        )
        meal_source = meal_result.get(
            "source",
            "synthetic",
        )
        data_mode = (
            "mixed"
            if meal_source in {
                "edamam",
                "mixed",
            }
            else "demo"
        )
        if data_mode == "mixed":
            warnings.append(
                "Meal data is live or mixed while catalog/cart data remains demo; cart confirmation is disabled."
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
            data_mode
            == "demo"

            and

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

            data_mode=data_mode,

            effective_request=request,

            meal_plan=meals,

            nutrition_summary=(
                nutrition_summary
            ),

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

    
    def handle_chat_message(
            self,
            message,
            previous_result,
            session,
            emit_progress,
            current_request=None,
            selected_recurring_ids=None,
        ):
        """
        Entry point for natural-language changes
        to an existing planning result.

        Gemini decides WHAT the user wants.
        Python handlers decide HOW to execute it.
        """

        try:
            command = (
                self._get_chat_interpreter()
                .interpret(message)
            )

        except Exception:
            return {
                "type": "chat_error",
                "message": (
                    "I could not understand the request "
                    "because the AI interpreter is unavailable. "
                    "Please try again."
                ),
            }
        requires_existing_plan = {
            "change_budget",
            "reduce_cost",
            "upgrade_plan",
            "replace_ingredient",
            "explain_plan",
        }

        if (
            command.intent in requires_existing_plan
            and previous_result is None
        ):
            return {
                "type": "clarification",
                "message": (
                    "Please create a plan before "
                    "trying to modify it."
                ),
                "command": command.model_dump(),
            }

        if command.intent == "create_plan":
            return self._handle_create_plan(
                command=command,
                previous_result=previous_result,
                current_request=current_request,
                session=session,
                emit_progress=emit_progress,
            )

        if command.intent == "recalculate_plan":
            return self._handle_recalculate_plan(
                command=command,
                previous_result=previous_result,
                selected_recurring_ids=(
                    selected_recurring_ids
                ),
                session=session,
                emit_progress=emit_progress,
            )
        
        handlers = {
            "change_budget":
                self._handle_change_budget,

            "reduce_cost":
                self._handle_reduce_cost,

            "upgrade_plan":
                self._handle_upgrade_plan,

            "replace_ingredient":
                self._handle_replace_ingredient,

            "explain_plan":
                self._handle_explain_plan,
        }

        handler = handlers.get(
            command.intent
        )

        if handler is None:
            return {
                "type": "unsupported",
                "message": (
                    "I could not map this request "
                    "to a supported planning action."
                ),
                "command": command.model_dump(),
            }

        return handler(
            command=command,
            previous_result=previous_result,
            session=session,
            emit_progress=emit_progress,
        )

    def _handle_change_budget(
        self,
        command,
        previous_result,
        session,
        emit_progress,
    ):
        if previous_result is None:
            return {
                "type": "clarification",
                "message": (
                    "Please create a plan before "
                    "changing its budget."
                ),
                "command": command.model_dump(),
            }

        if command.budget_uah is None:
            return {
                "type": "clarification",
                "message": (
                    "Please specify the new budget in UAH."
                ),
                "command": command.model_dump(),
            }

        if command.budget_uah <= 0:
            return {
                "type": "clarification",
                "message": (
                    "Budget must be greater than zero."
                ),
                "command": command.model_dump(),
            }

        old_budget_minor = (
            previous_result
            .budget_minor
        )

        new_budget_minor = (
            command.budget_uah * 100
        )

        # Nothing actually changed.
        if (
            new_budget_minor
            == old_budget_minor
        ):
            return previous_result

        new_request = (
            previous_result
            .effective_request
            .model_copy(
                update={
                    "budget_minor":
                        new_budget_minor
                }
            )
        )

        current_total = (
            previous_result
            .basket_total_minor
        )

        budget_remaining_minor = (
            new_budget_minor
            - current_total
        )

        if (
            previous_result
            .unresolved_requirements
        ):
            budget_status = "incomplete"

        elif budget_remaining_minor < 0:
            budget_status = "over_budget"

        else:
            budget_status = "within_budget"

        context = (
            self.catalog
            .get_user_context(session)
        )

        can_confirm_cart = (
            previous_result.data_mode
            == "demo"

            and

            budget_status
            == "within_budget"

            and len(
                previous_result
                .unresolved_requirements
            )
            == 0

            and context.cart_context_ready
        )

        # Temporary result with the NEW budget.
        #
        # Version is intentionally NOT increased yet.
        # The branch that produces the final result
        # will increase it exactly once.
        budget_updated_result = (
            previous_result
            .model_copy(
                update={
                    "effective_request":
                        new_request,

                    "budget_minor":
                        new_budget_minor,

                    "budget_remaining_minor":
                        budget_remaining_minor,

                    "budget_status":
                        budget_status,

                    "can_confirm_cart":
                        can_confirm_cart,
                }
            )
        )

        # ====================================================
        # NEW BUDGET IS LOWER
        # → try to make the plan cheaper
        # ====================================================

        if (
            new_budget_minor
            < old_budget_minor
        ):
            emit_progress(
                "optimization",
                (
                    "Budget decreased. "
                    "Trying to reduce plan cost."
                ),
            )

            reduce_command = (
                command.model_copy(
                    update={
                        "intent":
                            "reduce_cost"
                    }
                )
            )

            result = (
                self._handle_reduce_cost(
                    command=reduce_command,
                    previous_result=(
                        budget_updated_result
                    ),
                    session=session,
                    emit_progress=emit_progress,
                )
            )

            if isinstance(
                result,
                PlanningResult,
            ):
                return result

            # The budget change itself is still valid,
            # even if automatic replanning is unavailable
            # or no cheaper plan was found.
            warnings = list(
                budget_updated_result.warnings
            )

            message = result.get(
                "message"
            )

            if message:
                warnings.append(
                    (
                        "Budget was changed, but "
                        "automatic cost reduction "
                        f"was not completed: {message}"
                    )
                )

            return (
                budget_updated_result
                .model_copy(
                    update={
                        "version":
                            previous_result.version
                            + 1,

                        "warnings":
                            warnings,
                    }
                )
            )

        # ====================================================
        # NEW BUDGET IS HIGHER
        # → try to improve / diversify the plan
        # ====================================================

        emit_progress(
            "meals",
            (
                "Budget increased. "
                "Trying to upgrade the meal plan."
            ),
        )

        upgrade_command = (
            command.model_copy(
                update={
                    "intent":
                        "upgrade_plan"
                }
            )
        )

        result = (
            self._handle_upgrade_plan(
                command=upgrade_command,
                previous_result=(
                    budget_updated_result
                ),
                session=session,
                emit_progress=emit_progress,
            )
        )

        if isinstance(
            result,
            PlanningResult,
        ):
            return result

        # Same rule:
        # new budget stays valid even if
        # automatic meal upgrade cannot run yet.
        warnings = list(
            budget_updated_result.warnings
        )

        message = result.get(
            "message"
        )

        if message:
            warnings.append(
                (
                    "Budget was changed, but "
                    "automatic plan upgrade "
                    f"was not completed: {message}"
                )
            )

        return (
            budget_updated_result
            .model_copy(
                update={
                    "version":
                        previous_result.version
                        + 1,

                    "warnings":
                        warnings,
                }
            )
        )

    def _handle_explain_plan(
        self,
        command,
        previous_result,
        session,
        emit_progress,
    ):
        budget_uah = (
            previous_result.budget_minor
            / 100
        )

        total_uah = (
            previous_result
            .basket_total_minor
            / 100
        )

        remaining_uah = (
            previous_result
            .budget_remaining_minor
            / 100
        )

        if (
            previous_result.budget_status
            == "over_budget"
        ):
            message = (
                f"The basket costs "
                f"{total_uah:.2f} UAH, "
                f"while the budget is "
                f"{budget_uah:.2f} UAH. "
                f"The plan exceeds the budget by "
                f"{abs(remaining_uah):.2f} UAH."
            )

        elif (
            previous_result.budget_status
            == "incomplete"
        ):
            message = (
                "The plan is incomplete because "
                f"{len(previous_result.unresolved_requirements)} "
                "requirements could not be resolved."
            )

        else:
            message = (
                f"The basket costs "
                f"{total_uah:.2f} UAH. "
                f"The remaining budget is "
                f"{remaining_uah:.2f} UAH."
            )

        return {
            "type": "explanation",
            "message": message,
            "command": command.model_dump(),
        }

    def _build_updated_result(
        self,
        previous_result,
        optimization,
        context,
        recurring_items=None,
    ):
        can_confirm_cart = (
            previous_result.data_mode == "demo"

            and optimization.budget_status
                == "within_budget"

            and len(
                optimization.unresolved_requirements
            ) == 0

            and context.cart_context_ready
        )

        updates = {
            "version":
                previous_result.version + 1,

            "selected_products":
                optimization.selected_products,

            "substitutions":
                optimization.substitutions,

            "basket_total_minor":
                optimization.basket_total_minor,

            "budget_remaining_minor":
                optimization.budget_remaining_minor,

            "savings_minor":
                optimization.savings_minor,

            "budget_status":
                optimization.budget_status,

            "unresolved_requirements":
                optimization.unresolved_requirements,

            "can_confirm_cart":
                can_confirm_cart,
        }

        if recurring_items is not None:
            updates["recurring_items"] = recurring_items

        return previous_result.model_copy(
            update=updates
        )

    def _build_replanned_result(
        self,
        previous_result,
        meal_result,
        optimization,
        context,
    ):
        meal_source = meal_result.get(
            "source",
            "synthetic",
        )

        data_mode = (
            "mixed"
            if meal_source in {
                "edamam",
                "mixed",
            }
            else "demo"
        )

        warnings = list(
            previous_result.warnings
        )

        for warning in meal_result.get(
            "warnings",
            [],
        ):
            if warning not in warnings:
                warnings.append(warning)

        if data_mode == "mixed":
            mixed_warning = (
                "Meal data is live or mixed while "
                "catalog/cart data remains demo; "
                "cart confirmation is disabled."
            )

            if mixed_warning not in warnings:
                warnings.append(
                    mixed_warning
                )

        can_confirm_cart = (
            data_mode == "demo"

            and

            optimization.budget_status
            == "within_budget"

            and len(
                optimization
                .unresolved_requirements
            )
            == 0

            and context.cart_context_ready
        )

        return previous_result.model_copy(
            update={
                "version":
                    previous_result.version + 1,

                "data_mode":
                    data_mode,

                "meal_plan":
                    meal_result["meals"],

                "nutrition_summary":
                    meal_result[
                        "nutrition_summary"
                    ],

                "ingredients":
                    meal_result["ingredients"],

                "selected_products":
                    optimization.selected_products,

                "substitutions":
                    optimization.substitutions,

                "basket_total_minor":
                    optimization.basket_total_minor,

                "budget_remaining_minor":
                    optimization
                    .budget_remaining_minor,

                "savings_minor":
                    optimization.savings_minor,

                "budget_status":
                    optimization.budget_status,

                "unresolved_requirements":
                    optimization
                    .unresolved_requirements,

                "warnings":
                    warnings,

                "can_confirm_cart":
                    can_confirm_cart,
            }
        )
    
    def _handle_reduce_cost(
            self,
            command,
            previous_result,
            session,
            emit_progress,
        ):
            request = (
                previous_result
                .effective_request
            )

            recurring_items = (
                previous_result.recurring_items
            )

            selected_recurring = [
                item
                for item in recurring_items
                if item.selected
            ]

            context = (
                self.catalog
                .get_user_context(session)
            )

            # previous_result is already product-optimized
            # for its current ingredients by run_planner().
            #
            # Therefore reduce_cost does NOT repeat
            # matching + optimization for the old ingredients.
            #
            # Instead, we move directly to one bounded
            # meal-level replan.
            meal_result = (
                self._request_meal_replan(
                    request=request,
                    context=context,
                    previous_meals=(
                        previous_result.meal_plan
                    ),
                    reason="reduce_cost",
                    preserve_meal_slots=(
                        command.preserve_meal_slots
                    ),
                    emit_progress=emit_progress,
                )
            )

            # Sofiia's real meal replanner is not connected yet.
            # Keep backward-compatible behavior until it exists.
            if meal_result is None:
                return {
                    "type":
                        "meal_replan_required",

                    "message": (
                        "The current basket is already "
                        "product-optimized. Reducing the "
                        "cost further requires meal replanning."
                    ),

                    "preserveMealSlots":
                        command.preserve_meal_slots,

                    "command":
                        command.model_dump(),
                }

            # These are NEW ingredients returned
            # by Sofiia after the meal-level replan.
            replanned_ingredients = (
                meal_result["ingredients"]
            )

            matching_context = MatchingContext(
                session=session,
                catalog=self.catalog,
                check_restrictions=(
                    self.catalog
                    .check_restrictions
                ),
            )

            # Now matching makes sense again,
            # because ingredients have changed.
            try:
                matching_result = (
                    find_product_candidates(
                        replanned_ingredients,
                        selected_recurring,
                        matching_context,
                    )
                )

            except ValueError as error:
                return {
                    "type": "blocked",
                    "message": str(error),
                    "command": command.model_dump(),
                }

            emit_progress(
                "matching",
                (
                    "Product matching completed "
                    "for replanned meals."
                ),
            )

            # Vika now chooses the cheapest valid
            # products for the NEW ingredients.
            optimization = optimize_basket(
                request=request,
                ingredients=replanned_ingredients,
                candidates=matching_result,
                selected_recurring=(
                    selected_recurring
                ),
            )
            if (
                optimization.basket_total_minor
                >= previous_result.basket_total_minor
            ):
                return {
                    "type": "no_cost_improvement",
                    "message": (
                        "A cheaper plan could not be found "
                        "while preserving the requested constraints."
                    ),
                    "previousBasketTotalMinor":
                        previous_result.basket_total_minor,
                    "candidateBasketTotalMinor":
                        optimization.basket_total_minor,
                    "preserveMealSlots":
                        command.preserve_meal_slots,
                    "command":
                        command.model_dump(),
                }

            emit_progress(
                "optimization",
                (
                    "Basket optimization completed "
                    "after meal replan."
                ),
            )

            # Build one coherent result:
            # new meals + new ingredients + new products
            # + new totals.
            return self._build_replanned_result(
                previous_result=previous_result,
                meal_result=meal_result,
                optimization=optimization,
                context=context,
            )
    def _handle_upgrade_plan(
        self,
        command,
        previous_result,
        session,
        emit_progress,
    ):
        if previous_result is None:
            return {
                "type": "clarification",
                "message": (
                    "Please create a plan before "
                    "upgrading it."
                ),
                "command": command.model_dump(),
            }

        request = (
            previous_result
            .effective_request
        )

        context = (
            self.catalog
            .get_user_context(session)
        )

        recurring_items = (
            previous_result.recurring_items
        )

        selected_recurring = [
            item
            for item in recurring_items
            if item.selected
        ]

        # Ask Sofiia to improve the meal plan.
        #
        # The current request already contains
        # the budget that the upgraded plan
        # must respect.
        meal_result = (
            self._request_meal_replan(
                request=request,
                context=context,
                previous_meals=(
                    previous_result.meal_plan
                ),
                reason="upgrade_plan",
                preserve_meal_slots=(
                    command.preserve_meal_slots
                ),
                emit_progress=emit_progress,
            )
        )

        # Until Sofiia implements the real
        # replan boundary.
        if meal_result is None:
            return {
                "type":
                    "meal_replan_required",

                "message": (
                    "Upgrading the current plan "
                    "requires meal replanning."
                ),

                "reason":
                    "upgrade_plan",

                "budgetMinor":
                    request.budget_minor,

                "preserveMealSlots":
                    command.preserve_meal_slots,

                "command":
                    command.model_dump(),
            }

        replanned_ingredients = (
            meal_result["ingredients"]
        )

        matching_context = MatchingContext(
            session=session,
            catalog=self.catalog,
            check_restrictions=(
                self.catalog
                .check_restrictions
            ),
        )

        try:
            matching_result = (
                find_product_candidates(
                    replanned_ingredients,
                    selected_recurring,
                    matching_context,
                )
            )

        except ValueError as error:
            return {
                "type": "blocked",
                "message": str(error),
                "command": command.model_dump(),
            }

        emit_progress(
            "matching",
            (
                "Product matching completed "
                "for the upgraded meal plan."
            ),
        )

        optimization = optimize_basket(
            request=request,
            ingredients=replanned_ingredients,
            candidates=matching_result,
            selected_recurring=(
                selected_recurring
            ),
        )

        # An upgrade must still respect
        # the available budget.
        if (
            optimization.budget_status
            != "within_budget"

            or

            optimization
            .unresolved_requirements
        ):
            return {
                "type":
                    "upgrade_not_feasible",

                "message": (
                    "An upgraded meal plan was found, "
                    "but it could not be completed "
                    "within the available budget."
                ),

                "budgetMinor":
                    request.budget_minor,

                "candidateBasketTotalMinor":
                    optimization
                    .basket_total_minor,

                "command":
                    command.model_dump(),
            }

        emit_progress(
            "optimization",
            (
                "Upgraded meal plan fits "
                "the available budget."
            ),
        )

        return self._build_replanned_result(
            previous_result=previous_result,
            meal_result=meal_result,
            optimization=optimization,
            context=context,
        )

    def _handle_replace_ingredient(
        self,
        command,
        previous_result,
        session,
        emit_progress,
    ):
        if not command.ingredient:
            return {
                "type": "clarification",
                "message": (
                    "Please specify which ingredient "
                    "you want to replace."
                ),
                "command": command.model_dump(),
            }

        requested_name = (
            command.ingredient
            .strip()
            .lower()
        )

        target = None

        for ingredient in previous_result.ingredients:
            searchable_names = [
                ingredient.name.lower(),
                *[
                    term.lower()
                    for term in ingredient.search_terms
                ],
            ]

            if any(
                requested_name in name
                or name in requested_name
                for name in searchable_names
            ):
                target = ingredient
                break

        if target is None:
            return {
                "type": "clarification",
                "message": (
                    f"Ingredient '{command.ingredient}' "
                    "was not found in the current plan."
                ),
                "command": command.model_dump(),
            }

        request = (
            previous_result
            .effective_request
        )

        context = (
            self.catalog
            .get_user_context(session)
        )

        meal_result = (
            self._request_meal_replan(
                request=request,
                context=context,
                previous_meals=(
                    previous_result.meal_plan
                ),
                reason="replace_ingredient",
                preserve_meal_slots=(
                    command.preserve_meal_slots
                ),
                replace_ingredient=(
                    target.name
                ),
                emit_progress=emit_progress,
            )
        )

        if meal_result is None:
            return {
                "type":
                    "meal_replan_required",

                "message": (
                    f"Ingredient '{target.name}' "
                    "was found. Replacing it requires "
                    "meal replanning."
                ),

                "ingredientId":
                    target.id,

                "ingredient":
                    target.name,

                "preserveMealSlots":
                    command.preserve_meal_slots,

                "command":
                    command.model_dump(),
            }

        recurring_items = (
            previous_result.recurring_items
        )

        selected_recurring = [
            item
            for item in recurring_items
            if item.selected
        ]

        replanned_ingredients = (
            meal_result["ingredients"]
        )
        target_still_present = any(
            ingredient.id == target.id
            or ingredient.name.strip().lower()
            == target.name.strip().lower()
            for ingredient
            in replanned_ingredients
        )

        if target_still_present:
            return {
                "type": "invalid_replan",
                "message": (
                    f"Ingredient '{target.name}' "
                    "was not replaced by the meal replanner."
                ),
                "ingredientId": target.id,
                "ingredient": target.name,
                "command": command.model_dump(),
            }
        matching_context = MatchingContext(
            session=session,
            catalog=self.catalog,
            check_restrictions=(
                self.catalog
                .check_restrictions
            ),
        )

        try:
            matching_result = (
                find_product_candidates(
                    replanned_ingredients,
                    selected_recurring,
                    matching_context,
                )
            )

        except ValueError as error:
            return {
                "type": "blocked",
                "message": str(error),
                "command": command.model_dump(),
            }

        emit_progress(
            "matching",
            (
                "Product matching refreshed "
                "after ingredient replacement."
            ),
        )

        optimization = optimize_basket(
            request=request,
            ingredients=replanned_ingredients,
            candidates=matching_result,
            selected_recurring=(
                selected_recurring
            ),
        )

        emit_progress(
            "optimization",
            (
                "Basket optimization completed "
                "after ingredient replacement."
            ),
        )

        return self._build_replanned_result(
            previous_result=previous_result,
            meal_result=meal_result,
            optimization=optimization,
            context=context,
        )
    
    def _handle_create_plan(
        self,
        command,
        previous_result,
        current_request,
        session,
        emit_progress,
    ):
        request = current_request

        if request is None and previous_result is not None:
            request = (
                previous_result
                .effective_request
            )

        if request is None:
            return {
                "type": "clarification",
                "message": (
                    "Please fill in the planning parameters "
                    "before creating the basket."
                ),
                "command": command.model_dump(),
            }

        if command.budget_uah is not None:
            request = request.model_copy(
                update={
                    "budget_minor":
                        command.budget_uah * 100
                }
            )

        return self.run_planner(
            request=request,
            session=session,
            emit_progress=emit_progress,
        )

    def _handle_recalculate_plan(
        self,
        command,
        previous_result,
        selected_recurring_ids,
        session,
        emit_progress,
    ):
        if previous_result is None:
            return {
                "type": "clarification",
                "message": (
                    "There is no existing plan "
                    "to recalculate."
                ),
                "command": command.model_dump(),
            }

        if selected_recurring_ids is None:
            selected_recurring_ids = [
                item.id
                for item
                in previous_result.recurring_items
                if item.selected
            ]

        return self.recalculate_plan(
            previous_result=previous_result,
            selected_recurring_ids=(
                selected_recurring_ids
            ),
            session=session,
            emit_progress=emit_progress,
        )

    def recalculate_plan(
        self,
        previous_result,
        selected_recurring_ids,
        session,
        emit_progress,
    ):
        """
        Recalculate an existing proposal
        after recurring-item selection changes.

        Meals and ingredients are reused.
        Matching and optimization are refreshed.
        """

        selected_ids = set(
            selected_recurring_ids or []
        )

        known_ids = {
            item.id
            for item
            in previous_result.recurring_items
        }

        unknown_ids = (
            selected_ids - known_ids
        )

        if unknown_ids:
            raise ValueError(
                "Unknown recurring suggestion IDs: "
                + ", ".join(sorted(unknown_ids))
            )

        recurring_items = [
            item.model_copy(
                update={
                    "selected":
                        item.id in selected_ids
                }
            )
            for item
            in previous_result.recurring_items
        ]

        selected_recurring = [
            item
            for item in recurring_items
            if item.selected
        ]

        request = (
            previous_result
            .effective_request
        )

        ingredients = (
            previous_result.ingredients
        )

        context = (
            self.catalog
            .get_user_context(session)
        )

        emit_progress(
            "context",
            "User context refreshed.",
        )
        
        matching_context = MatchingContext(
            session=session,
            catalog=self.catalog,
            check_restrictions=self.catalog.check_restrictions,
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
            "Product matching refreshed.",
        )

        optimization = optimize_basket(
            request=request,
            ingredients=ingredients,
            candidates=matching_result,
            selected_recurring=(
                selected_recurring
            ),
        )

        emit_progress(
            "optimization",
            (
                "Basket recalculated. "
                f"Status: "
                f"{optimization.budget_status}."
            ),
        )

        return self._build_updated_result(
            previous_result=previous_result,
            optimization=optimization,
            context=context,
            recurring_items=recurring_items,
        )