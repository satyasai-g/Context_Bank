from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, ContextVersion
from backend.api.auth import get_current_user
from backend.context_bank.storage import ContextStorage
from backend.context_bank.versioning import VersionManager
from backend.core.exceptions import VersionNotFoundError, ContextNotFoundError, UnauthorizedAccessError
from backend.schemas.contexts import (
    VersionResponse,
    VersionCompareResponse,
    RestoreVersionRequest,
    ContextResponse,
)

router = APIRouter(prefix="/api/v1/contexts/{context_id}/versions", tags=["Versioning"])


@router.get("", response_model=List[VersionResponse])
def list_versions(
    context_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all version snapshots for a context in descending order."""
    ContextStorage.get_context(db, context_id, current_user.id)
    versions = VersionManager.list_versions(db, context_id)
    return versions


@router.get("/{version_id}", response_model=VersionResponse)
def get_version(
    context_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get snapshot data for a specific version."""
    ContextStorage.get_context(db, context_id, current_user.id)
    try:
        return VersionManager.get_version(db, context_id, version_id)
    except VersionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/compare/diff", response_model=VersionCompareResponse)
def compare_versions(
    context_id: str,
    v1: int = Query(..., description="First version number"),
    v2: int = Query(..., description="Second version number"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare two versions field by field."""
    ContextStorage.get_context(db, context_id, current_user.id)
    try:
        diff = VersionManager.compare_versions(db, context_id, v1, v2)
        return VersionCompareResponse(
            context_id=context_id,
            v1_number=v1,
            v2_number=v2,
            diff_fields=diff,
        )
    except VersionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post("/restore/{version_id}", response_model=VersionResponse)
def restore_version(
    context_id: str,
    version_id: str,
    payload: RestoreVersionRequest = RestoreVersionRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Restore an authorized previous version of a context.
    Creates a new version recording the restoration.
    """
    context = ContextStorage.get_context(db, context_id, current_user.id)
    try:
        new_version = VersionManager.restore_version(
            db=db,
            context=context,
            version_id=version_id,
            user_id=current_user.id,
            reason=payload.reason,
        )
        db.commit()
        db.refresh(new_version)
        return new_version
    except VersionNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
