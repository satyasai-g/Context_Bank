import pytest
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.context_bank.storage import ContextStorage
from backend.schemas.contexts import ContextCreate
from backend.core.exceptions import (
    TriggerNotFoundError,
    TriggerAlreadyExistsError,
    ValidationDomainError,
)


def test_trigger_normalization_and_exact_match(db, user_a):
    """Test that triggers normalize case and whitespace and resolve accurately."""
    ctx_data = ContextCreate(
        trigger_word="  voxcent  ",
        title="Voxcent Project",
        summary="Voice learning assistant.",
    )
    context, trig = ContextStorage.create_context(db, user_a.id, ctx_data)

    # Trigger should be normalized uppercase
    assert trig.trigger_word == "VOXCENT"

    # Resolving with mixed case and whitespace should resolve to VOXCENT
    res1 = TriggerRegistry.resolve_exact_trigger(db, user_a.id, "voxcent")
    assert res1.context_id == context.id

    res2 = TriggerRegistry.resolve_exact_trigger(db, user_a.id, "  VOXCENT  ")
    assert res2.context_id == context.id

    # Missing trigger should raise TriggerNotFoundError
    with pytest.raises(TriggerNotFoundError):
        TriggerRegistry.resolve_exact_trigger(db, user_a.id, "NONEXISTENT")


def test_duplicate_trigger_in_same_user_namespace(db, user_a):
    """Test that the same user cannot register the same trigger twice."""
    ctx1 = ContextCreate(trigger_word="SQLPATH", title="SQL Course 1", summary="Basics")
    ContextStorage.create_context(db, user_a.id, ctx1)

    ctx2 = ContextCreate(trigger_word="sqlpath", title="SQL Course 2", summary="Advanced")
    with pytest.raises(TriggerAlreadyExistsError):
        ContextStorage.create_context(db, user_a.id, ctx2)


def test_same_trigger_different_users_allowed(db, user_a, user_b):
    """Test that two different users CAN have the identical trigger name in their own namespaces."""
    ctx1 = ContextCreate(trigger_word="RESUME", title="User A Resume", summary="Experience of A")
    c1, t1 = ContextStorage.create_context(db, user_a.id, ctx1)

    ctx2 = ContextCreate(trigger_word="RESUME", title="User B Resume", summary="Experience of B")
    c2, t2 = ContextStorage.create_context(db, user_b.id, ctx2)

    # Both resolve their own context without conflict
    res_a = TriggerRegistry.resolve_exact_trigger(db, user_a.id, "RESUME")
    res_b = TriggerRegistry.resolve_exact_trigger(db, user_b.id, "RESUME")

    assert res_a.context_id == c1.id
    assert res_b.context_id == c2.id
    assert res_a.user_id == user_a.id
    assert res_b.user_id == user_b.id


def test_trigger_renaming(db, user_a):
    """Test renaming an existing trigger."""
    ctx = ContextCreate(trigger_word="OLD_NAME", title="Test Renaming", summary="Summary")
    c, t = ContextStorage.create_context(db, user_a.id, ctx)

    renamed = TriggerRegistry.rename_trigger(db, user_a.id, "OLD_NAME", "NEW_NAME")
    assert renamed.trigger_word == "NEW_NAME"

    # Old trigger should no longer exist
    with pytest.raises(TriggerNotFoundError):
        TriggerRegistry.resolve_exact_trigger(db, user_a.id, "OLD_NAME")

    # New trigger should resolve
    resolved = TriggerRegistry.resolve_exact_trigger(db, user_a.id, "NEW_NAME")
    assert resolved.context_id == c.id


def test_trigger_aliases(db, user_a):
    """Test adding alternative triggers (aliases) and removing them."""
    ctx = ContextCreate(
        trigger_word="AIPROJECT",
        alternative_triggers=["AI_SPEC", "AI_DEV"],
        title="AI Project",
        summary="Detailed AI context",
    )
    c, t = ContextStorage.create_context(db, user_a.id, ctx)

    # Primary and both aliases should all resolve to the same context
    assert TriggerRegistry.resolve_exact_trigger(db, user_a.id, "AIPROJECT").context_id == c.id
    assert TriggerRegistry.resolve_exact_trigger(db, user_a.id, "AI_SPEC").context_id == c.id
    assert TriggerRegistry.resolve_exact_trigger(db, user_a.id, "AI_DEV").context_id == c.id

    # Remove one alias
    TriggerRegistry.remove_alias(db, user_a.id, "AI_SPEC")
    with pytest.raises(TriggerNotFoundError):
        TriggerRegistry.resolve_exact_trigger(db, user_a.id, "AI_SPEC")

    # Other triggers still work
    assert TriggerRegistry.resolve_exact_trigger(db, user_a.id, "AIPROJECT").context_id == c.id
