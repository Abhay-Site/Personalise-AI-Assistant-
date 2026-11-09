"""schemas/memory.py — Pydantic models for the /api/memory endpoint"""

from datetime import datetime
from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    category: str = Field("general", max_length=100)


class MemoryUpdateRequest(BaseModel):
    key: str | None = Field(None, max_length=255)
    value: str | None = None
    category: str | None = Field(None, max_length=100)
    enabled: bool | None = None


class MemorySchema(BaseModel):
    id: int
    key: str
    value: str
    category: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
