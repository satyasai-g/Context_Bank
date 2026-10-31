import pytest
from backend.context_bank.storage import ContextStorage
from backend.schemas.contexts import ContextCreate, ContextUpdate, DecisionItem
from backend.core.exceptions import ContextNotFoundError


def test_create_and_read_context(db, user_a):
    """Test full context creation with structured decisions and next steps."""
    data = ContextCreate(
        trigger_word="VOXCENT",
        title="Voxcent Project",
        summary="Voice-first learning assistant.",
        detailed_content="Full architecture doc here.",
        category="Projects",
        status="In Progress",
        tags=["voice", "fastapi"],
        important_decisions=[
            DecisionItem(text="Python 3 is chosen", status="confirmed"),
            DecisionItem(text="Consider WebRTC", status="proposed"),
        ],
        completed_work=["Auth flow built", "Database schema defined"],
        open_questions=["Which STT model to use?"],
        next_steps=["Setup WebSocket stream", "Write tests"],
    )

    context, trigger = ContextStorage.create_context(db, user_a.id, data)
    assert context.id is not None
    assert context.title == "Voxcent Project"
    assert len(context.important_decisions) == 2
    assert len(context.completed_work) == 2
    assert len(context.next_steps) == 2

    # Read back
    fetched = ContextStorage.get_context(db, context.id, user_a.id)
    assert fetched.id == context.id
    assert fetched.summary == "Voice-first learning assistant."


def test_update_context(db, user_a):
    """Test updating fields and recording version history."""
    data = ContextCreate(trigger_word="DOCS", title="Documentation", summary="Initial")
    ctx, _ = ContextStorage.create_context(db, user_a.id, data)

    update_data = ContextUpdate(
        summary="Updated documentation summary",
        status="Completed",
        next_steps=["Publish docs online"],
        change_summary="Finalized docs",
    )
    updated = ContextStorage.update_context(db, ctx.id, user_a.id, update_data)

    assert updated.summary == "Updated documentation summary"
    assert updated.status == "Completed"
    assert updated.next_steps == ["Publish docs online"]
    assert len(updated.versions) == 2  # Initial + Update


def test_delete_context_policy(db, user_a):
    """Test that deleting a context removes all associated triggers so they don't remain active."""
    data = ContextCreate(trigger_word="TEMPORARY", title="Temp Project", summary="To delete")
    ctx, trig = ContextStorage.create_context(db, user_a.id, data)

    ctx_id = ctx.id
    ContextStorage.delete_context(db, ctx_id, user_a.id)

    # Context should be gone
    with pytest.raises(ContextNotFoundError):
        ContextStorage.get_context(db, ctx_id, user_a.id)

    # Trigger should no longer resolve
    from backend.context_bank.trigger_registry import TriggerRegistry
    from backend.core.exceptions import TriggerNotFoundError

    with pytest.raises(TriggerNotFoundError):
        TriggerRegistry.resolve_exact_trigger(db, user_a.id, "TEMPORARY")
