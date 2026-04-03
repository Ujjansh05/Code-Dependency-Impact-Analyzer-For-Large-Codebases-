"""Audit logger used to create extra call dependencies for analysis."""


def record_event(event: str, payload: dict) -> None:
    """Record an informational event."""
    print(f"[AUDIT] {event} :: {payload}")


def record_security_event(event: str, payload: dict) -> None:
    """Record a security-sensitive event."""
    record_event(f"security.{event}", payload)
