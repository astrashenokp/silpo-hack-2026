"""Session-aware catalog facade for demo and authenticated Silpo planning."""

from __future__ import annotations

import asyncio
import logging
import re
from copy import deepcopy
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import anyio

from smart_basket.demo import DemoCatalog
from smart_basket.mcp.adapters import (
    get_product_details as get_silpo_product_details,
    get_purchase_history,
    get_user_context,
    normalize_purchase_history,
    product_content_amount,
    product_write_metadata,
    search_products,
)
from smart_basket.mcp.connection import SessionTokenStorage, get_mcp_session
from smart_basket.schemas import ProductCandidate

from .translation import GeminiIngredientTranslator


T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiveQueryProfile:
    """A bounded translation plus evidence rule for Silpo's Ukrainian catalog."""

    match_terms: tuple[str, ...]
    provider_queries: tuple[str, ...]
    required_name_terms: tuple[str, ...]
    forbidden_name_terms: tuple[str, ...] = ()
    grams_per_ml: float | None = None
    grams_per_piece: float | None = None
    require_all_name_terms: bool = False


def _normalized_words(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).split())


QUERY_PREPARATION_WORDS = {
    "fresh", "dry", "dried", "raw", "cooked", "boiled", "steamed", "baked",
    "ground", "chopped", "sliced", "diced", "minced", "frozen", "canned",
    "boneless", "skinless", "large", "medium", "small",
}

# These words usually mean that the matching ingredient is only a flavour or a component of a
# different grocery product. They are allowed only when the requested profile itself names that
# product form. This is a general guard against lemon marmalade, tomato beer, milk sweets, etc.
MISLEADING_PRODUCT_TERMS = (
    "зі смаком", "смаком", "ароматом", "мармелад", "цукер", "льодяник", "жуйк",
    "чипс", "снек", "печиво", "шоколад", "батончик", "морозиво", "десерт",
    "напій", "пиво", "чай", "кава", "йогурт", "соус", "кетчуп", "приправа",
    "вермішел", "локшин", "корм", "космет",
)


