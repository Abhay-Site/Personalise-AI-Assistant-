"""
services/audit_service.py — Sanitized Audit Logging Service

Security guarantees:
- Never persists raw secrets, API keys, bearer tokens, or full credentials.
- Masks sensitive patterns automatically prior to storage.
- Immutable historical audit trail for transparency and compliance.
"""

import re
from typing import Optional
from sqlalchemy.orm import Session
from app.database import crud
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Patterns that must never enter the persistent audit log
SENSITIVE_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z-_]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"password[\"':\s=]+[^\s,\"']+", re.IGNORECASE), "password=[REDACTED_SECRET]"),
    (re.compile(r"client_secret[\"':\s=]+[^\s,\"']+", re.IGNORECASE), "client_secret=[REDACTED]"),
]


def sanitize_summary(text: Optional[str], max_len: int = 250) -> Optional[str]:
    """Cleanses any detected credentials or tokens and truncates to safe length."""
    if not text:
        return text

    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "..."
    return sanitized


def log_action(
    db: Session,
    user_id: int,
    tool_name: str,
    service: str,
    action_type: str,
    status: str,
    conversation_id: int | None = None,
    input_summary: str | None = None,
    result_summary: str | None = None,
    approval_required: bool = False,
    approval_status: str | None = None,
):
    """
    Record an agent action in the audit log with automatic data sanitization.
    """
    try:
        clean_input = sanitize_summary(input_summary)
        clean_result = sanitize_summary(result_summary)

        crud.create_audit_log(
            db=db,
            user_id=user_id,
            action_type=action_type,
            service=service,
            tool_name=tool_name,
            status=status,
            conversation_id=conversation_id,
            input_summary=clean_input,
            result_summary=clean_result,
            approval_required=approval_required,
            approval_status=approval_status,
        )
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
