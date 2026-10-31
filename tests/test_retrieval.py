import pytest
from backend.context_bank.storage import ContextStorage
from backend.context_bank.retrieval import ContextRetrievalEngine
from backend.schemas.contexts import ContextCreate, DecisionItem
from backend.core.exceptions import TriggerNotFoundError


def test_exact_trigger_retrieval(db, user_a):
    """Test retrieving an AI context package via exact trigger VOXCENT."""
    data = ContextCreate(
        trigger_word="VOXCENT",
        title="AI Learning and Career Assistant",
        summary="A voice-first AI application with five specialized roles.",
        status="In Progress",
        category="Projects",
        important_decisions=[
            DecisionItem(text="Context Bank is an independent subsystem.", status="confirmed"),
            DecisionItem(text="Python is primary language.", status="confirmed"),
        ],
        next_steps=["Build context CRUD operations", "Integrate with AI client"],
    )
    ContextStorage.create_context(db, user_a.id, data)

    # 1. Retrieve exact trigger
    pkg = ContextRetrievalEngine.retrieve_by_exact_trigger(
        db=db,
        user_id=user_a.id,
        trigger_word="VOXCENT",
        detail_level="summary_and_state",
        output_format="markdown",
    )

    assert pkg.primary_trigger == "VOXCENT"
    assert pkg.title == "AI Learning and Career Assistant"
    assert "Context Bank is an independent subsystem." in pkg.package_content
    assert "Build context CRUD operations" in pkg.package_content

    # 2. Verify missing trigger throws TriggerNotFoundError
    with pytest.raises(TriggerNotFoundError):
        ContextRetrievalEngine.retrieve_by_exact_trigger(
            db=db,
            user_id=user_a.id,
            trigger_word="MISSING_TRIGGER",
        )


def test_natural_language_prompt_retrieval(db, user_a):
    """Test 'Continue VOXCENT from where I stopped.' extraction and retrieval."""
    data = ContextCreate(
        trigger_word="VOXCENT",
        title="AI Learning and Career Assistant",
        summary="Summary for VOXCENT.",
        next_steps=["Step 1", "Step 2"],
    )
    ContextStorage.create_context(db, user_a.id, data)

    prompt = "Continue VOXCENT from where I stopped."
    pkg = ContextRetrievalEngine.retrieve_by_prompt(
        db=db,
        user_id=user_a.id,
        prompt=prompt,
        detail_level="summary_and_state",
        output_format="prompt",
    )

    assert pkg.primary_trigger == "VOXCENT"
    # Ensure data fence is included in prompt format
    assert "CONTEXT BANK DATA FENCE" in pkg.package_content
    assert "<context_bank_package" in pkg.package_content


def test_retrieval_detail_levels(db, user_a):
    """Test summary_only vs detailed packages."""
    data = ContextCreate(
        trigger_word="TEST_LEVELS",
        title="Testing Levels",
        summary="Short summary.",
        detailed_content="Deep secret architecture notes that should only appear in detailed.",
    )
    ContextStorage.create_context(db, user_a.id, data)

    # summary_only should NOT have detailed_content
    pkg_summary = ContextRetrievalEngine.retrieve_by_exact_trigger(
        db=db, user_id=user_a.id, trigger_word="TEST_LEVELS", detail_level="summary_only"
    )
    assert "Deep secret architecture notes" not in pkg_summary.package_content

    # detailed SHOULD have detailed_content
    pkg_detailed = ContextRetrievalEngine.retrieve_by_exact_trigger(
        db=db, user_id=user_a.id, trigger_word="TEST_LEVELS", detail_level="detailed"
    )
    assert "Deep secret architecture notes" in pkg_detailed.package_content
