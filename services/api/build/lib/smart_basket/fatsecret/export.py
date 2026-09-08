"""Preview and asynchronous simulated Saved Meal operations, scoped to one session."""

from smart_basket.core import ApiError, DEMO_WARNING, expires, require_fresh, uid
from smart_basket.fatsecret.matching import match_personal_portion
from smart_basket.schemas import Error, ExportMealOutcome, FatSecretExport, FatSecretPreview


class DemoExportService:
    def preview(self, request, session, scenario="success"):
        with session.lock:
            plan = session.get_plan(request.run_id, request.version)
            meals = {m.id: m for m in plan.meal_plan}
            if len(set(request.meal_ids)) != len(request.meal_ids) or set(request.meal_ids) - meals.keys():
                raise ApiError("VALIDATION_ERROR", "Select unique meal IDs from this plan.", 400)
            matched = [match_personal_portion(meals[id], force_unmatched=scenario == "unmatched")
                       for id in request.meal_ids]
            preview = FatSecretPreview(preview_id=uid("export-preview"), run_id=plan.run_id,
                version=plan.version, account_label="Demo account (no FatSecret connection)",
                expires_at=expires(), can_confirm=not any(m.unresolved for m in matched),
                meals=matched, warnings=[DEMO_WARNING, "Nutrition comparison is unavailable in demo mode.",
                                        f"Simulated export outcome: {scenario}."])
            session.export_previews[preview.preview_id] = (preview, scenario)
            return preview

    def confirm(self, request, session):
        with session.lock:
            if request.preview_id not in session.export_previews:
                raise ApiError("NOT_FOUND", "Export preview not found in this session.", 404)
            prior = session.export_keys.get(request.idempotency_key)
            if prior:
                if prior[0] != request.preview_id:
                    raise ApiError("IDEMPOTENCY_CONFLICT", "This key belongs to another export preview.")
                return prior[1], False
            preview, scenario = session.export_previews[request.preview_id]
            if request.preview_id in session.export_operations:
                export_id = session.export_operations[request.preview_id]
                session.export_keys[request.idempotency_key] = (request.preview_id, export_id)
                return export_id, False
            require_fresh(preview)
            session.get_plan(preview.run_id, preview.version)
            if not preview.can_confirm:
                raise ApiError("UNRESOLVED_FOODS", "Select only completely matched meals in a new preview.")
            # Bind equivalent selections to the same operation even with a new preview/key.
            identity = (preview.run_id, preview.version, tuple(sorted(m.meal_id for m in preview.meals)))
            if identity in session.export_operations:
                export_id = session.export_operations[identity]
                session.export_operations[request.preview_id] = export_id
                session.export_keys[request.idempotency_key] = (request.preview_id, export_id)
                return export_id, False
            export_id = uid("export")
            session.exports[export_id] = FatSecretExport(export_id=export_id, status="queued",
                meals=[ExportMealOutcome(meal_id=m.meal_id, status="pending", saved_meal_id=None,
                    message="Queued for simulated saving.") for m in preview.meals], error=None,
                warnings=[DEMO_WARNING])
            session.export_operations[identity] = export_id
            session.export_operations[request.preview_id] = export_id
            session.export_keys[request.idempotency_key] = (request.preview_id, export_id)
            return export_id, True

    def execute(self, export_id, preview_id, session):
        with session.lock:
            operation = session.exports[export_id]
            preview, scenario = session.export_previews[preview_id]
            operation.status = "running"
            try:
                session.get_plan(preview.run_id, preview.version)
                for index, meal in enumerate(operation.meals):
                    identity = (preview.run_id, preview.version, meal.meal_id)
                    if identity in session.saved_meals:
                        meal.status = "already_saved"
                        meal.saved_meal_id = session.saved_meals[identity]
                        meal.message = "Previously saved demo meal reused."
                    elif scenario == "success" or (scenario == "partial" and index == 0):
                        session.saved_meals[identity] = uid("saved-meal")
                        meal.saved_meal_id = session.saved_meals[identity]
                        meal.status = "saved"
                        meal.message = "Demo Saved Meal recorded; no provider call made."
                    else:
                        meal.status = "failed"
                        meal.message = "Simulated provider failure; meal was not saved."
                successes = sum(m.status in {"saved", "already_saved"} for m in operation.meals)
                operation.status = "success" if successes == len(operation.meals) else "partial" if successes else "failed"
                if operation.status != "success":
                    operation.error = Error(code="UPSTREAM_UNAVAILABLE", message="Simulated FatSecret failure.", retryable=False)
            except Exception:
                operation.status = "failed"
                operation.error = Error(code="EXPORT_FAILED", message="Export could not finish. Review the plan.", retryable=False)
                for meal in operation.meals:
                    if meal.status == "pending":
                        meal.status = "failed"
                        meal.message = "Export stopped before this meal was saved."
