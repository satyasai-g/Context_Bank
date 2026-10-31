from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.database.models import Context, ContextVersion
from backend.core.exceptions import VersionNotFoundError


class VersionManager:
    """
    Manages snapshots, version history, comparisons, and restoration.
    """

    @staticmethod
    def snapshot_context_data(context: Context) -> Dict[str, Any]:
        """Serialize context fields into an immutable snapshot dict."""
        return {
            "id": context.id,
            "title": context.title,
            "summary": context.summary,
            "detailed_content": context.detailed_content,
            "status": context.status,
            "category": context.category,
            "tags": list(context.tags or []),
            "important_decisions": list(context.important_decisions or []),
            "completed_work": list(context.completed_work or []),
            "open_questions": list(context.open_questions or []),
            "next_steps": list(context.next_steps or []),
            "source_references": list(context.source_references or []),
            "privacy": context.privacy,
            "updated_at": context.updated_at.isoformat() if context.updated_at else None,
        }

    @staticmethod
    def create_version(
        db: Session,
        context: Context,
        change_summary: str,
        user_id: Optional[str] = None,
    ) -> ContextVersion:
        """Create a new version snapshot for the context."""
        # Get highest existing version number
        latest_ver = db.query(ContextVersion).filter(
            ContextVersion.context_id == context.id
        ).order_by(ContextVersion.version_number.desc()).first()

        next_version_num = (latest_ver.version_number + 1) if latest_ver else 1

        snapshot = VersionManager.snapshot_context_data(context)

        version = ContextVersion(
            context_id=context.id,
            version_number=next_version_num,
            snapshot_data=snapshot,
            change_summary=change_summary,
            created_at=datetime.now(timezone.utc),
            created_by=user_id or context.user_id,
        )
        db.add(version)
        db.flush()
        return version

    @staticmethod
    def list_versions(db: Session, context_id: str) -> List[ContextVersion]:
        """List all versions for a context in descending order."""
        return db.query(ContextVersion).filter(
            ContextVersion.context_id == context_id
        ).order_by(ContextVersion.version_number.desc()).all()

    @staticmethod
    def get_version(db: Session, context_id: str, version_id: str) -> ContextVersion:
        """Get a specific version by its version UUID."""
        ver = db.query(ContextVersion).filter(
            ContextVersion.id == version_id,
            ContextVersion.context_id == context_id,
        ).first()
        if not ver:
            raise VersionNotFoundError(context_id, version_id)
        return ver

    @staticmethod
    def compare_versions(
        db: Session, context_id: str, v1_num: int, v2_num: int
    ) -> Dict[str, Dict[str, Any]]:
        """Compare two versions field by field."""
        ver1 = db.query(ContextVersion).filter(
            ContextVersion.context_id == context_id,
            ContextVersion.version_number == v1_num,
        ).first()
        ver2 = db.query(ContextVersion).filter(
            ContextVersion.context_id == context_id,
            ContextVersion.version_number == v2_num,
        ).first()

        if not ver1 or not ver2:
            raise VersionNotFoundError(context_id, f"v{v1_num} or v{v2_num}")

        s1 = ver1.snapshot_data
        s2 = ver2.snapshot_data

        diff: Dict[str, Dict[str, Any]] = {}
        all_keys = set(s1.keys()).union(set(s2.keys()))

        for key in all_keys:
            val1 = s1.get(key)
            val2 = s2.get(key)
            if val1 != val2:
                diff[key] = {"v1": val1, "v2": val2}

        return diff

    @staticmethod
    def restore_version(
        db: Session,
        context: Context,
        version_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> ContextVersion:
        """
        Restore context to snapshot in version_id and record a new version documenting the restore.
        """
        target_ver = VersionManager.get_version(db, context.id, version_id)
        snapshot = target_ver.snapshot_data

        # Restore context fields
        context.title = snapshot.get("title", context.title)
        context.summary = snapshot.get("summary", context.summary)
        context.detailed_content = snapshot.get("detailed_content", context.detailed_content)
        context.status = snapshot.get("status", context.status)
        context.category = snapshot.get("category", context.category)
        context.tags = snapshot.get("tags", context.tags)
        context.important_decisions = snapshot.get("important_decisions", context.important_decisions)
        context.completed_work = snapshot.get("completed_work", context.completed_work)
        context.open_questions = snapshot.get("open_questions", context.open_questions)
        context.next_steps = snapshot.get("next_steps", context.next_steps)
        context.source_references = snapshot.get("source_references", context.source_references)
        context.privacy = snapshot.get("privacy", context.privacy)
        context.updated_at = datetime.now(timezone.utc)

        db.flush()

        change_summary = f"Restored from version {target_ver.version_number}"
        if reason:
            change_summary += f": {reason}"

        # Create new version reflecting restoration
        new_ver = VersionManager.create_version(
            db=db,
            context=context,
            change_summary=change_summary,
            user_id=user_id,
        )
        return new_ver
