"""
api/memory.py — User memory management endpoints

GET  /api/memory          — List all memories
POST /api/memory          — Create a memory
PUT  /api/memory/{id}     — Update a memory
DELETE /api/memory/{id}   — Delete a memory
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import crud
from app.api.auth import get_mock_user
from app.database.models import User
from app.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest, MemorySchema
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", response_model=list[MemorySchema])
def list_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """List all memories for the current user (enabled and disabled)."""
    return crud.get_memories(db, user_id=current_user.id)


@router.post("", response_model=MemorySchema, status_code=201)
def create_memory(
    request: MemoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """Create a new user memory/preference."""
    memory = crud.create_memory(
        db,
        user_id=current_user.id,
        key=request.key,
        value=request.value,
        category=request.category,
    )
    logger.info(f"Memory created for user {current_user.id}: {request.key}")
    return memory


@router.put("/{memory_id}", response_model=MemorySchema)
def update_memory(
    memory_id: int,
    request: MemoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """Update an existing memory."""
    updates = request.model_dump(exclude_none=True)
    memory = crud.update_memory(db, memory_id=memory_id, user_id=current_user.id, **updates)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", status_code=204)
def delete_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """Delete a memory permanently."""
    deleted = crud.delete_memory(db, memory_id=memory_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
