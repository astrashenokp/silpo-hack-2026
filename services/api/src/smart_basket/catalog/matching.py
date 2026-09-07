"""Rina's matching layer. Catalog functions return normalized ProductCandidate data."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Callable, Protocol

from smart_basket.schemas import (
    CandidateResult, IngredientRequirement, ProductCandidate, UnresolvedRequirement,
)


class CatalogReader(Protocol):
    def search_products(self, session: object, query: str) -> list[ProductCandidate]: ...
    def get_product_details(self, session: object, id: str) -> ProductCandidate: ...


@dataclass
class MatchingContext:
    session: object
    catalog: CatalogReader
    check_restrictions: Callable[[ProductCandidate, list[str]], str] | None = None


def purchase_quantity(quantity: float, unit: str, product: ProductCandidate) -> float:
    """Convert demand to selling units, rounding up to the actual sale increment."""
    if product.content_quantity is None or product.content_unit != unit:
        raise ValueError("Missing or incompatible content conversion; g and ml are not interchangeable.")
    step = Decimal(str(product.quantity_step))
    units = Decimal(str(quantity)) / Decimal(str(product.content_quantity))
    return float((units / step).to_integral_value(rounding=ROUND_CEILING) * step)


def line_total(quantity: float, price_minor: int) -> int:
    return int((Decimal(str(quantity)) * price_minor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def find_product_candidates(ingredients, selected_recurring, context: MatchingContext) -> CandidateResult:
    """Keep unsafe/unavailable candidates visible as evidence, but report no safe match.

    A composition evaluator must verify the requested restriction labels; without
    it restricted requirements fail closed. Never infer safety from a product name.
    selected_recurring items must be normalized by Vika before catalog lookup;
    this first ingredient matcher intentionally does not invent pet-food demand.
    """
    if selected_recurring:
        raise ValueError("Recurring candidate lookup awaits Vika's normalized requirements.")
    merged: dict[str, ProductCandidate] = {}
    for requirement in ingredients:
        seen = set()
        for term in requirement.search_terms or [requirement.name]:
            for hit in context.catalog.search_products(context.session, term):
                if hit.id in seen:
                    continue
                seen.add(hit.id)
                candidate = context.catalog.get_product_details(context.session, hit.id)
                candidate = ProductCandidate.model_validate(candidate).model_copy(deep=True)
                if requirement.restrictions:
                    candidate.restriction_check = (context.check_restrictions(candidate, requirement.restrictions)
                        if context.check_restrictions else "unknown")
                    candidate = ProductCandidate.model_validate(candidate.model_dump())
                candidate.requirement_ids = [requirement.id]
                if candidate.id in merged:
                    checks = {merged[candidate.id].restriction_check, candidate.restriction_check}
                    candidate.restriction_check = "fail" if "fail" in checks else "unknown" if "unknown" in checks else "pass"
                    candidate.requirement_ids = list(dict.fromkeys(
                        merged[candidate.id].requirement_ids + candidate.requirement_ids))
                merged[candidate.id] = candidate
    unresolved = []
    for requirement in ingredients:
        safe = any(requirement.id in c.requirement_ids and c.available and c.restriction_check == "pass"
                   and c.content_quantity is not None and c.content_unit == requirement.unit
                   for c in merged.values())
        if not safe:
            unresolved.append(UnresolvedRequirement(requirement_id=requirement.id,
                reason="No available verified match with compatible package contents."))
    return CandidateResult(candidates=list(merged.values()), unresolved_requirements=unresolved)


def find_replacement(requirement: IngredientRequirement, rejected_ids: list[str], context: MatchingContext):
    result = find_product_candidates([requirement], [], context)
    result.candidates = [c for c in result.candidates if c.id not in rejected_ids and c.available
                         and c.restriction_check == "pass" and c.content_quantity is not None
                         and c.content_unit == requirement.unit]
    if not result.candidates and not result.unresolved_requirements:
        result.unresolved_requirements = [UnresolvedRequirement(requirement_id=requirement.id,
            reason="No suitable replacement remains after excluding rejected products.")]
    return result
