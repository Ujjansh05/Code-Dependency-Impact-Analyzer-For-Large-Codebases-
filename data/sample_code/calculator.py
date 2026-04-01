"""Order calculation utilities for the demo application."""


def calculate_total(items: list[dict]) -> float:
    """Calculate the total price for a list of items."""
    total = sum(item["price"] * item.get("quantity", 1) for item in items)
    return round(total, 2)


def apply_discount(total: float, percent: float = 10) -> float:
    """Apply a percentage discount to a total."""
    discount = total * (percent / 100)
    return round(total - discount, 2)


def calculate_tax(total: float, rate: float = 0.08) -> float:
    """Calculate tax on a total."""
    return round(total * rate, 2)
