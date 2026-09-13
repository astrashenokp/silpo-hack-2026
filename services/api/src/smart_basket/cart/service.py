"""Reviewed demo and live Silpo cart operations."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from smart_basket.catalog.matching import line_total
from smart_basket.core import ApiError, DEMO_WARNING, expires, require_fresh, uid
from smart_basket.mcp.adapters import (
    add_or_update_cart_products,
    get_current_cart,
    get_product_details,
    get_user_context,
    normalize_product_search,
    search_products,
    uah_to_minor,
)
from smart_basket.mcp.connection import SessionTokenStorage, get_mcp_session
from smart_basket.schemas import CartChange, CartItemOutcome, CartPreview, CartReceipt


logger = logging.getLogger(__name__)


def cart_total(session):
    return sum(line_total(quantity, price) for quantity, price in session.cart.values())


class DemoCartService:
    def __init__(self, catalog):
        self.catalog = catalog

    def _check_products(self, plan, session):
        if plan.data_mode != "demo" or any(p.source != "synthetic" for p in plan.selected_products):
            raise ApiError("DEMO_ONLY", "This service accepts only synthetic plans.")
        if not plan.can_confirm_cart or plan.budget_status != "within_budget" or not plan.selected_products:
            raise ApiError("STALE_PLAN", "A complete proposal within budget is required.")
        for selected in plan.selected_products:
            try:
                current = self.catalog.get_product_details(session, selected.product_id)
            except KeyError:
                raise ApiError("STALE_PLAN", "A selected product no longer exists.") from None
            if (not current.available or current.restriction_check != "pass"
                    or current.price_minor != selected.unit_price_minor):
                raise ApiError("STALE_PLAN", "Product price, availability or composition changed; recalculate.")

    def preview_cart(self, run_id, version, session, scenario="success"):
        with session.lock:
            plan = session.get_plan(run_id, version)
            if run_id in session.cart_applied_runs:
                raise ApiError("STALE_PLAN", "This proposal already has a cart receipt; review that outcome.")
            self._check_products(plan, session)
            changes = [CartChange(product_id=p.product_id, name=p.name,
                before_quantity=session.cart.get(p.product_id, (0.0, 0))[0],
                after_quantity=session.cart.get(p.product_id, (0.0, 0))[0] + p.quantity,
                unit_price_minor=p.unit_price_minor) for p in plan.selected_products]
            existing = cart_total(session)
            preview = CartPreview(preview_id=uid("cart-preview"), run_id=run_id, version=version,
                expires_at=expires(), existing_cart_total_minor=existing,
                added_goods_total_minor=plan.basket_total_minor,
                projected_goods_total_minor=existing+plan.basket_total_minor,
                changes=changes, warnings=[DEMO_WARNING, f"Simulated confirmation outcome: {scenario}."])
            session.cart_previews[preview.preview_id] = (preview, dict(session.cart), scenario)
            return preview

    def confirm_cart(self, preview_id, idempotency_key, session):
        with session.lock:
            if preview_id not in session.cart_previews:
                raise ApiError("NOT_FOUND", "Cart preview not found in this session.", 404)
            prior = session.cart_keys.get(idempotency_key)
            if prior is not None and prior != preview_id:
                raise ApiError("IDEMPOTENCY_CONFLICT", "This key belongs to another cart preview.")
            if preview_id in session.cart_receipts:
                session.cart_keys[idempotency_key] = preview_id
                return session.cart_receipts[preview_id]
            preview, snapshot, scenario = session.cart_previews[preview_id]
            require_fresh(preview)
            plan = session.get_plan(preview.run_id, preview.version)
            if preview.run_id in session.cart_applied_runs:
                raise ApiError("STALE_PLAN", "This proposal already has a receipt.")
            self._check_products(plan, session)
            if snapshot != session.cart:
                raise ApiError("STALE_PLAN", "Existing cart changed. Review a new preview.")
            items = []
            for index, change in enumerate(preview.changes):
                success = scenario == "success" or (scenario == "partial" and index == 0)
                if success:
                    session.cart[change.product_id] = (change.after_quantity, change.unit_price_minor)
                actual = session.cart.get(change.product_id, (0.0, 0))[0]
                items.append(CartItemOutcome(product_id=change.product_id,
                    status="success" if success else "failed",
                    requested_quantity=change.after_quantity, actual_quantity=actual,
                    message="Demo quantity read back." if success else "Simulated provider failure; no addition."))
            successes = sum(item.status == "success" for item in items)
            receipt = CartReceipt(preview_id=preview_id,
                status="success" if successes == len(items) else "partial" if successes else "failed",
                items=items, verified_cart_total_minor=cart_total(session), warnings=[DEMO_WARNING])
            session.cart_keys[idempotency_key] = preview_id
            session.cart_receipts[preview_id] = receipt
            session.cart_applied_runs.add(preview.run_id)
            return receipt


@dataclass
class LiveCartPreviewRecord:
    preview: CartPreview
    snapshot: dict[str, tuple[float, int | None]]
    write_products: list[dict[str, Any]]


def normalize_cart_snapshot(payload: Any) -> dict[str, tuple[float, int | None]]:
    """Extract product quantities and unit prices without exposing the raw cart."""
    snapshot: dict[str, tuple[float, int | None]] = {}

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            product_id = value.get("productId")
            quantity = next(
                (value.get(key) for key in ("quantity", "count") if value.get(key) is not None),
                None,
            )
            price_minor = next(
                (value.get(key) for key in (
                    "unitPriceMinor", "priceMinor", "currentPriceMinor",
                ) if value.get(key) is not None),
                None,
            )
            if price_minor is None:
                price = next(
                    (value.get(key) for key in (
                        "unitPrice", "currentPrice", "price",
                    ) if value.get(key) is not None),
                    None,
                )
                if price is not None:
                    try:
                        price_minor = uah_to_minor(price)
                    except ValueError:
                        price_minor = None
            try:
                parsed_quantity = float(Decimal(str(quantity)))
                parsed_price = int(price_minor) if price_minor is not None else None
            except (InvalidOperation, TypeError, ValueError):
                parsed_quantity = -1
                parsed_price = None
            if product_id is not None and parsed_quantity >= 0:
                snapshot[str(product_id)] = (parsed_quantity, parsed_price)
                return
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(payload)
    return snapshot


def snapshot_total(snapshot: dict[str, tuple[float, int | None]]) -> int:
    return sum(
        line_total(quantity, price)
        for quantity, price in snapshot.values()
        if price is not None
    )


class LiveCartService:
    """Use the authenticated MCP gateway only after a reviewed, fresh preview."""

    async def preview_cart(self, run_id: str, version: int, owner) -> CartPreview:
        with owner.lock:
            plan = owner.get_plan(run_id, version).model_copy(deep=True)
            if run_id in owner.live_cart_applied_runs:
                raise ApiError("STALE_PLAN", "This proposal already has a live cart receipt.")
            connected = owner.silpo_connected
            cart_id = owner.silpo_cart_id
            branch_id = owner.silpo_branch_id
            delivery_type = owner.silpo_delivery_type
            timeslot = owner.silpo_timeslot
            schemas = dict(owner.silpo_tool_schemas)
            metadata = dict(owner.silpo_product_write_metadata)
        if not connected:
            raise ApiError("AUTH_REQUIRED", "Connect the Silpo account before cart preview.", 401)

        try:
            async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
                # A transient cart read during OAuth used to leave this session permanently
                # incomplete. Refresh once at the action boundary, where current cart context is
                # required anyway, so reconnecting the whole Silpo account is unnecessary.
                if not cart_id or not branch_id:
                    await get_user_context(mcp_session, owner)
                    with owner.lock:
                        cart_id = owner.silpo_cart_id
                        branch_id = owner.silpo_branch_id
                        delivery_type = owner.silpo_delivery_type
                        timeslot = owner.silpo_timeslot
                        schemas = dict(owner.silpo_tool_schemas)
                        metadata = dict(owner.silpo_product_write_metadata)
                if not cart_id or not branch_id:
                    raise ApiError(
                        "CART_CONTEXT_REQUIRED",
                        "Load a complete Silpo cart context first.",
                    )
                if (
                    not plan.selected_products
                    or plan.budget_status != "within_budget"
                    or plan.unresolved_requirements
                    or any(item.source != "silpo" for item in plan.selected_products)
                ):
                    raise ApiError(
                        "STALE_PLAN",
                        "A complete reviewed live Silpo proposal is required.",
                    )

                raw_cart = await get_current_cart(mcp_session)
                snapshot = normalize_cart_snapshot(raw_cart)
                changes: list[CartChange] = []
                write_products: list[dict[str, Any]] = []
                for selected in plan.selected_products:
                    coordinates = metadata.get(selected.product_id)
                    current = None
                    if coordinates and coordinates.get("companyId"):
                        try:
                            raw_details = await get_product_details(
                                mcp_session,
                                selected.product_id,
                                branch_id,
                                slug=coordinates.get("slug"),
                                cart_id=cart_id,
                                delivery_type=delivery_type,
                                timeslot=timeslot,
                                input_schema=schemas.get("silpo_get_product_details"),
                            )
                            details = normalize_product_search(
                                raw_details, selected.name
                            ).products
                            current = next(
                                (
                                    item for item in details
                                    if item.id == selected.product_id
                                ),
                                None,
                            )
                        except Exception as exc:
                            logger.warning(
                                "Silpo product detail revalidation failed for %s; "
                                "refreshing it through catalog search (%s).",
                                selected.product_id,
                                type(exc).__name__,
                            )

                    # Product-detail payloads can omit catalog fields needed by the normalizer,
                    # and provider write coordinates may expire. The live search endpoint is the
                    # canonical source for both, so recover them before declaring the plan stale.
                    if current is None:
                        refreshed = await search_products(
                            mcp_session,
                            selected.name,
                            branch_id,
                            cart_id=cart_id,
                            delivery_type=delivery_type,
                            timeslot=timeslot,
                            tool_schemas=schemas,
                            owner=owner,
                        )
                        current = next(
                            (
                                item for item in refreshed.products
                                if item.id == selected.product_id
                            ),
                            None,
                        )
                        with owner.lock:
                            coordinates = dict(
                                owner.silpo_product_write_metadata.get(
                                    selected.product_id, {}
                                )
                            )
                        metadata[selected.product_id] = coordinates
                    if not coordinates or not coordinates.get("companyId"):
                        raise ApiError(
                            "STALE_PLAN",
                            f"Provider write coordinates expired for {selected.name}; search again.",
                        )
                    if (
                        current is None or not current.available
                        or current.price_minor != selected.unit_price_minor
                    ):
                        raise ApiError(
                            "STALE_PLAN",
                            f"Price or availability changed for {selected.name}; recalculate.",
                        )
                    before = snapshot.get(selected.product_id, (0.0, 0))[0]
                    after = before + selected.quantity
                    changes.append(CartChange(
                        product_id=selected.product_id,
                        name=selected.name,
                        before_quantity=before,
                        after_quantity=after,
                        unit_price_minor=current.price_minor,
                    ))
                    write_products.append({
                        **coordinates,
                        "quantity": after,
                    })
        except ApiError:
            raise
        except Exception as exc:
            self._provider_error(owner, exc, "Could not prepare the Silpo cart preview.")

        existing = snapshot_total(snapshot)
        added = sum(
            line_total(change.after_quantity - change.before_quantity, change.unit_price_minor)
            for change in changes
        )
        warnings = [
            "LIVE: confirmation will update the connected Silpo cart.",
            "Existing unrelated cart items are preserved.",
        ]
        if any(price is None for _, price in snapshot.values()):
            warnings.append(
                "Silpo omitted a unit price for one or more existing lines; displayed cart totals exclude those lines."
            )
        preview = CartPreview(
            preview_id=uid("live-cart-preview"),
            run_id=run_id,
            version=version,
            expires_at=expires(),
            existing_cart_total_minor=existing,
            added_goods_total_minor=added,
            projected_goods_total_minor=existing + added,
            changes=changes,
            warnings=warnings,
        )
        with owner.lock:
            owner.live_cart_previews[preview.preview_id] = LiveCartPreviewRecord(
                preview=preview, snapshot=snapshot, write_products=write_products
            )
        return preview

    async def confirm_cart(self, preview_id: str, idempotency_key: str, owner) -> CartReceipt:
        with owner.lock:
            record = owner.live_cart_previews.get(preview_id)
            if record is None:
                raise ApiError("NOT_FOUND", "Live cart preview not found in this session.", 404)
            prior = owner.live_cart_keys.get(idempotency_key)
            if prior is not None and prior != preview_id:
                raise ApiError("IDEMPOTENCY_CONFLICT", "This key belongs to another cart preview.")
            receipt = owner.live_cart_receipts.get(preview_id)
            if receipt is not None:
                owner.live_cart_keys[idempotency_key] = preview_id
                return receipt
            if preview_id in owner.live_cart_inflight:
                raise ApiError(
                    "CONFIRMATION_IN_PROGRESS",
                    "This cart preview is already being confirmed.",
                    409,
                    True,
                )
            require_fresh(record.preview)
            owner.get_plan(record.preview.run_id, record.preview.version)
            if record.preview.run_id in owner.live_cart_applied_runs:
                raise ApiError("STALE_PLAN", "This proposal already has a live cart receipt.")
            cart_id = owner.silpo_cart_id
            delivery_type = owner.silpo_delivery_type
            timeslot = owner.silpo_timeslot
            schemas = dict(owner.silpo_tool_schemas)
            owner.live_cart_keys[idempotency_key] = preview_id
            owner.live_cart_inflight.add(preview_id)
        if not owner.silpo_connected:
            raise ApiError("AUTH_REQUIRED", "Reconnect the Silpo account.", 401)
        if not cart_id:
            raise ApiError("CART_CONTEXT_REQUIRED", "Silpo cart context is unavailable.")

        write_error: Exception | None = None
        try:
            try:
                async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
                    before = normalize_cart_snapshot(await get_current_cart(mcp_session))
                    if before != record.snapshot:
                        raise ApiError("STALE_PLAN", "Existing Silpo cart changed; review a new preview.")
                    try:
                        await add_or_update_cart_products(
                            mcp_session,
                            record.write_products,
                            cart_id=cart_id,
                            delivery_type=delivery_type,
                            timeslot=timeslot,
                            tool_schemas=schemas,
                        )
                    except Exception as exc:
                        write_error = exc
                    verified = normalize_cart_snapshot(await get_current_cart(mcp_session))
            except ApiError:
                raise
            except Exception as exc:
                self._provider_error(owner, exc, "Could not verify the Silpo cart mutation.")
        finally:
            with owner.lock:
                owner.live_cart_inflight.discard(preview_id)

        outcomes = []
        for change in record.preview.changes:
            actual = verified.get(change.product_id, (0.0, 0))[0]
            saved = actual >= change.after_quantity
            outcomes.append(CartItemOutcome(
                product_id=change.product_id,
                status="success" if saved else "failed",
                requested_quantity=change.after_quantity,
                actual_quantity=actual,
                message=(
                    "Silpo quantity was read back successfully."
                    if saved else "Requested Silpo quantity was not visible during read-back."
                ),
            ))
        successes = sum(item.status == "success" for item in outcomes)
        status = (
            "success" if successes == len(outcomes)
            else "partial" if successes else "failed"
        )
        warnings = ["LIVE: result verified by reading the connected Silpo cart."]
        if any(price is None for _, price in verified.values()):
            warnings.append(
                "Silpo omitted a unit price for one or more lines; the verified total excludes those lines."
            )
        if write_error is not None:
            warnings.append(
                "The write response was uncertain; the reported result comes from cart read-back."
            )
        receipt = CartReceipt(
            preview_id=preview_id,
            status=status,
            items=outcomes,
            verified_cart_total_minor=snapshot_total(verified),
            warnings=warnings,
        )
        with owner.lock:
            owner.live_cart_receipts[preview_id] = receipt
            if status != "failed":
                owner.live_cart_applied_runs.add(record.preview.run_id)
        return receipt

    @staticmethod
    def _provider_error(owner, exc: Exception, fallback: str):
        message = str(exc).lower()
        if any(value in message for value in ("401", "403", "unauthorized", "invalid_token")):
            with owner.lock:
                owner.silpo_connected = False
            raise ApiError("AUTH_REQUIRED", "Reconnect the Silpo account.", 401) from exc
        if "429" in message or "rate limit" in message:
            raise ApiError("RATE_LIMITED", "Silpo request limit was reached.", 429, True) from exc
        raise ApiError("UPSTREAM_UNAVAILABLE", fallback, 502, True) from exc
