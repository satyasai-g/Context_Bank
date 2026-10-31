from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ExactRetrievalRequest(BaseModel):
    trigger: str = Field(..., description="The registered exact trigger word, e.g. VOXCENT")
    detail_level: str = Field("summary_and_state", description="summary_only, summary_and_state, detailed, full_archive")
    output_format: str = Field("markdown", description="markdown, json, prompt")


class RetrievePromptRequest(BaseModel):
    prompt: str = Field(..., description="Natural language prompt like 'Continue VOXCENT from where I stopped'")
    detail_level: str = "summary_and_state"
    output_format: str = "prompt"


class ContextPackageResponse(BaseModel):
    context_id: str
    primary_trigger: str
    title: str
    summary: str
    status: str
    detail_level: str
    output_format: str
    package_content: str
    structured_data: Dict[str, Any]
    retrieved_at: datetime
    retrieved_via: str = "exact_trigger"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language semantic search query")
    limit: int = Field(10, ge=1, le=50)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    search_mode: str = Field("hybrid", description="hybrid, text, vector")


class SearchResultItem(BaseModel):
    context_id: str
    primary_trigger: str
    title: str
    summary: str
    category: str
    tags: List[str]
    relevance_score: float
    match_reason: str


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
    search_provider_used: str


class QuickLookupResponse(BaseModel):
    found: bool
    trigger_searched: str
    message: str
    context: Optional[Dict[str, Any]] = None
    package: Optional[str] = None
