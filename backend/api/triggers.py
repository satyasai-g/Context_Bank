from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Context, ContextTrigger
from backend.api.auth import get_current_user
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.core.exceptions import (
    TriggerNotFoundError,
    TriggerAlreadyExistsError,
    ValidationDomainError,
)
from backend.schemas.triggers import (
    TriggerCreate,
    TriggerRename,
    TriggerResponse,
    TriggerDetailResponse,
    TriggerListResponse,
    normalize_trigger_word,
)

router = APIRouter(prefix="/api/v1/triggers", tags=["Trigger Registry"])


@router.post("", response_model=TriggerResponse, status_code=status.HTTP_201_CREATED)
def register_trigger(
    data: TriggerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register a new trigger word for a context in the authenticated user's namespace.
    """
    try:
        trigger = TriggerRegistry.register_trigger(
            db=db,
            user_id=current_user.id,
            context_id=data.context_id,
            trigger_word=data.trigger_word,
            is_primary=data.is_primary,
        )
        db.commit()
        db.refresh(trigger)
        return trigger
    except TriggerAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TriggerListResponse)
def list_triggers(
    search: Optional[str] = Query(None, description="Prefix search for triggers"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all registered triggers in the authenticated user's namespace."""
    triggers = TriggerRegistry.list_user_triggers(db, current_user.id, search_prefix=search)

    details: List[TriggerDetailResponse] = []
    for t in triggers:
        ctx = db.query(Context).filter(Context.id == t.context_id).first()
        details.append(
            TriggerDetailResponse(
                id=t.id,
                context_id=t.context_id,
                trigger_word=t.trigger_word,
                is_primary=t.is_primary,
                created_at=t.created_at,
                last_accessed_at=t.last_accessed_at,
                access_count=t.access_count,
                context_title=ctx.title if ctx else None,
                context_summary=ctx.summary if ctx else None,
                context_status=ctx.status if ctx else None,
            )
        )

    return TriggerListResponse(total=len(details), triggers=details)


@router.get("/{trigger}", response_model=TriggerDetailResponse)
def resolve_trigger(
    trigger: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Resolve an exact trigger word in the user's namespace.
    Does NOT return unrelated semantic matches.
    """
    try:
        t = TriggerRegistry.resolve_exact_trigger(
            db=db,
            user_id=current_user.id,
            trigger_word=trigger,
            record_access=True,
        )
        db.commit()

        ctx = db.query(Context).filter(Context.id == t.context_id).first()
        return TriggerDetailResponse(
            id=t.id,
            context_id=t.context_id,
            trigger_word=t.trigger_word,
            is_primary=t.is_primary,
            created_at=t.created_at,
            last_accessed_at=t.last_accessed_at,
            access_count=t.access_count,
            context_title=ctx.title if ctx else None,
            context_summary=ctx.summary if ctx else None,
            context_status=ctx.status if ctx else None,
        )
    except TriggerNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.patch("/{trigger}", response_model=TriggerResponse)
def rename_trigger(
    trigger: str,
    data: TriggerRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a trigger word within the user's namespace."""
    try:
        updated = TriggerRegistry.rename_trigger(
            db=db,
            user_id=current_user.id,
            old_trigger_word=trigger,
            new_trigger_word=data.new_trigger_word,
        )
        db.commit()
        db.refresh(updated)
        return updated
    except TriggerNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=e.message)
    except TriggerAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=e.message)


@router.delete("/{trigger}", status_code=status.HTTP_200_OK)
def remove_trigger_alias(
    trigger: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a trigger alias.
    Note: Cannot delete primary trigger if no alternative trigger exists.
    """
    try:
        TriggerRegistry.remove_alias(db, current_user.id, trigger)
        db.commit()
        return {"status": "success", "message": f"Trigger '{trigger.strip().upper()}' removed."}
    except TriggerNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationDomainError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=e.message)