# Specific phrases come before broader ingredients. A live hit is accepted only when its display
# name contains Ukrainian evidence for the ingredient; fuzzy result position alone is not proof.
LIVE_QUERY_PROFILES = (
    LiveQueryProfile(("sun dried tomato", "sundried tomato"), ("в'ялені помідори", "томати в'ялені"), ("в ялен", "сушен", "помідор", "томат"), ("пиво",)),
    LiveQueryProfile(("extra virgin olive oil", "olive oil"), ("олія оливкова", "оливкова олія"), ("оливков",), ("космет", "мило"), 0.91),
    LiveQueryProfile(("all purpose flour", "all-purpose flour", "wheat flour", "flour"), ("борошно пшеничне", "борошно"), ("борошн",), ("джин", "gin", "пиво", "цукер")),
    LiveQueryProfile(("parmesan cheese", "parmesan"), ("сир пармезан", "пармезан"), ("пармезан",)),
    LiveQueryProfile(("arborio rice", "risotto rice"), ("рис арборіо", "рис для різото"), ("арбор", "різото"), ("чипс", "снек")),
    LiveQueryProfile(("red potato", "red potatoes", "potato", "potatoes"), ("картопля",), ("картоп",), ("чипс", "снек"), None, 180.0),
    # Broth type is essential evidence: Silpo's fuzzy search can otherwise return chicken-flavour
    # instant noodles for fish broth merely because both product names contain "бульйон".
    LiveQueryProfile(("fish broth", "fish stock"), ("рибний бульйон", "бульйон рибний"), ("рибн", "риб'яч", "риб’яч"), ("куряч", "ялович", "говяж", "овоч", "смаком", "вермішел", "локшин", "мівіна", "корм"), 1.0),
    LiveQueryProfile(("chicken broth", "chicken stock"), ("курячий бульйон", "бульйон курячий"), ("куряч", "курк"), ("рибн", "риб'яч", "риб’яч", "ялович", "говяж", "овоч", "смаком", "вермішел", "локшин", "мівіна", "корм"), 1.0),
    LiveQueryProfile(("vegetable broth", "vegetable stock"), ("овочевий бульйон", "бульйон овочевий"), ("овоч",), ("рибн", "риб'яч", "риб’яч", "куряч", "ялович", "говяж", "смаком", "вермішел", "локшин", "мівіна", "корм"), 1.0),
    LiveQueryProfile(("beef broth", "beef stock"), ("яловичий бульйон", "бульйон яловичий"), ("ялович", "говяж"), ("рибн", "риб'яч", "риб’яч", "куряч", "овоч", "смаком", "вермішел", "локшин", "мівіна", "корм"), 1.0),
    LiveQueryProfile(("broth", "stock"), ("бульйон",), ("бульйон",), ("смаком", "вермішел", "локшин", "мівіна", "корм"), 1.0),
    LiveQueryProfile(("heavy cream", "double cream", "cream"), ("вершки",), ("вершк",), ("крем для", "космет"), 1.0),
    LiveQueryProfile(("butter",), ("масло вершкове",), ("масло",), ("олія", "космет", "арахіс")),
    LiveQueryProfile(("chicken",), ("куряче філе", "курка"), ("кур",), ("корм", "приправа", "смаком")),
    LiveQueryProfile(("tomato", "tomatoes"), ("помідор", "томат"), ("помідор", "томат"), ("пиво", "сік", "соус", "кетчуп"), None, 150.0),
    LiveQueryProfile(("onion", "onions"), ("цибуля",), ("цибул",), ("приправа", "чипс", "смаком"), None, 150.0),
    LiveQueryProfile(("garlic",), ("часник",), ("часник",), ("приправа", "соус", "смаком"), None, 60.0),
    LiveQueryProfile(("milk",), ("молоко",), ("молок",), ("цукер", "шоколад", "соломин", "коктейль"), 1.03),
    LiveQueryProfile(("salt",), ("сіль кухонна", "сіль"), ("сіль",), ("льодяник", "цукер", "карамел", "ваніл")),
    LiveQueryProfile(("egg", "eggs"), ("яйця курячі", "яйця"), ("яйц",), ("цукер", "шоколад"), None, 50.0),
    LiveQueryProfile(("honey",), ("мед натуральний", "мед"), ("мед",), ("напій", "пиво")),
    LiveQueryProfile(("yeast",), ("дріжджі",), ("дріждж",)),
    LiveQueryProfile(("sugar",), ("цукор",), ("цукор",), ("цукер", "напій")),
    LiveQueryProfile(("oat", "oats"), ("вівсяні пластівці", "вівсянка"), ("вівсян",), ("печиво", "батончик")),
    LiveQueryProfile(("lentil", "lentils"), ("сочевиця", "чечевиця"), ("сочев", "чечев"), ("суп", "снек")),
    LiveQueryProfile(("rice",), ("крупа рисова", "рис"), ("рис",), ("чипс", "снек", "пудинг", "ірис", "хлібц")),
    LiveQueryProfile(("basil",), ("базилік свіжий", "базилік"), ("базилік",), ("соус", "приправа")),
    LiveQueryProfile(("carrot",), ("морква",), ("моркв",), ("сік", "пюре"), None, 100.0),
    LiveQueryProfile(("lemon",), ("лимон",), ("лимон",), ("напій", "пиво", "цукер"), None, 120.0),
    LiveQueryProfile(("black pepper", "pepper"), ("перець чорний", "перець"), ("перець",), ("чипс", "соус")),
    LiveQueryProfile(("paprika",), ("паприка",), ("паприк",), ("чипс", "соус")),
    LiveQueryProfile(("white wine", "red wine", "wine"), ("вино",), ("вино",), ("оцет",), 0.99),
    LiveQueryProfile(("vegetable oil", "sunflower oil", "canola oil", "cooking oil", "oil"), ("олія соняшникова", "олія"), ("олія",), ("космет", "мило", "оливков"), 0.92),
    LiveQueryProfile(("water",), ("вода питна", "вода"), ("вода",), ("аромат", "солодка"), 1.0),
    LiveQueryProfile(("yogurt", "yoghurt"), ("йогурт натуральний", "йогурт"), ("йогурт",), ("десерт",), 1.03),
    LiveQueryProfile(("cheese",), ("сир твердий", "сир"), ("сир",), ("сироп", "десерт")),
    LiveQueryProfile(("pasta", "spaghetti", "noodle", "noodles"), ("макарони", "спагеті"), ("макарон", "спагеті"), ("снек",)),
    LiveQueryProfile(("bread", "bun", "buns", "roll", "rolls"), ("хліб", "булочка"), ("хліб", "булоч"), ("сухар", "чипс")),
)


