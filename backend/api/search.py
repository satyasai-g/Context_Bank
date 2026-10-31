from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Context, ContextTrigger
from backend.api.auth import get_current_user
from backend.services.search_service import SearchService
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.context_bank.context_packager import ContextPackager
from backend.schemas.retrieval import SearchRequest, SearchResponse, QuickLookupResponse
from backend.core.exceptions import TriggerNotFoundError

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
def search_contexts(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search contexts by meaning, topic, or keyword.
    Completely separate from exact trigger lookup.
    """
    return SearchService.search(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        limit=payload.limit,
        category=payload.category,
        tags=payload.tags,
        search_mode=payload.search_mode,
    )


@router.get("/quick-lookup/{trigger}", response_model=QuickLookupResponse)
def quick_trigger_lookup(
    trigger: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Quick trigger lookup: checks if exact trigger exists in user namespace
    and returns a summary if found.
    """
    try:
        t = TriggerRegistry.resolve_exact_trigger(
            db=db,
            user_id=current_user.id,
            trigger_word=trigger,
            record_access=True,
        )
        ctx = db.query(Context).filter(Context.id == t.context_id).first()
        db.commit()

        if not ctx:
            return QuickLookupResponse(
                found=False,
                trigger_searched=trigger.strip().upper(),
                message="Trigger record exists but associated context was not found.",
            )

        pkg_str = ContextPackager.package(ctx, t.trigger_word, detail_level="summary_and_state")

        return QuickLookupResponse(
            found=True,
            trigger_searched=t.trigger_word,
            message="Exact trigger match resolved.",
            context={
                "id": ctx.id,
                "title": ctx.title,
                "summary": ctx.summary,
                "status": ctx.status,
                "category": ctx.category,
                "tags": ctx.tags or [],
            },
            package=pkg_str,
        )
    except TriggerNotFoundError:
        return QuickLookupResponse(
            found=False,
            trigger_searched=trigger.strip().upper(),
            message=f"No exact trigger registered for '{trigger.strip().upper()}'.",
        )
