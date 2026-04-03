"""Sample checkout flow used for CLI end-to-end testing."""

from services.auth_service import get_authenticated_user
from services.order_service import checkout_order


def run_checkout(token: str) -> dict:
    """Authenticate a user and create a sample order."""
    user = get_authenticated_user(token)
    items = [
        {"sku": "SKU-101", "price": 49.99, "qty": 1},
        {"sku": "SKU-202", "price": 19.50, "qty": 2},
    ]
    return checkout_order(user, items, campaign_code="SPRING10")


def main() -> None:
    """Run a demo checkout."""
    order = run_checkout("token_admin")
    print(f"Created order #{order['id']} with total {order['total']:.2f}")


if __name__ == "__main__":
    main()
