"""Authentication module for the demo application."""

from database import get_connection


USERS_DB = {
    "admin": {"id": 1, "username": "admin", "password": "password123", "role": "premium"},
    "guest": {"id": 2, "username": "guest", "password": "guest", "role": "standard"},
}


def authenticate(username: str, password: str) -> dict:
    """Authenticate a user by username and password."""
    user = USERS_DB.get(username)
    if user and user["password"] == password:
        log_login(username)
        return user
    raise ValueError("Invalid credentials")


def get_user_role(user: dict) -> str:
    """Return the role of an authenticated user."""
    return user.get("role", "standard")


def log_login(username: str):
    """Log a successful login event."""
    conn = get_connection()
    print(f"[LOG] User '{username}' logged in (db={conn['name']})")
