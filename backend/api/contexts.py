from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Context, ContextTrigger, ContextRelationship
from backend.api.auth import get_current_user
from backend.context_bank.storage import ContextStorage
from backend.context_bank.retrieval import ContextRetrievalEngine
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.context_bank.context_packager import ContextPackager
from backend.services.summarization_service import SummarizationService
from backend.services.embedding_service import EmbeddingService
from backend.core.exceptions import (
    ContextNotFoundError,
    TriggerNotFoundError,
    TriggerAlreadyExistsError,
    UnauthorizedAccessError,
)
from backend.schemas.contexts import (
    ContextCreate,
    ContextUpdate,
    ContextResponse,
    ContextSummaryItem,
    ContextListResponse,
    ContextExportResponse,
    ContextImportRequest,
    RelationshipCreate,
    RelationshipResponse,
)
from backend.schemas.retrieval import (
    ExactRetrievalRequest,
    RetrievePromptRequest,
    ContextPackageResponse,
)

router = APIRouter(prefix="/api/v1/contexts", tags=["Contexts"])


def _build_context_response(db: Session, context: Context) -> ContextResponse:
    """Helper to assemble full ContextResponse with primary & alternative triggers."""
    triggers = TriggerRegistry.list_triggers_for_context(db, context.id)
    primary = next((t.trigger_word for t in triggers if t.is_primary), "UNKNOWN")
    alts = [t.trigger_word for t in triggers if not t.is_primary]

    return ContextResponse(
        id=context.id,
        user_id=context.user_id,
        primary_trigger=primary,
        alternative_triggers=alts,
        title=context.title,
        summary=context.summary,
        detailed_content=context.detailed_content,
        status=context.status,
        category=context.category,
        tags=context.tags or [],
        important_decisions=context.important_decisions or [],
        completed_work=context.completed_work or [],
        open_questions=context.open_questions or [],
        next_steps=context.next_steps or [],
        source_references=context.source_references or [],
        privacy=context.privacy,
        is_archived=context.is_archived,
        created_at=context.created_at,
        updated_at=context.updated_at,
        last_accessed_at=context.last_accessed_at,
        version_count=len(context.versions) if context.versions else 1,
    )


