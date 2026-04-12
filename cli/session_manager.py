"""Persistent query session manager.

Stores chat sessions at ~/.graphxploit/sessions/ as JSON files.
Each session tracks its queries, results, and timestamps.
Sessions survive restarts and are cleaned up on uninstall.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SESSIONS_DIR = os.path.join(Path.home(), ".graphxploit", "sessions")


def _ensure_dir() -> None:
    os.makedirs(SESSIONS_DIR, exist_ok=True)


# ── Session Data ────────────────────────────────────────────────


class QueryEntry:
    """A single query/response pair inside a session."""

    def __init__(
        self,
        question: str,
        target: str = "",
        target_type: str = "",
        affected: list[str] | None = None,
        explanation: str = "",
        risk: str = "",
        timestamp: str = "",
    ):
        self.question = question
        self.target = target
        self.target_type = target_type
        self.affected = affected or []
        self.explanation = explanation
        self.risk = risk
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "target": self.target,
            "target_type": self.target_type,
            "affected": self.affected,
            "explanation": self.explanation,
            "risk": self.risk,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueryEntry":
        return cls(
            question=data.get("question", ""),
            target=data.get("target", ""),
            target_type=data.get("target_type", ""),
            affected=data.get("affected", []),
            explanation=data.get("explanation", ""),
            risk=data.get("risk", ""),
            timestamp=data.get("timestamp", ""),
        )


class Session:
    """A named conversation session containing multiple queries."""

    def __init__(
        self,
        session_id: str = "",
        name: str = "",
        created_at: str = "",
        updated_at: str = "",
        entries: list[QueryEntry] | None = None,
    ):
        self.id = session_id or uuid.uuid4().hex[:8]
        self.name = name or f"Session {self.id}"
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.entries: list[QueryEntry] = entries or []

    @property
    def query_count(self) -> int:
        return len(self.entries)

    @property
    def last_question(self) -> str:
        if self.entries:
            return self.entries[-1].question
        return ""

    def add_entry(self, entry: QueryEntry) -> None:
        self.entries.append(entry)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        entries = [QueryEntry.from_dict(e) for e in data.get("entries", [])]
        return cls(
            session_id=data.get("id", ""),
            name=data.get("name", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            entries=entries,
        )


# ── CRUD ────────────────────────────────────────────────────────


def _session_path(session_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")


def save_session(session: Session) -> None:
    """Persist a session to disk."""
    _ensure_dir()
    with open(_session_path(session.id), "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, indent=2, default=str)


def load_session(session_id: str) -> Session | None:
    """Load a session by ID. Returns None if not found."""
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Session.from_dict(data)
    except (json.JSONDecodeError, OSError):
        return None


def list_sessions() -> list[Session]:
    """Return all sessions, sorted by most recently updated."""
    _ensure_dir()
    sessions: list[Session] = []
    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(Session.from_dict(data))
        except (json.JSONDecodeError, OSError):
            continue
    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session by ID. Returns True if deleted."""
    path = _session_path(session_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def delete_all_sessions() -> int:
    """Delete all sessions. Returns the count deleted."""
    _ensure_dir()
    count = 0
    for fname in os.listdir(SESSIONS_DIR):
        if fname.endswith(".json"):
            os.remove(os.path.join(SESSIONS_DIR, fname))
            count += 1
    return count


def create_session(name: str = "") -> Session:
    """Create and save a new empty session."""
    session = Session(name=name)
    save_session(session)
    return session
