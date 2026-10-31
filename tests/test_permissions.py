import pytest
from backend.context_bank.storage import ContextStorage
from backend.context_bank.retrieval import ContextRetrievalEngine
from backend.schemas.contexts import ContextCreate, ContextUpdate
from backend.core.exceptions import UnauthorizedAccessError, ContextNotFoundError, TriggerNotFoundError


def test_user_isolation_private_context(db, user_a, user_b):
    """Ensure User B cannot retrieve User A's private context."""
    data = ContextCreate(
        trigger_word="SECRET_PROJECT",
        title="Classified Architecture",
        summary="Confidential notes.",
        privacy="private",
    )
    ctx, _ = ContextStorage.create_context(db, user_a.id, data)

    # User B tries to retrieve by exact trigger -> trigger doesn't exist in B's namespace
    with pytest.raises(TriggerNotFoundError):
        ContextRetrievalEngine.retrieve_by_exact_trigger(
            db=db,
            user_id=user_b.id,
            trigger_word="SECRET_PROJECT",
        )

    # User B tries to fetch context directly by ID -> Unauthorized
    with pytest.raises(UnauthorizedAccessError):
        ContextStorage.get_context(db, ctx.id, user_b.id)

    # User B tries to update User A's context -> Unauthorized
    with pytest.raises(UnauthorizedAccessError):
        ContextStorage.update_context(
            db, ctx.id, user_b.id, ContextUpdate(title="Hacked Title")
        )

    # User B tries to delete User A's context -> Unauthorized
    with pytest.raises(UnauthorizedAccessError):
        ContextStorage.delete_context(db, ctx.id, user_b.id)
