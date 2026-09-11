"""Session-aware catalog facade for demo and authenticated Silpo planning."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import anyio

from smart_basket.demo import DemoCatalog
from smart_basket.mcp.adapters import get_purchase_history, get_user_context, search_products
from smart_basket.mcp.connection import SessionTokenStorage, get_mcp_session
from smart_basket.schemas import ProductCandidate


T = TypeVar("T")


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
            return []
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
                for candidate in result.products:
                    found.setdefault(candidate.id, candidate)
        candidates = []
        for candidate in found.values():
            normalized = candidate.model_copy(update={"restriction_check": "pass"})
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
        # The normalized Silpo payload currently has no composition evidence.
        return "unknown"
