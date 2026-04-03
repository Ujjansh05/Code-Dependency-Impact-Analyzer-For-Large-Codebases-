"""User repository with in-memory records for demo purposes."""

USERS = {
    "token_admin": {"id": 1, "name": "Admin User", "email": "admin@example.com"},
    "token_staff": {"id": 2, "name": "Staff User", "email": "staff@example.com"},
}


def get_user_by_token(token: str) -> dict | None:
    """Return a user object if token exists."""
    return USERS.get(token)
