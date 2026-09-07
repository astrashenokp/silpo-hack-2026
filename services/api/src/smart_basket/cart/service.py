"""Isolated demo cart operations. A live gateway must be integrated separately."""

from smart_basket.catalog.matching import line_total
from smart_basket.core import ApiError, DEMO_WARNING, expires, require_fresh, uid
from smart_basket.schemas import CartChange, CartItemOutcome, CartPreview, CartReceipt


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
