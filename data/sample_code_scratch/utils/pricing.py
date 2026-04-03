"""Pricing helpers used by order_service."""


def calculate_subtotal(items: list[dict]) -> float:
    """Compute line-item subtotal."""
    return round(sum(item["price"] * item["qty"] for item in items), 2)


def apply_campaign_discount(subtotal: float, campaign_code: str | None) -> float:
    """Apply a campaign discount to subtotal."""
    if campaign_code == "SPRING10":
        return round(subtotal * 0.90, 2)
    return subtotal


def add_tax(amount: float, tax_rate: float) -> float:
    """Apply tax to amount."""
    return round(amount * (1.0 + tax_rate), 2)
