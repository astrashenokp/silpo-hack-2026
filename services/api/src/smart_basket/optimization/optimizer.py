from __future__ import annotations

from dataclasses import dataclass

from smart_basket.catalog.matching import line_total, purchase_quantity
from smart_basket.schemas import (
    CandidateResult,
    IngredientRequirement,
    PlanningRequest,
    ProductCandidate,
    ProductSelection,
    RecurringSuggestion,
    Substitution,
    UnresolvedRequirement,
)


@dataclass
class OptimizationResult:
    selected_products: list[ProductSelection]
    substitutions: list[Substitution]
    basket_total_minor: int
    budget_remaining_minor: int
    budget_status: str  # "within_budget" | "over_budget" | "incomplete"
    unresolved_requirements: list[UnresolvedRequirement]
    savings_minor: int | None
    replan_reason: str | None = None


def optimize_basket(
    request: PlanningRequest,
    ingredients: list[IngredientRequirement],
    candidates: CandidateResult,
    selected_recurring: list[RecurringSuggestion],
) -> OptimizationResult:

    selections: list[ProductSelection] = []
    pending: dict[str, tuple[ProductCandidate, float, list[str], list[str]]] = {}

    # Починаємо з того, що вже позначила нерозв'язаним сама Ріна
    # (наприклад: обмеження не пройшли перевірку, або одиниці виміру
    # несумісні для ВСІХ знайдених кандидатів).
    unresolved: list[UnresolvedRequirement] = list(candidates.unresolved_requirements)
    already_unresolved_ids = {u.requirement_id for u in unresolved}

    verified_savings_total = 0
    has_verified_savings = False

    # --- інгредієнти зі страв ---
    for req in ingredients:
        if req.id in already_unresolved_ids:
            continue

        picked = _pick_best_candidate(req.id, req.quantity, req.unit, candidates.candidates)
        if picked is None:
            unresolved.append(UnresolvedRequirement(
                requirement_id=req.id,
                reason="Немає доступного кандидата з відповідною одиницею "
                       "виміру й пройденою перевіркою обмежень.",
            ))
            continue

        selection, _, candidate = picked
        _add_pending(pending, candidate, req.quantity, [req.id], [])

    # --- обрані користувачем регулярні покупки / товари для тварин ---
    for rec in selected_recurring:
        picked = _pick_best_candidate(
            rec.id, rec.suggested_quantity, rec.unit, candidates.candidates,
            recurring_suggestion_ids=[rec.id],
        )
        if picked is None:
            unresolved.append(UnresolvedRequirement(
                requirement_id=rec.id,
                reason="Кандидат для цієї регулярної покупки ще недоступний "
                       "(очікує на реалізацію відповідності в Ріни).",
            ))
            continue

        selection, _, candidate = picked
        existing = pending.get(selection.product_id)
        if existing is not None:
            candidate, quantity, requirement_ids, recurring_ids = existing
            pending[selection.product_id] = (
                candidate,
                quantity,
                requirement_ids,
                list(dict.fromkeys(recurring_ids + [rec.id])),
            )
            continue
        _add_pending(pending, candidate, rec.suggested_quantity, [], [rec.id])

    for candidate, needed_qty, requirement_ids, recurring_ids in pending.values():
        quantity = purchase_quantity(needed_qty, candidate.content_unit, candidate)
        total = line_total(quantity, candidate.price_minor)
        savings = None
        if (candidate.regular_price_minor is not None
                and candidate.regular_price_minor > candidate.price_minor):
            savings = line_total(quantity, candidate.regular_price_minor) - total
            verified_savings_total += savings
            has_verified_savings = True
        selections.append(ProductSelection(
            product_id=candidate.id,
            name=candidate.name,
            requirement_ids=requirement_ids,
            recurring_suggestion_ids=recurring_ids,
            quantity=quantity,
            selling_unit=candidate.selling_unit,
            unit_price_minor=candidate.price_minor,
            line_total_minor=total,
            source=candidate.source,
            reason="Попит об'єднано перед округленням упаковок.",
            restriction_check=candidate.restriction_check,
        ))

    # --- підсумки бюджету ---
    basket_total = sum(s.line_total_minor for s in selections)
    remaining = request.budget_minor - basket_total

    if remaining < 0:
        status = "over_budget"
    elif unresolved:
        status = "incomplete"
    else:
        status = "within_budget"

    return OptimizationResult(
        selected_products=selections,
        substitutions=[],
        basket_total_minor=basket_total,
        budget_remaining_minor=remaining,
        budget_status=status,
        unresolved_requirements=unresolved,
        savings_minor=verified_savings_total if has_verified_savings else None,
    )


def _add_pending(
    pending: dict[str, tuple[ProductCandidate, float, list[str], list[str]]],
    candidate: ProductCandidate,
    needed_quantity: float,
    requirement_ids: list[str],
    recurring_ids: list[str],
) -> None:
    existing = pending.get(candidate.id)
    if existing is None:
        pending[candidate.id] = (
            candidate,
            needed_quantity,
            requirement_ids,
            recurring_ids,
        )
        return
    candidate, quantity, existing_requirements, existing_recurring = existing
    pending[candidate.id] = (
        candidate,
        quantity + needed_quantity,
        list(dict.fromkeys(existing_requirements + requirement_ids)),
        list(dict.fromkeys(existing_recurring + recurring_ids)),
    )


def _pick_best_candidate(
    requirement_id: str,
    needed_qty: float,
    unit: str,
    all_candidates: list[ProductCandidate],
    recurring_suggestion_ids: list[str] | None = None,
) -> tuple[ProductSelection, int | None, ProductCandidate] | None:
    """
    Серед усіх кандидатів обирає найдешевший ПРИДАТНИЙ варіант, що
    покриває ПОВНУ потрібну кількість — не за ціною однієї упаковки,
    а за загальною вартістю покриття вимоги (packages_needed * price).
    """
    valid = [
        c for c in all_candidates
        if requirement_id in c.requirement_ids
        and c.available
        and c.restriction_check == "pass"
        and c.content_quantity is not None
        and c.content_unit == unit
    ]
    if not valid:
        return None

    best = None
    best_qty = None
    best_total = None
    for c in valid:
        qty = purchase_quantity(needed_qty, unit, c)   
        total = line_total(qty, c.price_minor)          
        if best_total is None or total < best_total:
            best, best_qty, best_total = c, qty, total

    # Якщо є перевірена регулярна ціна (regularPriceMinor) і вона вища
    # за поточну — це підтверджена акція, і ми МОЖЕМО показати економію.
    savings = None
    if best.regular_price_minor is not None and best.regular_price_minor > best.price_minor:
        baseline_total = line_total(best_qty, best.regular_price_minor)
        savings = baseline_total - best_total

    selection = ProductSelection(
        product_id=best.id,
        name=best.name,
        requirement_ids=[requirement_id],
        recurring_suggestion_ids=recurring_suggestion_ids or [],
        quantity=best_qty,
        selling_unit=best.selling_unit,
        unit_price_minor=best.price_minor,
        line_total_minor=best_total,
        source=best.source,
        reason="Найдешевший доступний кандидат, що покриває повну потрібну кількість.",
        restriction_check=best.restriction_check,
    )
    return selection, savings, best
