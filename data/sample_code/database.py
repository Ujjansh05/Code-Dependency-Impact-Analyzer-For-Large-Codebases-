"""Database connection and query module for the demo application."""


def get_connection() -> dict:
    """Get a database connection (simulated)."""
    return {"name": "demo_db", "host": "localhost", "port": 5432}


def fetch_orders(conn: dict, user_id: int) -> list[dict]:
    """Fetch orders for a user (simulated)."""
    _ = conn  # would use the connection in real code
    return [
        {
            "id": 101,
            "user_id": user_id,
            "items": [
                {"name": "Widget A", "price": 29.99, "quantity": 2},
                {"name": "Widget B", "price": 14.50, "quantity": 1},
            ],
        },
        {
            "id": 102,
            "user_id": user_id,
            "items": [
                {"name": "Gadget X", "price": 99.99, "quantity": 1},
            ],
        },
    ]


def save_order(conn: dict, order: dict) -> bool:
    """Save an order to the database (simulated)."""
    print(f"[DB] Saving order #{order.get('id')} to {conn['name']}")
    return True
