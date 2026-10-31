from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.database.models import Context, ContextTrigger, ContextAccessLog
from backend.core.exceptions import TriggerNotFoundError, ContextNotFoundError
from backend.context_bank.trigger_registry import TriggerRegistry
from backend.context_bank.context_packager import ContextPackager
from backend.context_bank.permissions import verify_context_ownership
from backend.schemas.retrieval import ContextPackageResponse


class ContextRetrievalEngine:
    """
    Retrieval Engine:
    Handles exact trigger retrieval and natural language trigger extraction.
    Strictly isolated by user_id.
    """

    @staticmethod
    def retrieve_by_exact_trigger(
        db: Session,
        user_id: str,
        trigger_word: str,
        detail_level: str = "summary_and_state",
        output_format: str = "markdown",
        accessed_via: str = "exact_trigger",
    ) -> ContextPackageResponse:
        """
        Primary feature: Retrieve context using exact registered trigger.
        Raises TriggerNotFoundError if no exact match exists.
        Never silently falls back to unrelated semantic search.
        """
        # 1. Resolve exact trigger
        trigger_record = TriggerRegistry.resolve_exact_trigger(
            db=db,
            user_id=user_id,
            trigger_word=trigger_word,
            record_access=True,
        )

        # 2. Retrieve Context
        context = verify_context_ownership(db, trigger_record.context_id, user_id)

        # 3. Update Context last_accessed_at
        now = datetime.now(timezone.utc)
        context.last_accessed_at = now

        # 4. Record access audit log
        log_entry = ContextAccessLog(
            context_id=context.id,
            user_id=user_id,
            trigger_used=trigger_record.trigger_word,
            accessed_via=accessed_via,
            timestamp=now,
        )
        db.add(log_entry)
        db.flush()

        # 5. Package context for client
        package_content = ContextPackager.package(
            context=context,
            trigger=trigger_record.trigger_word,
            detail_level=detail_level,
            output_format=output_format,
        )
        structured_data = ContextPackager.to_structured_dict(
            context=context,
            trigger=trigger_record.trigger_word,
            detail_level=detail_level,
        )

        return ContextPackageResponse(
            context_id=context.id,
            primary_trigger=trigger_record.trigger_word,
            title=context.title,
            summary=context.summary,
            status=context.status,
            detail_level=detail_level,
            output_format=output_format,
            package_content=package_content,
            structured_data=structured_data,
            retrieved_at=now,
            retrieved_via=accessed_via,
        )

    @staticmethod
    def retrieve_by_prompt(
        db: Session,
        user_id: str,
        prompt: str,
        detail_level: str = "summary_and_state",
        output_format: str = "prompt",
    ) -> ContextPackageResponse:
        """
        Resolve trigger inside a natural language prompt such as:
        'Continue VOXCENT from where I stopped.'
        """
        user_triggers = TriggerRegistry.list_user_triggers(db, user_id)
        trigger_words = [t.trigger_word for t in user_triggers]

        matched_trigger = ContextPackager.extract_trigger_from_prompt(prompt, trigger_words)
        if not matched_trigger:
            raise TriggerNotFoundError(f"prompt '{prompt}' (no registered trigger recognized)")

        return ContextRetrievalEngine.retrieve_by_exact_trigger(
            db=db,
            user_id=user_id,
            trigger_word=matched_trigger,
            detail_level=detail_level,
            output_format=output_format,
            accessed_via="prompt_retrieval",
        )
