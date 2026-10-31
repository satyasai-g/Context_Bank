import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


def normalize_trigger_word(val: str) -> str:
    """Normalize trigger word: strip whitespace, convert to uppercase."""
    if not val or not val.strip():
        raise ValueError("Trigger word cannot be empty.")
    cleaned = val.strip().upper()
    # Ensure reasonable characters: alphanumeric, hyphens, underscores, dots
    if not re.match(r"^[A-Z0-9_\-\.]+$", cleaned):
        raise ValueError("Trigger word must contain only letters, numbers, underscores, dashes, or dots.")
    if len(cleaned) > 100:
        raise ValueError("Trigger word cannot exceed 100 characters.")
    return cleaned


class TriggerCreate(BaseModel):
    trigger_word: str = Field(..., min_length=1, max_length=100)
    context_id: str
    is_primary: bool = False

    @field_validator("trigger_word")
    @classmethod
    def clean_trigger(cls, v: str) -> str:
        return normalize_trigger_word(v)


class TriggerRename(BaseModel):
    new_trigger_word: str = Field(..., min_length=1, max_length=100)

    @field_validator("new_trigger_word")
    @classmethod
    def clean_trigger(cls, v: str) -> str:
        return normalize_trigger_word(v)


class TriggerResponse(BaseModel):
    id: str
    context_id: str
    trigger_word: str
    is_primary: bool
    created_at: datetime
    last_accessed_at: Optional[datetime] = None
    access_count: int

    model_config = ConfigDict(from_attributes=True)


class TriggerDetailResponse(TriggerResponse):
    context_title: Optional[str] = None
    context_summary: Optional[str] = None
    context_status: Optional[str] = None


class TriggerListResponse(BaseModel):
    total: int
    triggers: List[TriggerDetailResponse]
