from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.models import ContextTrigger, Context
from backend.core.exceptions import (
    TriggerNotFoundError,
    TriggerAlreadyExistsError,
    ValidationDomainError,
)
from backend.schemas.triggers import normalize_trigger_word


class TriggerRegistry:
    """
    Dedicated Trigger Registry:
    Manages trigger-to-context mappings strictly isolated by user_id.
    """

    @staticmethod
    def register_trigger(
        db: Session,
        user_id: str,
        context_id: str,
        trigger_word: str,
        is_primary: bool = False,
    ) -> ContextTrigger:
        """
        Register a trigger for a context in user's namespace.
        Raises TriggerAlreadyExistsError if already in use.
        """
        normalized = normalize_trigger_word(trigger_word)

        # Check uniqueness within user's namespace
        existing = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == user_id,
            ContextTrigger.trigger_word == normalized,
        ).first()

        if existing:
            raise TriggerAlreadyExistsError(normalized, existing.context_id)

        # If this is marked as primary, demote existing primary for this context
        if is_primary:
            db.query(ContextTrigger).filter(
                ContextTrigger.context_id == context_id,
                ContextTrigger.user_id == user_id,
                ContextTrigger.is_primary == True,
            ).update({"is_primary": False})

        new_trigger = ContextTrigger(
            user_id=user_id,
            context_id=context_id,
            trigger_word=normalized,
            is_primary=is_primary,
            created_at=datetime.now(timezone.utc),
            access_count=0,
        )
        db.add(new_trigger)
        db.flush()
        return new_trigger

    @staticmethod
    def resolve_exact_trigger(
        db: Session,
        user_id: str,
        trigger_word: str,
        record_access: bool = True,
    ) -> ContextTrigger:
        """
        Resolve exact trigger in user namespace.
        Does NOT silently fall back to semantic search.
        Raises TriggerNotFoundError if not found.
        """
        normalized = normalize_trigger_word(trigger_word)

        trigger = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == user_id,
            ContextTrigger.trigger_word == normalized,
        ).first()

        if not trigger:
            raise TriggerNotFoundError(normalized)

        if record_access:
            trigger.access_count += 1
            trigger.last_accessed_at = datetime.now(timezone.utc)
            db.flush()

        return trigger

    @staticmethod
    def rename_trigger(
        db: Session,
        user_id: str,
        old_trigger_word: str,
        new_trigger_word: str,
    ) -> ContextTrigger:
        """Rename an existing trigger to a new trigger word."""
        old_norm = normalize_trigger_word(old_trigger_word)
        new_norm = normalize_trigger_word(new_trigger_word)

        if old_norm == new_norm:
            return TriggerRegistry.resolve_exact_trigger(db, user_id, old_norm, record_access=False)

        # Ensure target name is not already registered in this user's namespace
        collision = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == user_id,
            ContextTrigger.trigger_word == new_norm,
        ).first()
        if collision:
            raise TriggerAlreadyExistsError(new_norm, collision.context_id)

        trigger = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == user_id,
            ContextTrigger.trigger_word == old_norm,
        ).first()

        if not trigger:
            raise TriggerNotFoundError(old_norm)

        trigger.trigger_word = new_norm
        db.flush()
        return trigger

    @staticmethod
    def add_alias(
        db: Session,
        user_id: str,
        context_id: str,
        alias_word: str,
    ) -> ContextTrigger:
        """Add an alternative trigger name (alias) to a context."""
        return TriggerRegistry.register_trigger(
            db=db,
            user_id=user_id,
            context_id=context_id,
            trigger_word=alias_word,
            is_primary=False,
        )

    @staticmethod
    def remove_alias(
        db: Session,
        user_id: str,
        trigger_word: str,
    ) -> None:
        """
        Remove an alias trigger.
        Cannot remove if it's the sole primary trigger.
        """
        normalized = normalize_trigger_word(trigger_word)
        trigger = db.query(ContextTrigger).filter(
            ContextTrigger.user_id == user_id,
            ContextTrigger.trigger_word == normalized,
        ).first()

        if not trigger:
            raise TriggerNotFoundError(normalized)

        if trigger.is_primary:
            # Check if there are other triggers for this context
            other = db.query(ContextTrigger).filter(
                ContextTrigger.context_id == trigger.context_id,
                ContextTrigger.id != trigger.id,
            ).first()
            if not other:
                raise ValidationDomainError(
                    f"Cannot delete primary trigger '{normalized}'. A context must retain at least one trigger."
                )
            other.is_primary = True

        db.delete(trigger)
        db.flush()

    @staticmethod
    def list_triggers_for_context(
        db: Session,
        context_id: str,
    ) -> List[ContextTrigger]:
        """List all triggers (primary and aliases) for a context."""
        return db.query(ContextTrigger).filter(
            ContextTrigger.context_id == context_id
        ).order_by(ContextTrigger.is_primary.desc(), ContextTrigger.trigger_word.asc()).all()

    @staticmethod
    def list_user_triggers(
        db: Session,
        user_id: str,
        search_prefix: Optional[str] = None,
    ) -> List[ContextTrigger]:
        """List all triggers in user's namespace."""
        query = db.query(ContextTrigger).filter(ContextTrigger.user_id == user_id)
        if search_prefix:
            norm_prefix = search_prefix.strip().upper()
            query = query.filter(ContextTrigger.trigger_word.startswith(norm_prefix))
        return query.order_by(ContextTrigger.trigger_word.asc()).all()