EDAMAM_CATEGORY_TERMS = {
    "vegetables", "canned vegetables", "condiments and sauces", "grains",
    "cooked grains", "bread rolls and tortillas", "quick breads and pastries",
    "fruit", "canned fruit", "sugars", "sugar syrups", "dairy", "cheese", "oils",
    "eggs", "poultry", "meats", "cured meats", "seafood", "plant based protein",
    "vegan products", "canned soup", "non dairy beverages", "100 juice", "wines",
    "chocolate", "water",
}


def live_query_profile(query: str) -> LiveQueryProfile | None:
    def semantic_key(value: str) -> tuple[str, ...]:
        return tuple(
            word for word in _normalized_words(value).split()
            if word not in QUERY_PREPARATION_WORDS
        )

    query_key = semantic_key(query)
    matches: list[tuple[int, LiveQueryProfile]] = []
    for profile in LIVE_QUERY_PROFILES:
        specificity = max(
            (len(_normalized_words(term).split()) for term in profile.match_terms
             if semantic_key(term) == query_key),
            default=0,
        )
        if specificity:
            matches.append((specificity, profile))
    return max(matches, key=lambda item: item[0])[1] if matches else None


def live_product_name_matches(
    query: str,
    product_name: str,
    profile: LiveQueryProfile | None = None,
) -> bool:
    """Require lexical evidence instead of trusting fuzzy provider result position."""
    profile = profile or live_query_profile(query)
    normalized_name = _normalized_words(product_name)
    if profile is not None:
        required = tuple(_normalized_words(term) for term in profile.required_name_terms)
        forbidden = tuple(_normalized_words(term) for term in profile.forbidden_name_terms)
        profile_language = " ".join(_normalized_words(term) for term in (
            *profile.provider_queries, *profile.required_name_terms,
        ))
        misleading = tuple(_normalized_words(term) for term in MISLEADING_PRODUCT_TERMS)
        required_match = (
            all(term in normalized_name for term in required)
            if profile.require_all_name_terms
            else any(term in normalized_name for term in required)
        )
        return (
            required_match
            and not any(term in normalized_name for term in forbidden)
            and not any(
                term in normalized_name and term not in profile_language
                for term in misleading
            )
        )

    query_words = {
        word for word in _normalized_words(query).split()
        if len(word) >= 3 and word not in {"and", "with", "fresh", "dried", "ground"}
    }
    return bool(query_words) and any(word in normalized_name for word in query_words)


def ingredient_package_amount(
    profile: LiveQueryProfile | None,
    quantity: float | None,
    unit: str | None,
) -> tuple[float | None, str | None]:
    """Express liquid volume or piece counts as Edamam ingredient grams."""
    if (
        profile is not None
        and profile.grams_per_ml is not None
        and quantity is not None
        and unit == "ml"
    ):
        return quantity * profile.grams_per_ml, "g"
    if (
        profile is not None
        and profile.grams_per_piece is not None
        and quantity is not None
        and unit == "piece"
    ):
        return quantity * profile.grams_per_piece, "g"
    return quantity, unit


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in _flatten_strings(child)]
    if isinstance(value, list):
        return [text for child in value for text in _flatten_strings(child)]
    return []


def _named_values(payload: Any, names: set[str]) -> list[Any]:
    values: list[Any] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = key.replace("_", "").replace("-", "").casefold()
            if normalized in names:
                values.append(value)
            values.extend(_named_values(value, names))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_named_values(value, names))
    return values


def _attribute_values(payload: Any, names: set[str]) -> list[Any]:
    """Read values from provider attribute records such as {name: Склад, value: ...}."""
    values: list[Any] = []
    if isinstance(payload, dict):
        label = next((payload.get(key) for key in (
            "name", "title", "label", "key", "code",
            "propertyName", "attributeName", "displayName",
        ) if payload.get(key) is not None), None)
        normalized = (
            str(label).replace("_", "").replace("-", "").replace(" ", "").casefold()
            if label is not None else ""
        )
        if normalized in names:
            value = next((payload.get(key) for key in (
                "value", "values", "text", "content", "description",
                "propertyValue", "attributeValue",
            ) if payload.get(key) is not None), None)
            if value is not None:
                values.append(value)
        for child in payload.values():
            values.extend(_attribute_values(child, names))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_attribute_values(value, names))
    return values


