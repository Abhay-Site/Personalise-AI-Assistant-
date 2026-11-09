"""
api/chat.py — Main chat endpoint

This is the primary entry point for all user interactions.

POST /api/chat:
  1. Get or create a conversation
  2. Save the user message
  3. Load user memories
  4. Build conversation history
  5. Call the AI orchestrator
  6. Save the assistant reply
  7. Log the interaction to audit
  8. Return a structured ChatResponse
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import crud
from app.api.auth import get_mock_user
from app.database.models import User
from app.schemas.chat import ChatRequest, ChatResponse, TraceStep
from app.agents.orchestrator import process_message
from app.services.memory_service import get_memories_for_prompt
from app.services.google_auth_service import get_user_credentials
from app.services.audit_service import log_action
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """
    Process a user message and return an AI agent response.

    The response includes:
    - The assistant's text reply
    - An action plan (if applicable)
    - An execution trace showing what the agent did
    - An approval request (if a sensitive action is planned)
    """
    logger.info(f"Chat request from user {current_user.id}: '{request.message[:80]}...'")

    # ── Step 1: Get or create conversation ────────────────────
    if request.conversation_id:
        conversation = crud.get_conversation(db, request.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = crud.create_conversation(
            db,
            user_id=current_user.id,
            title=request.message[:60] + ("..." if len(request.message) > 60 else ""),
        )

    # ── Step 2: Save user message ─────────────────────────────
    crud.add_message(db, conversation_id=conversation.id, role="user", content=request.message)

    # ── Step 3: Load memories ─────────────────────────────────
    memories = get_memories_for_prompt(db, user_id=current_user.id)

    # ── Step 4: Build conversation history ────────────────────
    messages = crud.get_messages(db, conversation_id=conversation.id)
    history = [{"role": m.role, "content": m.content} for m in messages]

    # ── Step 5: Call AI orchestrator ──────────────────────────
    try:
        user_creds = get_user_credentials(db, current_user)
        result = await process_message(
            user_message=request.message,
            memories=memories,
            conversation_history=history,
            credentials=user_creds,
            user_id=current_user.id,
        )
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")

    # ── Step 6: Save assistant reply ──────────────────────────
    assistant_message = crud.add_message(
        db,
        conversation_id=conversation.id,
        role="model",
        content=result["reply"],
    )

    # ── Step 7: Save action plan if present ───────────────────
    plan_record = None
    if result.get("action_plan"):
        plan_dict = result["action_plan"].model_dump()
        if result.get("approval_action"):
            plan_dict["pending_action"] = result["approval_action"]
        plan_record = crud.create_action_plan(
            db,
            user_id=current_user.id,
            conversation_id=conversation.id,
            plan_json=plan_dict,
        )

    # ── Step 8: Audit log ─────────────────────────────────────
    log_action(
        db=db,
        user_id=current_user.id,
        tool_name="chat",
        service="system",
        action_type="read",
        status="success",
        conversation_id=conversation.id,
        input_summary=request.message[:200],
        result_summary=result["reply"][:200],
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        reply=result["reply"],
        action_plan_id=plan_record.id if plan_record else None,
        action_plan=result.get("action_plan"),
        trace=result.get("trace", []),
        requires_approval=result.get("requires_approval", False),
        approval_action=result.get("approval_action"),
        integration_status=result.get("integration_status", "connected"),
        model_name=result.get("model_name"),
        is_fallback=result.get("is_fallback", False),
        error_detail=result.get("error_detail"),
    )


@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """List all conversations for the current user."""
    conversations = crud.get_conversations(db, user_id=current_user.id)
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """Get all messages in a conversation."""
    conversation = crud.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = crud.get_messages(db, conversation_id=conversation_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in messages
    ]
