"""Order repository with a minimal in-memory write path."""

_ORDERS: list[dict] = []


def save_order(order: dict) -> bool:
    """Persist order in memory."""
    _ORDERS.append(order)
    print(f"[DB] Saved order #{order['id']}")
    return True


def list_orders() -> list[dict]:
    """Return all orders for debugging."""
    return list(_ORDERS)
