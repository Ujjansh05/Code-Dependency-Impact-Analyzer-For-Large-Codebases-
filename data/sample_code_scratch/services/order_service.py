"""Order service orchestrates pricing, persistence, and notifications."""

from repositories.order_repo import save_order
from services.notification_service import send_receipt_email
from utils.audit import record_event
from utils.pricing import add_tax, apply_campaign_discount, calculate_subtotal


def checkout_order(user: dict, items: list[dict], campaign_code: str | None = None) -> dict:
    """Create and persist an order from a cart payload."""
    subtotal = calculate_subtotal(items)
    discounted = apply_campaign_discount(subtotal, campaign_code)
    total = add_tax(discounted, tax_rate=0.18)

    order = {
        "id": 9001,
        "user_id": user["id"],
        "items": items,
        "subtotal": subtotal,
        "total": total,
    }

    save_order(order)
    send_receipt_email(user, order)
    record_event("order_created", {"order_id": order["id"], "user_id": user["id"]})
    return order
