"""Authentication service used by the sample checkout flow."""

from repositories.user_repo import get_user_by_token
from utils.audit import record_security_event


def get_authenticated_user(token: str) -> dict:
    """Validate token and return user data."""
    user = get_user_by_token(token)
    if not user:
        record_security_event("auth_failed", {"token": token})
        raise ValueError("Invalid token")

    record_security_event("auth_success", {"user_id": user["id"]})
    return user
