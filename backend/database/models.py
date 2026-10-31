import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from backend.database.connection import Base


class AdaptiveVector(TypeDecorator):
    """
    Adaptive vector type:
    Uses pgvector's Vector type when dialect is postgresql,
    and fallback to standard JSON on SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(384))
            except Exception:
                return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(JSON())


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    api_key_hash = Column(String(64), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    contexts = relationship("Context", back_populates="user", cascade="all, delete-orphan")
    triggers = relationship("ContextTrigger", back_populates="user", cascade="all, delete-orphan")
    access_logs = relationship("ContextAccessLog", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")


class Context(Base):
    __tablename__ = "contexts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    detailed_content = Column(Text, nullable=True)
    status = Column(String(50), default="Active", nullable=False)
    category = Column(String(100), default="General", nullable=False, index=True)
    tags = Column(JSON, default=list, nullable=False)
    important_decisions = Column(JSON, default=list, nullable=False)
    completed_work = Column(JSON, default=list, nullable=False)
    open_questions = Column(JSON, default=list, nullable=False)
    next_steps = Column(JSON, default=list, nullable=False)
    source_references = Column(JSON, default=list, nullable=False)
    privacy = Column(String(50), default="private", nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    embedding = Column(AdaptiveVector, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="contexts")
    triggers = relationship("ContextTrigger", back_populates="context", cascade="all, delete-orphan")
    versions = relationship("ContextVersion", back_populates="context", cascade="all, delete-orphan", order_by="desc(ContextVersion.version_number)")
    access_logs = relationship("ContextAccessLog", back_populates="context", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="context", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_contexts_user_status", "user_id", "status"),
        Index("idx_contexts_user_category", "user_id", "category"),
    )


class ContextTrigger(Base):
    """
    Dedicated Trigger Registry:
    Maps normalized trigger words to Context IDs in user namespace.
    """
    __tablename__ = "context_triggers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    context_id = Column(String(36), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_word = Column(String(100), nullable=False, index=True)
    is_primary = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="triggers")
    context = relationship("Context", back_populates="triggers")

    __table_args__ = (
        UniqueConstraint("user_id", "trigger_word", name="uq_user_trigger"),
        Index("idx_triggers_user_word", "user_id", "trigger_word"),
    )


class ContextVersion(Base):
    """
    Version history snapshots for Contexts.
    """
    __tablename__ = "context_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    context_id = Column(String(36), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot_data = Column(JSON, nullable=False)
    change_summary = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    context = relationship("Context", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("context_id", "version_number", name="uq_context_version"),
        Index("idx_versions_context_num", "context_id", "version_number"),
    )


class ContextRelationship(Base):
    """
    Explicit links between contexts (e.g. related_to, depends_on).
    """
    __tablename__ = "context_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_context_id = Column(String(36), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    target_context_id = Column(String(36), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), default="related_to", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_context_id", "target_context_id", name="uq_context_rel"),
    )


class ContextAccessLog(Base):
    """
    Audit and activity log of context retrievals and access.
    """
    __tablename__ = "context_access_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    context_id = Column(String(36), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_used = Column(String(100), nullable=True)
    accessed_via = Column(String(50), default="exact_trigger", nullable=False)  # exact_trigger, semantic_search, api, ui, mcp
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="access_logs")
    context = relationship("Context", back_populates="access_logs")


class Document(Base):
    """
    Optional source documents / attachments linked to contexts.
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    context_id = Column(String(36), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="documents")
    context = relationship("Context", back_populates="documents")
