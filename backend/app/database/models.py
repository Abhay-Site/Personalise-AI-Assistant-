"""
models.py — SQLAlchemy ORM models (classical column style)

Using classical Column() syntax instead of Mapped[] annotations for
full compatibility with Python 3.14 and all SQLAlchemy 2.x versions.

Google (Gmail, Calendar, Drive) remains the source of truth for live data.
Only Personal AI Assistant's own state lives here.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from app.database.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    profile_picture = Column(String(500), nullable=True)
    google_credentials_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    automation_rules = relationship("AutomationRule", back_populates="user", cascade="all, delete-orphan")
    action_plans = relationship("ActionPlan", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
# Conversations & Messages
# ─────────────────────────────────────────────────────────────

class Conversation(Base):
    """A named conversation thread between the user and ORBIT 180."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(500), default="New Conversation")
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    action_plans = relationship("ActionPlan", back_populates="conversation")


class Message(Base):
    """
    A single message in a conversation.
    Roles: user | model | system | tool
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True, nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversation = relationship("Conversation", back_populates="messages")


# ─────────────────────────────────────────────────────────────
# User Memory
# ─────────────────────────────────────────────────────────────

class Memory(Base):
    """
    Structured user preferences injected into AI prompts.
    Example: key="preferred_meeting_time" value="11 AM to 4 PM"
    """
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="memories")


# ─────────────────────────────────────────────────────────────
# Automation Rules
# ─────────────────────────────────────────────────────────────

class AutomationRule(Base):
    """User-defined automation rules (Phase 6+)."""
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    trigger = Column(String(500), nullable=False)
    condition = Column(Text, nullable=True)
    action = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="automation_rules")


# ─────────────────────────────────────────────────────────────
# Action Plans
# ─────────────────────────────────────────────────────────────

class ActionPlan(Base):
    """
    A structured multi-step plan generated before execution.
    Status flow: pending → approved | rejected → executed | failed
    """
    __tablename__ = "action_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    plan_json = Column(JSON, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="action_plans")
    conversation = relationship("Conversation", back_populates="action_plans")
    approvals = relationship("Approval", back_populates="action_plan", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
# Approvals
# ─────────────────────────────────────────────────────────────

class Approval(Base):
    """
    Records a user's explicit decision on a sensitive agent action.
    An action must NEVER execute without an Approval(approved=True) record.
    """
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    action_plan_id = Column(Integer, ForeignKey("action_plans.id"), index=True, nullable=False)
    action_type = Column(String(100), nullable=False)
    approved = Column(Boolean, nullable=False)
    approved_at = Column(DateTime(timezone=True), default=_now)

    action_plan = relationship("ActionPlan", back_populates="approvals")


# ─────────────────────────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable record of every significant agent action.
    Never store raw secrets, passwords, or full OAuth tokens here.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    conversation_id = Column(Integer, nullable=True)
    action_type = Column(String(100), nullable=False)
    service = Column(String(100), nullable=False)
    tool_name = Column(String(255), nullable=False)
    input_summary = Column(Text, nullable=True)
    result_summary = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    approval_required = Column(Boolean, default=False)
    approval_status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="audit_logs")
