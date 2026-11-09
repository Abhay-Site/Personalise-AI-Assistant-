"""
services/memory_service.py — User memory management

Loads, stores, and formats user memories for injection into AI prompts.
"""

from sqlalchemy.orm import Session
from app.database import crud
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_memories_for_prompt(db: Session, user_id: int) -> list[dict]:
    """
    Returns enabled memories as a list of dicts suitable for prompt injection.
    Only enabled memories are returned.
    """
    memories = crud.get_memories(db, user_id=user_id, enabled_only=True)
    return [{"key": m.key, "value": m.value, "category": m.category} for m in memories]


def save_memory_from_conversation(db: Session, user_id: int, key: str, value: str, category: str = "general"):
    """
    Save a new memory discovered during a conversation.
    Example: User says 'I prefer meetings after 11 AM' → save as preference.
    """
    existing = crud.get_memories(db, user_id=user_id)
    # Avoid duplicates: update if same key exists
    for mem in existing:
        if mem.key.lower() == key.lower():
            crud.update_memory(db, mem.id, user_id, value=value)
            logger.info(f"Updated memory for user {user_id}: {key}={value}")
            return

    crud.create_memory(db, user_id=user_id, key=key, value=value, category=category)
    logger.info(f"Created memory for user {user_id}: {key}={value}")
