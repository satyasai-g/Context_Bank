from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database.connection import get_db
from backend.database.models import User, Context, ContextTrigger, ContextAccessLog
from backend.api.auth import get_current_user
from backend.core.config import settings

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations & Stats"])


@router.get("/status")
def get_system_status():
    """
    Check the status of system subsystems and integrations.
    Masks credentials.
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_type": "PostgreSQL" if settings.is_postgres else "SQLite (Local/Dev)",
        "gemini_configured": settings.gemini_available,
        "gemini_model": settings.GEMINI_MODEL if settings.gemini_available else "Not configured",
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "mcp_server_available": True,
        "auth_methods": ["Bearer JWT", "X-API-Key"],
    }


@router.get("/dashboard-stats")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve personalized dashboard metrics for authenticated user.
    Shows meaningful empty state if new user.
    """
    total_contexts = db.query(Context).filter(
        Context.user_id == current_user.id,
        Context.is_archived == False,
    ).count()

    total_triggers = db.query(ContextTrigger).filter(
        ContextTrigger.user_id == current_user.id
    ).count()

    # Recently accessed contexts
    recent_accessed = db.query(Context).filter(
        Context.user_id == current_user.id,
        Context.last_accessed_at.isnot(None),
    ).order_by(desc(Context.last_accessed_at)).limit(5).all()

    # Recently updated contexts
    recent_updated = db.query(Context).filter(
        Context.user_id == current_user.id,
        Context.is_archived == False,
    ).order_by(desc(Context.updated_at)).limit(5).all()

    # Frequently used triggers
    frequent_triggers = db.query(ContextTrigger).filter(
        ContextTrigger.user_id == current_user.id,
        ContextTrigger.access_count > 0,
    ).order_by(desc(ContextTrigger.access_count)).limit(6).all()

    # Recent activity logs
    logs = db.query(ContextAccessLog).filter(
        ContextAccessLog.user_id == current_user.id
    ).order_by(desc(ContextAccessLog.timestamp)).limit(8).all()

    # Format helpers
    def format_ctx(c: Context):
        primary_trig = db.query(ContextTrigger).filter(
            ContextTrigger.context_id == c.id,
            ContextTrigger.is_primary == True,
        ).first()
        return {
            "id": c.id,
            "title": c.title,
            "primary_trigger": primary_trig.trigger_word if primary_trig else "UNKNOWN",
            "summary": c.summary,
            "category": c.category,
            "status": c.status,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "last_accessed_at": c.last_accessed_at.isoformat() if c.last_accessed_at else None,
        }

    activity_items = []
    for log in logs:
        ctx = db.query(Context).filter(Context.id == log.context_id).first()
        activity_items.append({
            "context_id": log.context_id,
            "context_title": ctx.title if ctx else "Unknown Context",
            "trigger_used": log.trigger_used,
            "accessed_via": log.accessed_via,
            "timestamp": log.timestamp.isoformat(),
        })

    return {
        "has_data": total_contexts > 0,
        "total_contexts": total_contexts,
        "total_triggers": total_triggers,
        "recently_accessed": [format_ctx(c) for c in recent_accessed],
        "recently_updated": [format_ctx(c) for c in recent_updated],
        "frequently_used_triggers": [
            {
                "trigger_word": t.trigger_word,
                "access_count": t.access_count,
                "context_id": t.context_id,
                "last_accessed_at": t.last_accessed_at.isoformat() if t.last_accessed_at else None,
            }
            for t in frequent_triggers
        ],
        "recent_activity": activity_items,
    }
