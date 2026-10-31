from sqlalchemy.orm import Session
from backend.core.exceptions import UnauthorizedAccessError, ContextNotFoundError
from backend.database.models import Context


def verify_context_ownership(db: Session, context_id: str, user_id: str) -> Context:
    """
    Ensure the context exists and belongs to the given user.
    Enforces strict user isolation.
    """
    context = db.query(Context).filter(Context.id == context_id).first()
    if not context:
        raise ContextNotFoundError(context_id)

    if context.user_id != user_id:
        # Check if shared read-only
        if context.privacy == "shared":
            return context
        raise UnauthorizedAccessError(f"context '{context_id}'")

    return context


def verify_context_write_permission(db: Session, context_id: str, user_id: str) -> Context:
    """
    Ensure user has write permission on the context (must be owner).
    """
    context = db.query(Context).filter(Context.id == context_id).first()
    if not context:
        raise ContextNotFoundError(context_id)

    if context.user_id != user_id:
        raise UnauthorizedAccessError(f"context '{context_id}' (modification requires ownership)")

    return context
