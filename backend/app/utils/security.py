"""
security.py — Security utilities

Handles session tokens and any other security-related helpers.
Phase 1: Simple token generation.
Phase 3+: Full OAuth token management.
"""

import secrets
import hashlib


def generate_session_token() -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_urlsafe(32)


def hash_value(value: str) -> str:
    """One-way hash for storing sensitive identifiers (e.g. Google IDs)."""
    return hashlib.sha256(value.encode()).hexdigest()
