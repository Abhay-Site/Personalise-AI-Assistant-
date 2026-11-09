from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from app.database import models
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────

def get_user_by_google_id(db: Session, google_id: str) -> models.User | None:
    return db.query(models.User).filter(models.User.google_id == google_id).first()


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, google_id: str, name: str, email: str, profile_picture: str | None = None) -> models.User:
    user = models.User(google_id=google_id, name=name, email=email, profile_picture=profile_picture)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created user: {email}")
    return user


def get_or_create_user(db: Session, google_id: str, name: str, email: str, profile_picture: str | None = None) -> models.User:
    user = get_user_by_google_id(db, google_id)
    if not user:
        user = create_user(db, google_id, name, email, profile_picture)
    return user


# ─────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────

def create_conversation(db: Session, user_id: int, title: str = "New Conversation") -> models.Conversation:
    convo = models.Conversation(user_id=user_id, title=title)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def get_conversations(db: Session, user_id: int, limit: int = 20) -> list[models.Conversation]:
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user_id)
        .order_by(models.Conversation.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_conversation(db: Session, conversation_id: int, user_id: int) -> models.Conversation | None:
    return (
        db.query(models.Conversation)
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == user_id,
        )
        .first()
    )


# ─────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────

def add_message(db: Session, conversation_id: int, role: str, content: str) -> models.Message:
    msg = models.Message(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: Session, conversation_id: int) -> list[models.Message]:
    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )


# ─────────────────────────────────────────────────────────────
# Memories
# ─────────────────────────────────────────────────────────────

def get_memories(db: Session, user_id: int, enabled_only: bool = False) -> list[models.Memory]:
    q = db.query(models.Memory).filter(models.Memory.user_id == user_id)
    if enabled_only:
        q = q.filter(models.Memory.enabled == True)  # noqa: E712
    return q.order_by(models.Memory.created_at.desc()).all()


def create_memory(db: Session, user_id: int, key: str, value: str, category: str = "general") -> models.Memory:
    mem = models.Memory(user_id=user_id, key=key, value=value, category=category)
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def update_memory(db: Session, memory_id: int, user_id: int, **kwargs) -> models.Memory | None:
    mem = db.query(models.Memory).filter(
        models.Memory.id == memory_id,
        models.Memory.user_id == user_id,
    ).first()
    if not mem:
        return None
    for key, val in kwargs.items():
        setattr(mem, key, val)
    db.commit()
    db.refresh(mem)
    return mem


def delete_memory(db: Session, memory_id: int, user_id: int) -> bool:
    mem = db.query(models.Memory).filter(
        models.Memory.id == memory_id,
        models.Memory.user_id == user_id,
    ).first()
    if not mem:
        return False
    db.delete(mem)
    db.commit()
    return True


# ─────────────────────────────────────────────────────────────
# Action Plans
# ─────────────────────────────────────────────────────────────

def create_action_plan(db: Session, user_id: int, plan_json: dict, conversation_id: int | None = None) -> models.ActionPlan:
    plan = models.ActionPlan(user_id=user_id, conversation_id=conversation_id, plan_json=plan_json)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_action_plan_status(db: Session, plan_id: int, status: str) -> models.ActionPlan | None:
    plan = db.query(models.ActionPlan).filter(models.ActionPlan.id == plan_id).first()
    if plan:
        plan.status = status
        db.commit()
        db.refresh(plan)
    return plan


# ─────────────────────────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────────────────────────

def create_audit_log(
    db: Session,
    user_id: int,
    action_type: str,
    service: str,
    tool_name: str,
    status: str,
    conversation_id: int | None = None,
    input_summary: str | None = None,
    result_summary: str | None = None,
    approval_required: bool = False,
    approval_status: str | None = None,
) -> models.AuditLog:
    log = models.AuditLog(
        user_id=user_id,
        conversation_id=conversation_id,
        action_type=action_type,
        service=service,
        tool_name=tool_name,
        input_summary=input_summary,
        result_summary=result_summary,
        status=status,
        approval_required=approval_required,
        approval_status=approval_status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(
    db: Session,
    user_id: int,
    service: str | None = None,
    status: str | None = None,
    approval_status: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> list[models.AuditLog]:
    q = db.query(models.AuditLog).filter(models.AuditLog.user_id == user_id)
    if service:
        q = q.filter(models.AuditLog.service == service)
    if status:
        q = q.filter(models.AuditLog.status == status)
    if approval_status:
        q = q.filter(models.AuditLog.approval_status == approval_status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (models.AuditLog.tool_name.ilike(pattern))
            | (models.AuditLog.input_summary.ilike(pattern))
            | (models.AuditLog.result_summary.ilike(pattern))
        )
    return q.order_by(models.AuditLog.created_at.desc()).limit(limit).all()
