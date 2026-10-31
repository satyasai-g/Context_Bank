import re
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database.models import Context, ContextTrigger
from backend.services.embedding_service import EmbeddingService
from backend.schemas.retrieval import SearchResultItem, SearchResponse


class SearchService:
    """
    Semantic & Text Search Service:
    Enables exploratory searching by concept, topic, or query.
    Completely distinct from exact trigger lookup.
    """

    @classmethod
    def search(
        cls,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search_mode: str = "hybrid",
    ) -> SearchResponse:
        """
        Execute search across user's contexts.
        Returns ranked results with match reasons.
        """
        query_clean = query.strip()
        query_words = set(re.findall(r"\w+", query_clean.lower()))

        # Query contexts belonging to user
        q = db.query(Context).filter(
            Context.user_id == user_id,
            Context.is_archived == False,
        )
        if category:
            q = q.filter(Context.category == category)

        contexts = q.all()
        if not contexts:
            return SearchResponse(
                query=query_clean,
                total_results=0,
                results=[],
                search_provider_used="none",
            )

        query_vec = None
        if search_mode in ("hybrid", "vector"):
            query_vec = EmbeddingService.get_embedding(query_clean)

        scored_results: List[Tuple[Context, float, str]] = []

        for ctx in contexts:
            # 1. Text match analysis
            title_lower = ctx.title.lower()
            summary_lower = ctx.summary.lower()
            content_lower = (ctx.detailed_content or "").lower()
            tags_lower = [t.lower() for t in (ctx.tags or [])]

            matched_terms = []
            text_score = 0.0

            for word in query_words:
                if len(word) <= 2:
                    continue
                in_title = word in title_lower
                in_summary = word in summary_lower
                in_tags = any(word in t for t in tags_lower)
                in_content = word in content_lower

                if in_title:
                    text_score += 0.4
                    matched_terms.append(f"'{word}' in title")
                elif in_summary:
                    text_score += 0.3
                    matched_terms.append(f"'{word}' in summary")
                elif in_tags:
                    text_score += 0.25
                    matched_terms.append(f"'{word}' in tags")
                elif in_content:
                    text_score += 0.15
                    matched_terms.append(f"'{word}' in detailed content")

            # 2. Vector similarity
            vec_score = 0.0
            if query_vec and ctx.embedding:
                try:
                    vec_score = EmbeddingService.cosine_similarity(query_vec, ctx.embedding)
                except Exception:
                    vec_score = 0.0

            # 3. Calculate final score and reason
            if search_mode == "vector":
                final_score = vec_score
                reason = f"Semantic similarity: {vec_score:.2f}"
            elif search_mode == "text":
                final_score = min(text_score, 1.0)
                reason = f"Keyword match: {', '.join(matched_terms[:3])}" if matched_terms else "Text relevance"
            else:  # hybrid
                final_score = 0.4 * min(text_score, 1.0) + 0.6 * vec_score
                reasons = []
                if matched_terms:
                    reasons.append(f"Matched {', '.join(matched_terms[:2])}")
                if vec_score > 0.3:
                    reasons.append(f"Semantic match ({vec_score:.2f})")
                reason = "; ".join(reasons) if reasons else "Topic contextual match"

            if final_score > 0.05 or matched_terms:
                scored_results.append((ctx, final_score, reason))

        # Sort descending by score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_results[:limit]

        # Convert to response items
        items = []
        for ctx, score, reason in top_results:
            # Get primary trigger
            primary_trig = db.query(ContextTrigger).filter(
                ContextTrigger.context_id == ctx.id,
                ContextTrigger.is_primary == True,
            ).first()
            trig_name = primary_trig.trigger_word if primary_trig else "NONE"

            items.append(
                SearchResultItem(
                    context_id=ctx.id,
                    primary_trigger=trig_name,
                    title=ctx.title,
                    summary=ctx.summary,
                    category=ctx.category,
                    tags=ctx.tags or [],
                    relevance_score=round(float(score), 3),
                    match_reason=reason,
                )
            )

        provider = "hybrid (embeddings + keyword index)"
        return SearchResponse(
            query=query_clean,
            total_results=len(items),
            results=items,
            search_provider_used=provider,
        )
