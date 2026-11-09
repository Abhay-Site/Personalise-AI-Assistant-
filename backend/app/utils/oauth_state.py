"""Temporary storage for OAuth PKCE verifiers."""

import time
from threading import Lock

_STATE_TTL_SECONDS = 600
_states: dict[str, tuple[str, float]] = {}
_lock = Lock()


def save_oauth_state(state: str, code_verifier: str | None) -> None:
    """Store a verifier temporarily, keyed by OAuth state."""
    if not state or not code_verifier:
        raise ValueError("OAuth state and PKCE code verifier are required")

    now = time.time()

    with _lock:
        expired = [
            key for key, (_, created_at) in _states.items()
            if now - created_at > _STATE_TTL_SECONDS
        ]

        for key in expired:
            _states.pop(key, None)

        _states[state] = (code_verifier, now)


def consume_oauth_state(state: str) -> str | None:
    """Retrieve a verifier once, then remove it."""
    if not state:
        return None

    with _lock:
        entry = _states.pop(state, None)

    if entry is None:
        return None

    verifier, created_at = entry

    if time.time() - created_at > _STATE_TTL_SECONDS:
        return None

    return verifier