@router.post("", response_model=ContextResponse, status_code=status.HTTP_201_CREATED)
def create_context(
    data: ContextCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new context with a primary trigger, structured fields, and initial version.
    """
    try:
        context, primary_trig = ContextStorage.create_context(
            db=db,
            user_id=current_user.id,
            data=data,
        )

        # Generate embedding vector asynchronously/inline
        combined_text = f"{context.title} {context.summary} {' '.join(context.tags or [])}"
        context.embedding = EmbeddingService.get_embedding(combined_text)

        db.commit()
        db.refresh(context)
        return _build_context_response(db, context)
    except TriggerAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ContextListResponse)
def list_contexts(
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("updated_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List contexts for authenticated user with filters, sorting, and pagination."""
    contexts, total = ContextStorage.list_contexts(
        db=db,
        user_id=current_user.id,
        category=category,
        tag=tag,
        status=status,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    items = []
    for c in contexts:
        triggers = TriggerRegistry.list_triggers_for_context(db, c.id)
        primary = next((t.trigger_word for t in triggers if t.is_primary), "UNKNOWN")
        alts = [t.trigger_word for t in triggers if not t.is_primary]
        items.append(
            ContextSummaryItem(
                id=c.id,
                primary_trigger=primary,
                alternative_triggers=alts,
                title=c.title,
                summary=c.summary,
                category=c.category,
                tags=c.tags or [],
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
                last_accessed_at=c.last_accessed_at,
            )
        )

    return ContextListResponse(
        total=total,
        page=page,
        page_size=page_size,
        contexts=items,
    )


@router.post("/retrieve", response_model=ContextPackageResponse)
def retrieve_context_package(
    data: ExactRetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve an AI-ready context package using an exact trigger word.
    Strictly reports not found if exact trigger does not exist.
    """
    try:
        pkg = ContextRetrievalEngine.retrieve_by_exact_trigger(
            db=db,
            user_id=current_user.id,
            trigger_word=data.trigger,
            detail_level=data.detail_level,
            output_format=data.output_format,
            accessed_via="api_retrieve",
        )
        db.commit()
        return pkg
    except TriggerNotFoundError:
        db.rollback()
        raise
    except UnauthorizedAccessError:
        db.rollback()
        raise


@router.post("/retrieve-prompt", response_model=ContextPackageResponse)
def retrieve_by_prompt(
    data: RetrievePromptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Parse a natural language instruction (e.g. 'Continue VOXCENT from where I stopped')
    and retrieve the corresponding context package.
    """
    try:
        pkg = ContextRetrievalEngine.retrieve_by_prompt(
            db=db,
            user_id=current_user.id,
            prompt=data.prompt,
            detail_level=data.detail_level,
            output_format=data.output_format,
        )
        db.commit()
        return pkg
    except TriggerNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/{context_id}", response_model=ContextResponse)
def get_context(
    context_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full context by identifier, enforcing ownership."""
    try:
        context = ContextStorage.get_context(db, context_id, current_user.id)
        return _build_context_response(db, context)
    except ContextNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UnauthorizedAccessError as e:
        raise HTTPException(status_code=403, detail=e.message)


@router.patch("/{context_id}", response_model=ContextResponse)
def update_context(
    context_id: str,
    data: ContextUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update context details and record a new version snapshot."""
    try:
        context = ContextStorage.update_context(
            db=db,
            context_id=context_id,
            user_id=current_user.id,
            data=data,
        )

        # Update embedding
        combined_text = f"{context.title} {context.summary} {' '.join(context.tags or [])}"
        context.embedding = EmbeddingService.get_embedding(combined_text)

        db.commit()
        db.refresh(context)
        return _build_context_response(db, context)
    except ContextNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=e.message)
    except UnauthorizedAccessError as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=e.message)


@router.delete("/{context_id}", status_code=status.HTTP_200_OK)
def delete_context(
    context_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a context and all its triggers, versions, relationships, and logs.
    """
    try:
        ContextStorage.delete_context(db, context_id, current_user.id)
        db.commit()
        return {"status": "success", "message": f"Context '{context_id}' deleted."}
    except ContextNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=e.message)
    except UnauthorizedAccessError as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=e.message)


@router.post("/{context_id}/export", response_model=ContextExportResponse)
def export_context(
    context_id: str,
    format: str = Query("json", description="json or markdown"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a context in JSON or Markdown format."""
    context = ContextStorage.get_context(db, context_id, current_user.id)
    triggers = TriggerRegistry.list_triggers_for_context(db, context.id)
    primary = next((t.trigger_word for t in triggers if t.is_primary), "UNKNOWN")

    structured = ContextPackager.to_structured_dict(context, primary, detail_level="full_archive")
    structured["alternative_triggers"] = [t.trigger_word for t in triggers if not t.is_primary]

    content = ContextPackager.package(
        context, primary, detail_level="full_archive", output_format=format
    )

    return ContextExportResponse(
        context=structured,
        export_format=format,
        content=content,
        exported_at=datetime.now(timezone.utc),
    )


@router.post("/import", response_model=ContextResponse)
def import_context(
    payload: ContextImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import a context from structured data.
    Validates data, checks duplicate triggers, and applies conflict strategy.
    """
    data = payload.data
    raw_trigger = payload.new_trigger_word or data.get("trigger") or data.get("primary_trigger") or "IMPORTED"

    create_data = ContextCreate(
        trigger_word=raw_trigger,
        title=data.get("title", "Imported Context"),
        summary=data.get("summary", "No summary provided"),
        detailed_content=data.get("detailed_content", ""),
        status=data.get("status", "Active"),
        category=data.get("category", "General"),
        tags=data.get("tags", []),
        important_decisions=[{"text": d if isinstance(d, str) else d.get("text", "")} for d in data.get("confirmed_decisions", data.get("important_decisions", []))],
        completed_work=data.get("completed_work", []),
        open_questions=data.get("open_questions", []),
        next_steps=data.get("next_steps", []),
        privacy="private",
    )

    try:
        context, _ = ContextStorage.create_context(db, current_user.id, create_data)
        db.commit()
        db.refresh(context)
        return _build_context_response(db, context)
    except TriggerAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Trigger '{e.trigger}' already exists. Choose a different trigger name or rename before importing.",
        )


@router.post("/extract", response_model=Dict[str, Any])
def extract_context(
    payload: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract structured context draft and auto-generate trigger words from raw conversation.
    Checks user namespace to avoid trigger collisions.
    """
    raw_text = payload.get("text", "")
    return SummarizationService.extract_context_from_text(
        raw_text=raw_text,
        db=db,
        user_id=current_user.id,
    )


@router.post("/auto-create-from-chat", response_model=ContextResponse)
def auto_create_from_chat(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Automatically analyze chat/conversation text, determine the best trigger word,
    extract structured decisions, summary, and next steps, and immediately save it
    to Context Bank in a single autonomous operation.
    """
    raw_text = payload.get("chat_text", "")
    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="chat_text is required.")

    extracted = SummarizationService.extract_context_from_text(
        raw_text=raw_text,
        db=db,
        user_id=current_user.id,
    )

    trigger_word = payload.get("custom_trigger") or extracted.get("suggested_trigger") or "CONTEXT"
    alts = extracted.get("alternative_triggers", [])

    create_data = ContextCreate(
        trigger_word=trigger_word,
        alternative_triggers=alts,
        title=extracted.get("title", f"{trigger_word.title()} Project"),
        summary=extracted.get("summary", "Context automatically created from chat conversation."),
        detailed_content=raw_text[:4000],
        status=extracted.get("status", "Active"),
        category=extracted.get("category", "Projects"),
        tags=extracted.get("tags", ["auto-chat"]),
        important_decisions=[{"text": d if isinstance(d, str) else d.get("text", "")} for d in extracted.get("confirmed_decisions", [])],
        completed_work=extracted.get("completed_work", []),
        open_questions=extracted.get("open_questions", []),
        next_steps=extracted.get("next_steps", []),
        privacy="private",
    )

    try:
        context, _ = ContextStorage.create_context(db, current_user.id, create_data)

        # Index embedding
        combined_text = f"{context.title} {context.summary} {' '.join(context.tags or [])}"
        context.embedding = EmbeddingService.get_embedding(combined_text)

        db.commit()
        db.refresh(context)
        return _build_context_response(db, context)
    except TriggerAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{context_id}/relationships", response_model=RelationshipResponse)
def add_relationship(
    context_id: str,
    data: RelationshipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link two contexts explicitly."""
    rel = ContextStorage.link_relationship(
        db=db,
        user_id=current_user.id,
        source_id=context_id,
        target_id=data.target_context_id,
        rel_type=data.relationship_type,
        notes=data.notes,
    )
    db.commit()

    target_ctx = db.query(Context).filter(Context.id == data.target_context_id).first()
    target_trig = db.query(ContextTrigger).filter(
        ContextTrigger.context_id == data.target_context_id,
        ContextTrigger.is_primary == True,
    ).first()

    return RelationshipResponse(
        id=rel.id,
        source_context_id=rel.source_context_id,
        target_context_id=rel.target_context_id,
        target_title=target_ctx.title if target_ctx else None,
        target_trigger=target_trig.trigger_word if target_trig else None,
        relationship_type=rel.relationship_type,
        notes=rel.notes,
        created_at=rel.created_at,
    )


@router.get("/{context_id}/relationships", response_model=List[RelationshipResponse])
def get_relationships(
    context_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List relationships for this context."""
    ContextStorage.get_context(db, context_id, current_user.id)
    rels = db.query(ContextRelationship).filter(
        (ContextRelationship.source_context_id == context_id) |
        (ContextRelationship.target_context_id == context_id)
    ).all()

    items = []
    for r in rels:
        other_id = r.target_context_id if r.source_context_id == context_id else r.source_context_id
        other_ctx = db.query(Context).filter(Context.id == other_id).first()
        other_trig = db.query(ContextTrigger).filter(
            ContextTrigger.context_id == other_id,
            ContextTrigger.is_primary == True,
        ).first()

        items.append(
            RelationshipResponse(
                id=r.id,
                source_context_id=r.source_context_id,
                target_context_id=r.target_context_id,
                target_title=other_ctx.title if other_ctx else None,
                target_trigger=other_trig.trigger_word if other_trig else None,
                relationship_type=r.relationship_type,
                notes=r.notes,
                created_at=r.created_at,
            )
        )
    return items
