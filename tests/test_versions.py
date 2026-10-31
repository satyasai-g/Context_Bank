import pytest
from backend.context_bank.storage import ContextStorage
from backend.context_bank.versioning import VersionManager
from backend.schemas.contexts import ContextCreate, ContextUpdate


def test_version_snapshots_and_comparison(db, user_a):
    """Test version snapshot creation and field diffs."""
    data = ContextCreate(
        trigger_word="DOCS_V",
        title="Version Test Doc",
        summary="Version 1 summary",
        status="Active",
        next_steps=["Step A"],
    )
    ctx, _ = ContextStorage.create_context(db, user_a.id, data)

    # Version 1 exists
    versions = VersionManager.list_versions(db, ctx.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1

    # Update to Version 2
    ContextStorage.update_context(
        db,
        ctx.id,
        user_a.id,
        ContextUpdate(
            summary="Version 2 updated summary",
            next_steps=["Step A", "Step B"],
            change_summary="Added Step B",
        ),
    )

    versions = VersionManager.list_versions(db, ctx.id)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[1].version_number == 1

    # Compare v1 and v2
    diff = VersionManager.compare_versions(db, ctx.id, 1, 2)
    assert "summary" in diff
    assert diff["summary"]["v1"] == "Version 1 summary"
    assert diff["summary"]["v2"] == "Version 2 updated summary"
    assert "next_steps" in diff


def test_version_restoration(db, user_a):
    """Test restoring an older version creates a new version documenting the restore."""
    data = ContextCreate(
        trigger_word="RESTORE_TEST",
        title="Original Title",
        summary="Original Summary",
    )
    ctx, _ = ContextStorage.create_context(db, user_a.id, data)
    v1_id = ctx.versions[0].id

    # Change title and summary in v2
    ContextStorage.update_context(
        db, ctx.id, user_a.id, ContextUpdate(title="Modified Title", summary="Modified Summary")
    )
    assert ctx.title == "Modified Title"

    # Restore v1
    new_v = VersionManager.restore_version(db, ctx, v1_id, user_a.id, reason="Rolling back changes")

    assert ctx.title == "Original Title"
    assert ctx.summary == "Original Summary"
    assert new_v.version_number == 3
    assert "Restored from version 1" in new_v.change_summary
