"""
session_store.py
===================

In-memory session management for Day 14, per Requirement 2: each
activity session is independent, terminates (clearing ALL its data) after
60 seconds of inactivity or when the user returns to the home screen, and
no session data persists after termination -- there is no database and
nothing is ever written to disk for a session.

Two layers enforce the 60-second timeout, not just one:
  1. The FRONTEND runs its own 60-second inactivity timer and calls
     DELETE /api/session/{id} + navigates home when it fires -- this is
     what a well-behaved client does.
  2. This module ALSO enforces the same timeout server-side (via
     is_expired() checked on every access, and a periodic background
     sweep in main.py) so that session data cannot outlive 60 seconds of
     inactivity even if a client never calls the terminate endpoint (a
     dropped connection, a closed tab, a buggy client, etc.). This is the
     real, authoritative enforcement of "no session data shall persist
     after termination" -- the frontend timer is a good citizen's
     nicety, not the actual guarantee.
"""

import os
import time
import uuid

SESSION_TIMEOUT_SECONDS = int(os.environ.get("SESSION_TIMEOUT_SECONDS", "60"))

# session_id -> {
#     "activity": "brain_buster" | "quick_fire" | "ask_explore",
#     "messages": [ {role, content}, ... ]          (LAST 6 kept, see append_message)
#     "used_riddle_indices": set(int)                (Brain Buster only)
#     "used_question_indices": set(int)              (Quick Fire only)
#     "current_index": int | None                     (index into the relevant content bank)
#     "hints_given": int                               (Brain Buster only, 0-3)
#     "created_at": float (epoch seconds)
#     "last_active": float (epoch seconds)
# }
sessions: dict = {}

MAX_CONTEXT_MESSAGES = 6  # Requirement 7: only the 6 most recent messages are kept


def create_session(activity: str) -> str:
    """Creates a brand-new session for the given activity and returns its new session_id."""
    session_id = str(uuid.uuid4())
    now = time.time()
    sessions[session_id] = {
        "activity": activity,
        "messages": [],
        "used_riddle_indices": set(),
        "used_question_indices": set(),
        "current_index": None,
        "hints_given": 0,
        "created_at": now,
        "last_active": now,
    }
    return session_id


def session_exists(session_id: str) -> bool:
    """Returns True if a session with this ID currently exists in the store."""
    return session_id in sessions


def is_expired(session_id: str) -> bool:
    """Returns True if the session hasn't been touched in over SESSION_TIMEOUT_SECONDS -- the server-side half of the 60-second inactivity rule."""
    if session_id not in sessions:
        return True
    return (time.time() - sessions[session_id]["last_active"]) > SESSION_TIMEOUT_SECONDS


def touch(session_id: str) -> None:
    """Updates a session's last-active timestamp -- called on every real interaction, resetting the 60-second inactivity clock."""
    if session_id in sessions:
        sessions[session_id]["last_active"] = time.time()


def terminate_session(session_id: str) -> bool:
    """Immediately and completely deletes a session's data. Returns True if a session was actually found and removed."""
    return sessions.pop(session_id, None) is not None


def sweep_expired_sessions() -> int:
    """Deletes every session that has exceeded the inactivity timeout. Returns how many were removed. Called periodically by a background task in main.py."""
    expired = [sid for sid in sessions if is_expired(sid)]
    for sid in expired:
        del sessions[sid]
    return len(expired)


def get_session(session_id: str) -> dict:
    """Returns the full mutable state dict for a session (messages, game progress, timestamps)."""
    return sessions[session_id]


def append_message(session_id: str, role: str, content: str) -> None:
    """Appends a message and trims to the MAX_CONTEXT_MESSAGES most recent (Requirement 7)."""
    messages = sessions[session_id]["messages"]
    messages.append({"role": role, "content": content})
    if len(messages) > MAX_CONTEXT_MESSAGES:
        del messages[: len(messages) - MAX_CONTEXT_MESSAGES]


def active_session_count() -> int:
    """Returns how many sessions are currently active, for the health-check endpoint."""
    return len(sessions)
