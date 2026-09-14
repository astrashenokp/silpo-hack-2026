import pytest

from smart_basket.catalog.matching import MatchingContext, find_product_candidates, find_replacement, line_total, purchase_quantity
from smart_basket.demo import CATEGORY_PRODUCTS, DemoCatalog
from smart_basket.schemas import IngredientRequirement


def edamam_ingredient(id, name, category, quantity=200.0):
    # Mirrors meals/edamam.py:_search_terms — [ingredient name, foodCategory (if any)].
    terms = [name] if category is None else [name, category]
    return IngredientRequirement(id=id, name=name, search_terms=terms,
        quantity=quantity, unit="g", meal_ids=["m1"], restrictions=[])


def ingredient(id="oats", quantity=750.0, unit="g"):
    return IngredientRequirement(id=id, name="Dry oats", search_terms=["oats"], quantity=quantity,
        unit=unit, meal_ids=["m1"], restrictions=[])


def test_package_rounding_and_weighted_price():
    product = DemoCatalog().products["demo-oats"]
    assert purchase_quantity(750, "g", product) == 2
    assert line_total(2, product.price_minor) == 12000
    weighted = product.model_copy(update={"selling_unit": "kg", "content_quantity": 1000.0, "quantity_step": 0.1})
    assert purchase_quantity(750, "g", weighted) == 0.8
    assert line_total(0.125, 1004) == 126
    with pytest.raises(ValueError):
        purchase_quantity(750, "ml", product)


def test_candidates_and_replacement_exclude_unsafe():
    catalog = DemoCatalog()
    context = MatchingContext(None, catalog)
    result = find_product_candidates([ingredient()], [], context)
    assert len(result.candidates) == 4
    assert result.unresolved_requirements == []
    assert find_replacement(ingredient(), [], context).candidates[0].id == "demo-oats"
    assert find_replacement(ingredient(), ["demo-oats"], context).candidates[0].id == "demo-oats-unknown"
    assert find_product_candidates([ingredient(unit="ml")], [], context).unresolved_requirements
    for product in catalog.products.values():
        product.available = False
    assert find_product_candidates([ingredient()], [], context).unresolved_requirements


def test_one_product_links_multiple_requirements():
    result = find_product_candidates([ingredient("a", 200.0), ingredient("b", 300.0)], [], MatchingContext(None, DemoCatalog()))
    assert len(result.candidates) == 4
    assert result.candidates[0].requirement_ids == ["a", "b"]


def test_restriction_evidence_is_required():
    requirement = ingredient().model_copy(update={"restrictions": ["peanut-free"]})
    catalog = DemoCatalog()
    result = find_product_candidates([requirement], [], MatchingContext(None, catalog))
    assert result.unresolved_requirements
    verified = find_product_candidates([requirement], [], MatchingContext(None, catalog, catalog.check_restrictions))
    assert not verified.unresolved_requirements


@pytest.mark.parametrize("restriction", sorted(DemoCatalog.SUPPORTED_RESTRICTIONS))
def test_every_demo_restriction_has_explicitly_verified_products(restriction):
    requirement = ingredient().model_copy(update={"restrictions": [restriction]})
    catalog = DemoCatalog()

    result = find_product_candidates(
        [requirement], [], MatchingContext(None, catalog, catalog.check_restrictions)
    )

    assert result.unresolved_requirements == []
    assert any(
        candidate.available and candidate.restriction_check == "pass"
        for candidate in result.candidates
    )


def test_unrestricted_live_candidate_does_not_require_dietary_evidence():
    catalog = DemoCatalog()
    catalog.products["demo-oats"].restriction_check = "unknown"
    catalog.terms = {"oats": ["demo-oats"]}

    result = find_product_candidates([ingredient()], [], MatchingContext(None, catalog))

    assert result.unresolved_requirements == []
    assert result.candidates[0].restriction_check == "pass"