def _field_paths(payload: Any, prefix: str = "", depth: int = 0) -> list[str]:
    """Return bounded provider field paths without logging any field values."""
    if depth > 5:
        return []
    paths: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.append(path)
            paths.extend(_field_paths(value, path, depth + 1))
    elif isinstance(payload, list) and payload:
        path = f"{prefix}[]" if prefix else "[]"
        paths.append(path)
        paths.extend(_field_paths(payload[0], path, depth + 1))
    return list(dict.fromkeys(paths))[:80]


def _package_signals(payload: Any) -> dict[str, Any]:
    """Extract non-sensitive catalog values relevant to unit conversion."""
    product = payload.get("product") if isinstance(payload, dict) else None
    if not isinstance(product, dict):
        return {}

    signals = {
        key: product.get(key)
        for key in ("weighted", "step", "ratio", "displayRatio")
        if product.get(key) is not None
    }
    attributes = product.get("attributes")
    if isinstance(attributes, dict):
        for key, value in attributes.items():
            normalized = str(key).replace(" ", "").casefold()
            if normalized in {"розмір/об'єм", "розмір/об’єм", "вага", "об'єм", "об’єм"}:
                signals[f"attributes.{key}"] = value
    return signals


def restriction_check_from_details(payload: Any, restrictions: list[str]) -> str:
    """Verify restrictions from explicit provider labels or a non-empty composition."""
    if not restrictions:
        return "pass"
    label_values = _named_values(
        payload,
        {"healthlabels", "dietarylabels", "dietlabels"},
    )
    labels = {
        label.strip().casefold().replace("_", "-").replace(" ", "-")
        for value in label_values
        for label in _flatten_strings(value)
        if label.strip()
    }
    composition_names = {
        "ingredients", "ingredientlist", "composition", "components",
        "productcomposition", "compositiontext", "ingredientstext",
        "ingredientsdescription", "склад", "складпродукту",
    }
    composition_values = _named_values(
        payload,
        composition_names,
    )
    composition_values.extend(_attribute_values(payload, composition_names))
    composition = " ".join(
        _flatten_strings(composition_values)
    ).casefold()
    forbidden = {
        "fish-free": (
            "fish", "tuna", "salmon", "anchov", "herring",
            "риб", "тун", "лосос", "анчоус", "оселед",
        ),
        "red-meat-free": (
            "beef", "veal", "pork", "lamb", "mutton", "duck", "goose",
            "ялович", "теляч", "свин", "баранин", "качк", "гуск",
        ),
    }
    checks: list[str] = []
    for restriction in restrictions:
        if restriction in labels:
            checks.append("pass")
        elif restriction in forbidden and composition:
            checks.append(
                "fail" if any(token in composition for token in forbidden[restriction]) else "pass"
            )
        else:
            checks.append("unknown")
    if "fail" in checks:
        return "fail"
    return "pass" if checks and all(check == "pass" for check in checks) else "unknown"


def _run_async(factory: Callable[[], Awaitable[T]]) -> T:
    """Bridge Uliana's synchronous planner from Starlette's worker thread."""
    try:
        return anyio.from_thread.run(factory)
    except RuntimeError as exc:
        if "AnyIO worker thread" not in str(exc):
            raise
        return asyncio.run(factory())


