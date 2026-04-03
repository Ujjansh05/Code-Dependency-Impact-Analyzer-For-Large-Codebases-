"""Notification service for post-checkout communication."""

from utils.audit import record_event


def send_receipt_email(user: dict, order: dict) -> None:
    """Simulate sending an email receipt after order creation."""
    print(f"[MAIL] Receipt sent to {user['email']} for order #{order['id']}")
    record_event("receipt_sent", {"order_id": order["id"], "email": user["email"]})
