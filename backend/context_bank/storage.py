from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from backend.database.models import Context, ContextTrigger, ContextRelationship, ContextAccessLog
from backend.core.exceptions import ContextNotFoundError, ValidationDomainError
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.context_bank.versioning import VersionManager
from backend.context_bank.permissions import verify_context_ownership, verify_context_write_permission
from backend.schemas.contexts import ContextCreate, ContextUpdate


class ContextStorage:
    """
    Core Context Storage operations: CRUD, relationships, and lifecycle.
    """

    @staticmethod
    def create_context(
        db: Session,
        user_id: str,
        data: ContextCreate,
    ) -> Tuple[Context, ContextTrigger]:
        """
        Create a new context with primary trigger and initial version snapshot.
        Enforces atomic transaction.
        """
        # 1. Create Context record
        context = Context(
            user_id=user_id,
            title=data.title.strip(),
            summary=data.summary.strip(),
            detailed_content=data.detailed_content or "",
            status=data.status,
            category=data.category,
            tags=data.tags or [],
            important_decisions=[d.model_dump() for d in data.important_decisions],
            completed_work=data.completed_work or [],
            open_questions=data.open_questions or [],
            next_steps=data.next_steps or [],
            source_references=[s.model_dump() for s in data.source_references],
            privacy=data.privacy,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(context)
        db.flush()

        # 2. Register Primary Trigger
        primary_trigger = TriggerRegistry.register_trigger(
            db=db,
            user_id=user_id,
            context_id=context.id,
            trigger_word=data.trigger_word,
            is_primary=True,
        )

        # 3. Register Alternative Triggers (Aliases)
        for alt in (data.alternative_triggers or []):
            if alt != data.trigger_word:
                TriggerRegistry.add_alias(
                    db=db,
                    user_id=user_id,
                    context_id=context.id,
                    alias_word=alt,
                )

        # 4. Link Related Contexts if any
        for rel_id in (data.related_context_ids or []):
            if rel_id != context.id:
                rel = ContextRelationship(
                    source_context_id=context.id,
                    target_context_id=rel_id,
                    relationship_type="related_to",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(rel)

        # 5. Create Initial Version Snapshot
        VersionManager.create_version(
            db=db,
            context=context,
            change_summary="Initial context creation",
            user_id=user_id,
        )

        db.flush()
        return context, primary_trigger

    @staticmethod
    def get_context(db: Session, context_id: str, user_id: str) -> Context:
        """Retrieve context verifying access."""
        return verify_context_ownership(db, context_id, user_id)

    @staticmethod
    def update_context(
        db: Session,
        context_id: str,
        user_id: str,
        data: ContextUpdate,
    ) -> Context:
        """Update context details and create a new version snapshot."""
        context = verify_context_write_permission(db, context_id, user_id)

        if data.title is not None:
            context.title = data.title.strip()
        if data.summary is not None:
            context.summary = data.summary.strip()
        if data.detailed_content is not None:
            context.detailed_content = data.detailed_content
        if data.status is not None:
            context.status = data.status
        if data.category is not None:
            context.category = data.category
        if data.tags is not None:
            context.tags = data.tags
        if data.important_decisions is not None:
            context.important_decisions = [d.model_dump() for d in data.important_decisions]
        if data.completed_work is not None:
            context.completed_work = data.completed_work
        if data.open_questions is not None:
            context.open_questions = data.open_questions
        if data.next_steps is not None:
            context.next_steps = data.next_steps
        if data.source_references is not None:
            context.source_references = [s.model_dump() for s in data.source_references]
        if data.privacy is not None:
            context.privacy = data.privacy
        if data.is_archived is not None:
            context.is_archived = data.is_archived

        context.updated_at = datetime.now(timezone.utc)
        db.flush()

        # Capture Version Snapshot
        change_desc = data.change_summary or "Updated context fields"
        VersionManager.create_version(
            db=db,
            context=context,
            change_summary=change_desc,
            user_id=user_id,
        )

        db.flush()
        return context

    @staticmethod
    def delete_context(db: Session, context_id: str, user_id: str) -> None:
        """
        Delete context and all associated triggers, versions, relationships, and logs.
        Enforces deletion policy so deleted contexts cannot remain accessible through active triggers.
        """
        context = verify_context_write_permission(db, context_id, user_id)
        db.delete(context)
        db.flush()

    @staticmethod
    def list_contexts(
        db: Session,
        user_id: str,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        is_archived: bool = False,
        sort_by: str = "updated_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Context], int]:
        """List contexts for user with filtering, sorting, and pagination."""
        query = db.query(Context).filter(
            Context.user_id == user_id,
            Context.is_archived == is_archived,
        )

        if category:
            query = query.filter(Context.category == category)
        if status:
            query = query.filter(Context.status == status)

        # Sorting
        if sort_by == "updated_desc":
            query = query.order_by(desc(Context.updated_at))
        elif sort_by == "created_desc":
            query = query.order_by(desc(Context.created_at))
        elif sort_by == "accessed_desc":
            query = query.order_by(desc(Context.last_accessed_at.nulls_last()))
        elif sort_by == "title_asc":
            query = query.order_by(asc(Context.title))
        else:
            query = query.order_by(desc(Context.updated_at))

        total = query.count()
        offset = (page - 1) * page_size
        contexts = query.offset(offset).limit(page_size).all()

        # If tag filter is specified, filter in memory if JSON contains tag
        if tag:
            filtered = [c for c in contexts if tag in (c.tags or [])]
            return filtered, len(filtered)

        return contexts, total

    @staticmethod
    def link_relationship(
        db: Session,
        user_id: str,
        source_id: str,
        target_id: str,
        rel_type: str = "related_to",
        notes: Optional[str] = None,
    ) -> ContextRelationship:
        """Link two contexts explicitly."""
        verify_context_write_permission(db, source_id, user_id)
        verify_context_ownership(db, target_id, user_id)

        existing = db.query(ContextRelationship).filter(
            ContextRelationship.source_context_id == source_id,
            ContextRelationship.target_context_id == target_id,
        ).first()

        if existing:
            existing.relationship_type = rel_type
            existing.notes = notes
            db.flush()
            return existing

        rel = ContextRelationship(
            source_context_id=source_id,
            target_context_id=target_id,
            relationship_type=rel_type,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rel)
        db.flush()
        return rel