class SessionCatalog:
    """Use live Silpo reads for connected sessions and demo only for guests."""

    def __init__(self, demo: DemoCatalog | None = None, translator=None):
        self.demo = demo or DemoCatalog()
        self.translator = translator
        self._candidates: dict[tuple[str, str], ProductCandidate] = {}
        self._details: dict[tuple[str, str], Any] = {}
        self._dynamic_profiles: dict[tuple[str, str], LiveQueryProfile] = {}
        self._reported_unknown_details: set[tuple[str, str]] = set()

    @property
    def products(self):
        """Compatibility for demo tests and deliberate fixture mutation drills."""
        return self.demo.products

    @staticmethod
    def _live(owner: Any) -> bool:
        return bool(getattr(owner, "silpo_connected", False))

    def _profile(self, owner: Any, query: str) -> LiveQueryProfile | None:
        return self._dynamic_profiles.get(
            (owner.id, _normalized_words(query))
        ) or live_query_profile(query)

    def prepare_requirements(self, owner, requirements):
        """Translate every unknown live ingredient in one call before catalog lookup."""
        if not self._live(owner) or not owner.silpo_branch_id:
            return requirements

        unknown = [
            requirement for requirement in requirements
            if live_query_profile(requirement.name) is None
        ]
        translations = {}
        if unknown:
            try:
                if self.translator is None:
                    self.translator = GeminiIngredientTranslator()
                translations = self.translator.translate(unknown)
            except Exception as exc:
                logger.warning(
                    "Ingredient translation is unavailable; unknown ingredients will use "
                    "exact-language matching (%s).",
                    type(exc).__name__,
                )

        prepared = []
        for requirement in requirements:
            translation = translations.get(requirement.id)
            if translation is not None:
                profile = LiveQueryProfile(
                    match_terms=(requirement.name,),
                    provider_queries=tuple(dict.fromkeys(
                        query.strip() for query in translation.queries if query.strip()
                    )),
                    required_name_terms=tuple(dict.fromkeys(
                        term.strip() for term in translation.evidence_terms if term.strip()
                    )),
                    grams_per_ml=translation.grams_per_ml,
                    grams_per_piece=translation.grams_per_piece,
                    require_all_name_terms=True,
                )
                self._dynamic_profiles[(owner.id, _normalized_words(requirement.name))] = profile
            # requirement.name goes first so the dynamic/static profile above is what actually
            # drives the live search; the ingredient's own category terms (from Edamam, or the
            # demo-only bucket guesses in meals/edamam.py) are kept after it, not discarded, since
            # they are what lets _search() fall back to a labelled synthetic candidate when even a
            # correctly translated live search finds nothing Silpo carries.
            prepared.append(requirement.model_copy(update={
                "search_terms": list(dict.fromkeys([requirement.name, *requirement.search_terms])),
            }))

        logger.info(
            "Prepared %d live ingredient searches (%d dynamically translated).",
            len(prepared),
            len(translations),
        )
        return prepared

    async def _context(self, owner):
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            context = await get_user_context(mcp_session, owner)
        with owner.lock:
            owner.silpo_context = context.model_copy(deep=True)
        return context

    def get_user_context(self, owner):
        if not self._live(owner):
            return self.demo.get_user_context(owner)
        with owner.lock:
            cached = owner.silpo_context
        if cached is not None:
            return cached.model_copy(deep=True)
        return _run_async(lambda: self._context(owner))

    async def _history(self, owner):
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            history = await get_purchase_history(
                mcp_session,
                branch_id=owner.silpo_branch_id,
                delivery_type=owner.silpo_delivery_type,
                timeslot=owner.silpo_timeslot,
                tool_schemas=owner.silpo_tool_schemas,
            )
        with owner.lock:
            owner.silpo_purchase_history = deepcopy(history)
        return history

    def get_purchase_history(self, owner):
        if not self._live(owner):
            return self.demo.get_purchase_history(owner)
        with owner.lock:
            cached = deepcopy(owner.silpo_purchase_history)
        if cached is not None:
            return self._normalized_history(cached)
        try:
            return self._normalized_history(_run_async(lambda: self._history(owner)))
        except Exception as exc:
            logger.warning(
                "Silpo purchase history is temporarily unavailable; using empty history (%s).",
                type(exc).__name__,
            )
            return self.demo.get_purchase_history(owner)

    @staticmethod
    def _normalized_history(history):
        """Return only Vika-compatible purchase rows from the provider's order payload."""
        if not history:
            return []
        # get_user_context() caches raw Silpo orders because the same read also determines
        # historyAvailable. Vika's recurrence analyzer consumes flattened Purchase rows; passing
        # raw orders through used to fail the entire plan as soon as a real account had history.
        if all(
            isinstance(item, dict)
            and {"receiptId", "purchasedAt", "name", "category", "quantity", "unit"}
            <= item.keys()
            for item in history
        ):
            return deepcopy(history)
        return normalize_purchase_history(history).purchases

    async def _search_live(self, owner, query: str):
        found: dict[str, ProductCandidate] = {}
        profile = self._profile(owner, query)
        provider_queries = profile.provider_queries if profile is not None else (query,)
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            for provider_query in provider_queries:
                result = await search_products(
                    mcp_session,
                    provider_query,
                    owner.silpo_branch_id,
                    cart_id=owner.silpo_cart_id,
                    delivery_type=owner.silpo_delivery_type,
                    timeslot=owner.silpo_timeslot,
                    tool_schemas=owner.silpo_tool_schemas,
                    owner=owner,
                )
                for candidate in result.products[:10]:
                    if live_product_name_matches(query, candidate.name, profile):
                        found.setdefault(candidate.id, candidate)
            reviewed = list(found.values())[:30]
            enriched: list[ProductCandidate] = []
            for candidate in reviewed:
                with owner.lock:
                    coordinates = dict(
                        owner.silpo_product_write_metadata.get(candidate.id, {})
                    )
                details = await get_silpo_product_details(
                    mcp_session,
                    candidate.id,
                    owner.silpo_branch_id,
                    slug=coordinates.get("slug"),
                    cart_id=owner.silpo_cart_id,
                    delivery_type=owner.silpo_delivery_type,
                    timeslot=owner.silpo_timeslot,
                    input_schema=owner.silpo_tool_schemas.get(
                        "silpo_get_product_details"
                    ),
                )
                self._details[(owner.id, candidate.id)] = details
                content_quantity, content_unit = product_content_amount(
                    details, candidate.id
                )
                content_quantity, content_unit = ingredient_package_amount(
                    profile, content_quantity, content_unit
                )
                if content_quantity is not None:
                    candidate = candidate.model_copy(update={
                        "content_quantity": content_quantity,
                        "content_unit": content_unit,
                    })
                else:
                    logger.warning(
                        "Silpo product %s has no normalized package contents; "
                        "package signals: %s",
                        candidate.id,
                        _package_signals(details) or "none",
                    )
                enriched.append(candidate)
                metadata = product_write_metadata(details)
                if metadata:
                    with owner.lock:
                        for product_id, coordinates in metadata.items():
                            existing = owner.silpo_product_write_metadata.get(product_id, {})
                            owner.silpo_product_write_metadata[product_id] = {
                                **existing,
                                **coordinates,
                            }
        candidates = []
        for candidate in enriched:
            normalized = candidate.model_copy(update={"restriction_check": "unknown"})
            self._candidates[(owner.id, normalized.id)] = normalized.model_copy(deep=True)
            candidates.append(normalized)
        return candidates

    async def _search(self, owner, query: str):
        if not owner.silpo_branch_id:
            # A connected session must never receive synthetic product IDs: those cannot be
            # written to the user's real Silpo cart. Leave the requirement unresolved instead.
            return []
        if (
            _normalized_words(query) in EDAMAM_CATEGORY_TERMS
            and self._profile(owner, query) is None
        ):
            # A category such as "grains" is not evidence that an arbitrary result is flour.
            return []
        try:
            return await self._search_live(owner, query)
        except Exception as exc:
            logger.warning(
                "Silpo product search is temporarily unavailable for %s; "
                "leaving the ingredient unresolved (%s).",
                query,
                type(exc).__name__,
            )
            return []

    def search_products(self, owner, query: str):
        if not self._live(owner):
            return self.demo.search_products(owner, query)
        return _run_async(lambda: self._search(owner, query))

    def get_product_details(self, owner, product_id: str):
        if not self._live(owner):
            return self.demo.get_product_details(owner, product_id)
        candidate = self._candidates.get((owner.id, product_id))
        if candidate is None:
            raise KeyError(f"Silpo product {product_id} is not in the reviewed search results.")
        return candidate.model_copy(deep=True)

    def check_restrictions(self, product, restrictions):
        if not restrictions:
            return "pass"
        if product.source == "synthetic":
            return self.demo.check_restrictions(product, restrictions)
        owner_id, details = next(
            (
                (owner_id, payload)
                for (owner_id, product_id), payload in self._details.items()
                if product_id == product.id
            ),
            ("unknown", None),
        )
        result = restriction_check_from_details(details, restrictions)
        detail_key = (owner_id, product.id)
        if result == "unknown" and detail_key not in self._reported_unknown_details:
            self._reported_unknown_details.add(detail_key)
            fields = ", ".join(_field_paths(details)) or "none"
            logger.warning(
                "Silpo product details for %s contain no recognized dietary evidence; "
                "available field paths: %s",
                product.id,
                fields,
            )
        return result
