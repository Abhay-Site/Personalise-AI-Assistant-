"""
services/privacy_shield.py — Privacy Shield & PII Redaction Engine

Security & Privacy mandate:
Protects user confidentiality by masking Personally Identifiable Information (PII)
and confidential tokens before prompts are forwarded to third-party LLMs (Google Gemini).

Redacts:
- Phone numbers
- Credit card / financial numbers
- Passwords and secret credentials
- API keys and bearer tokens
- Social security / national ID patterns
"""

import re
from typing import Tuple, List
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Pre-compiled high-precision regex patterns for PII
PII_PATTERNS = [
    # 1. API Keys & Bearer Tokens
    (re.compile(r"AIza[0-9A-Za-z-_]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(?:sk|ghp|gho)_[a-zA-Z0-9]{20,}", re.IGNORECASE), "[REDACTED_TOKEN]"),
    # 2. Passwords & Secrets
    (re.compile(r"(?:password|passwd|secret)[\"':\s=]+[^\s,\"']+", re.IGNORECASE), "password=[REDACTED_SECRET]"),
    # 3. Credit Card / Financial Numbers (13-16 digits with optional spaces or dashes)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD_NUMBER]"),
    # 4. Phone Numbers (International & standard 10-digit formats)
    (re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
    # 5. Social Security Numbers (SSN format: XXX-XX-XXXX)
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
]


def redact_pii(text: str, enabled: bool = True) -> Tuple[str, List[str]]:
    """
    Scans text and redacts any detected PII or confidential credentials.

    Args:
        text: The source string destined for the LLM
        enabled: If False, returns original text unmodified

    Returns:
        (sanitized_text, list_of_redaction_labels_applied)
    """
    if not enabled or not text:
        return text, []

    sanitized = text
    applied: List[str] = []

    for pattern, replacement in PII_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            applied.append(replacement.strip("[]"))
            sanitized = pattern.sub(replacement, sanitized)

    if applied:
        logger.info(f"Privacy Shield active: masked {len(applied)} PII entity types: {applied}")

    return sanitized, applied