@pytest.mark.parametrize(
    "category",
    [alias for _key, _name, _size, _price, aliases in CATEGORY_PRODUCTS for alias in aliases],
)
def test_every_edamam_food_category_resolves_to_a_demo_product(category):
    # Real ingredient names never appear in the demo catalog (chicken, red potatoes, ...); the
    # category alone — Edamam's bounded foodCategory taxonomy — is what has to carry the match.
    requirement = edamam_ingredient("live-1", "some ingredient not in any demo list", category)
    catalog = DemoCatalog()

    result = find_product_candidates([requirement], [], MatchingContext(None, catalog))

    assert result.unresolved_requirements == [], f"category {category!r} did not resolve"
    assert result.candidates[0].source == "synthetic"


def test_edamam_category_match_is_case_insensitive():
    # Edamam's own data is inconsistently cased for the same category (observed live).
    requirement = edamam_ingredient("live-1", "salt", "Condiments and Sauces")
    catalog = DemoCatalog()

    result = find_product_candidates([requirement], [], MatchingContext(None, catalog))

    assert result.unresolved_requirements == []


def test_edamam_category_product_needs_restriction_evidence_to_be_selected():
    # No composition data exists for a generic placeholder, so — unlike oats/rice/lentils — a
    # requested restriction must still fail closed rather than silently passing.
    requirement = edamam_ingredient("live-1", "chicken", "Poultry").model_copy(
        update={"restrictions": ["peanut-free"]}
    )
    catalog = DemoCatalog()

    unchecked = find_product_candidates([requirement], [], MatchingContext(None, catalog))
    assert unchecked.unresolved_requirements

    verified = find_product_candidates(
        [requirement], [], MatchingContext(None, catalog, catalog.check_restrictions)
    )
    assert verified.unresolved_requirements
    assert "lacked provider evidence" in verified.unresolved_requirements[0].reason


def test_a_realistic_live_edamam_ingredient_set_mostly_resolves():
    # The exact mix observed live (run 20): 8 of 9 ingredients carry a category the demo
    # catalog now covers; "Tst" (an Edamam data artifact) has neither a usable name nor category.
    ingredients = [
        edamam_ingredient("i1", "chicken", "Poultry"),
        edamam_ingredient("i2", "red potatoes", "vegetables"),
        edamam_ingredient("i3", "extra virgin olive oil", "Oils"),
        edamam_ingredient("i4", "salt", "Condiments and sauces"),
        edamam_ingredient("i5", "parmesan cheese", "Cheese"),
        edamam_ingredient("i6", "eggs", "Eggs"),
        edamam_ingredient("i7", "all purpose flour", "grains"),
        edamam_ingredient("i8", "white wine", "wines"),
        edamam_ingredient("i9", "an untagged mystery ingredient", None),
    ]
    catalog = DemoCatalog()

    result = find_product_candidates(ingredients, [], MatchingContext(None, catalog))

    resolved = {i.id for i in ingredients} - {u.requirement_id for u in result.unresolved_requirements}
    assert len(resolved) == 8
    assert {u.requirement_id for u in result.unresolved_requirements} == {"i9"}


def test_unresolved_reason_distinguishes_dietary_evidence_from_package_data():
    requirement = ingredient().model_copy(update={"restrictions": ["fish-free"]})
    catalog = DemoCatalog()
    unknown = find_product_candidates([requirement], [], MatchingContext(None, catalog))
    assert "lacked provider evidence" in unknown.unresolved_requirements[0].reason

    missing_size = catalog.products["demo-oats"].model_copy(update={
        "content_quantity": None,
        "content_unit": None,
    })
    catalog.products = {"demo-oats": missing_size}
    catalog.terms = {"oats": ["demo-oats"]}
    unresolved = find_product_candidates(
        [ingredient()], [], MatchingContext(None, catalog, catalog.check_restrictions)
    )
    assert "package contents" in unresolved.unresolved_requirements[0].reason
