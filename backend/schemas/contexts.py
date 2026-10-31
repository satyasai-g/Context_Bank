from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from backend.schemas.triggers import normalize_trigger_word, TriggerResponse


class DecisionItem(BaseModel):
    text: str
    status: str = "confirmed"  # "confirmed" or "proposed"
    date: Optional[str] = None


class SourceReferenceItem(BaseModel):
    title: str
    url: Optional[str] = None
    notes: Optional[str] = None


class ContextCreate(BaseModel):
    trigger_word: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    summary: str = Field(..., min_length=1)
    detailed_content: Optional[str] = ""
    status: str = "Active"
    category: str = "General"
    tags: List[str] = Field(default_factory=list)
    important_decisions: List[DecisionItem] = Field(default_factory=list)
    completed_work: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    source_references: List[SourceReferenceItem] = Field(default_factory=list)
    privacy: str = "private"
    alternative_triggers: List[str] = Field(default_factory=list)
    related_context_ids: List[str] = Field(default_factory=list)
    source_conversation: Optional[str] = None

    @field_validator("trigger_word")
    @classmethod
    def clean_primary_trigger(cls, v: str) -> str:
        return normalize_trigger_word(v)

    @field_validator("alternative_triggers")
    @classmethod
    def clean_alt_triggers(cls, v: List[str]) -> List[str]:
        return [normalize_trigger_word(item) for item in v if item and item.strip()]


class ContextUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    detailed_content: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    important_decisions: Optional[List[DecisionItem]] = None
    completed_work: Optional[List[str]] = None
    open_questions: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None
    source_references: Optional[List[SourceReferenceItem]] = None
    privacy: Optional[str] = None
    is_archived: Optional[bool] = None
    change_summary: Optional[str] = "Updated context details"


class ContextResponse(BaseModel):
    id: str
    user_id: str
    primary_trigger: str
    alternative_triggers: List[str] = Field(default_factory=list)
    title: str
    summary: str
    detailed_content: Optional[str] = None
    status: str
    category: str
    tags: List[str]
    important_decisions: List[Dict[str, Any]]
    completed_work: List[str]
    open_questions: List[str]
    next_steps: List[str]
    source_references: List[Dict[str, Any]]
    privacy: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None
    version_count: int = 1

    model_config = ConfigDict(from_attributes=True)


class ContextSummaryItem(BaseModel):
    id: str
    primary_trigger: str
    alternative_triggers: List[str] = Field(default_factory=list)
    title: str
    summary: str
    category: str
    tags: List[str]
    status: str
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None


class ContextListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    contexts: List[ContextSummaryItem]


class VersionResponse(BaseModel):
    id: str
    context_id: str
    version_number: int
    change_summary: str
    snapshot_data: Dict[str, Any]
    created_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VersionCompareResponse(BaseModel):
    context_id: str
    v1_number: int
    v2_number: int
    diff_fields: Dict[str, Dict[str, Any]]


class RestoreVersionRequest(BaseModel):
    reason: Optional[str] = "Restored previous version"


class ContextExportResponse(BaseModel):
    context: Dict[str, Any]
    export_format: str  # "json" or "markdown"
    content: str
    exported_at: datetime


class ContextImportRequest(BaseModel):
    data: Dict[str, Any]
    conflict_strategy: str = "fail"  # "fail", "rename", "overwrite"
    new_trigger_word: Optional[str] = None


class RelationshipCreate(BaseModel):
    target_context_id: str
    relationship_type: str = "related_to"
    notes: Optional[str] = None


class RelationshipResponse(BaseModel):
    id: str
    source_context_id: str
    target_context_id: str
    target_title: Optional[str] = None
    target_trigger: Optional[str] = None
    relationship_type: str
    notes: Optional[str] = None
    created_at: datetime
