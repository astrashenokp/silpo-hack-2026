"""Session-aware catalog facade for demo and authenticated Silpo planning."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import anyio

from smart_basket.demo import DemoCatalog
from smart_basket.mcp.adapters import (
    get_product_details as get_silpo_product_details,
    get_purchase_history,
    get_user_context,
    product_content_amount,
    product_write_metadata,
    search_products,
)
from smart_basket.mcp.connection import SessionTokenStorage, get_mcp_session
from smart_basket.schemas import ProductCandidate


T = TypeVar("T")
logger = logging.getLogger(__name__)


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
    """Use live Silpo reads for connected sessions and preserve the demo fallback."""

    def __init__(self, demo: DemoCatalog | None = None):
        self.demo = demo or DemoCatalog()
        self._candidates: dict[tuple[str, str], ProductCandidate] = {}
        self._details: dict[tuple[str, str], Any] = {}
        self._reported_unknown_details: set[tuple[str, str]] = set()

    QUERY_ALIASES = {
        "oats": ("вівсяні пластівці", "вівсянка", "oats"),
        "rice": ("крупа рисова", "рис", "rice"),
        "lentils": ("сочевиця", "чечевиця", "lentils"),
    }

    @property
    def products(self):
        """Compatibility for demo tests and deliberate fixture mutation drills."""
        return self.demo.products

    @staticmethod
    def _live(owner: Any) -> bool:
        return bool(getattr(owner, "silpo_connected", False))

    async def _context(self, owner):
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            return await get_user_context(mcp_session, owner)

    def get_user_context(self, owner):
        if not self._live(owner):
            return self.demo.get_user_context(owner)
        return _run_async(lambda: self._context(owner))

    async def _history(self, owner):
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            return await get_purchase_history(
                mcp_session,
                branch_id=owner.silpo_branch_id,
                delivery_type=owner.silpo_delivery_type,
                timeslot=owner.silpo_timeslot,
                tool_schemas=owner.silpo_tool_schemas,
            )

    def get_purchase_history(self, owner):
        if not self._live(owner):
            return self.demo.get_purchase_history(owner)
        return _run_async(lambda: self._history(owner))

    async def _search(self, owner, query: str):
        if not owner.silpo_branch_id:
            # A connected profile may legitimately have no active cart/branch yet. The app is
            # still a labelled demo, so keep planning usable with transparent synthetic items.
            return self.demo.search_products(owner, query)
        found: dict[str, ProductCandidate] = {}
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            for provider_query in self.QUERY_ALIASES.get(query.casefold(), (query,)):
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
                for candidate in result.products[:2]:
                    found.setdefault(candidate.id, candidate)
            reviewed = list(found.values())[:6]
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
        if not enriched:
            return self.demo.search_products(owner, query)

        candidates = []
        for candidate in enriched:
            normalized = candidate.model_copy(update={"restriction_check": "unknown"})
            self._candidates[(owner.id, normalized.id)] = normalized.model_copy(deep=True)
            candidates.append(normalized)
        return candidates

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
