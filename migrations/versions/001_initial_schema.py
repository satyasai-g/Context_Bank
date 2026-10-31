"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-28 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("api_key_hash", sa.String(length=64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_api_key_hash", "users", ["api_key_hash"])

    # 2. Contexts
    op.create_table(
        "contexts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("detailed_content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Active"),
        sa.Column("category", sa.String(length=100), nullable=False, server_default="General"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("important_decisions", sa.JSON(), nullable=False),
        sa.Column("completed_work", sa.JSON(), nullable=False),
        sa.Column("open_questions", sa.JSON(), nullable=False),
        sa.Column("next_steps", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("privacy", sa.String(length=50), nullable=False, server_default="private"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_contexts_title", "contexts", ["title"])
    op.create_index("ix_contexts_user_id", "contexts", ["user_id"])
    op.create_index("idx_contexts_user_status", "contexts", ["user_id", "status"])
    op.create_index("idx_contexts_user_category", "contexts", ["user_id", "category"])

    # 3. Context Triggers
    op.create_table(
        "context_triggers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context_id", sa.String(length=36), sa.ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_word", sa.String(length=100), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "trigger_word", name="uq_user_trigger"),
    )
    op.create_index("ix_context_triggers_trigger_word", "context_triggers", ["trigger_word"])
    op.create_index("idx_triggers_user_word", "context_triggers", ["user_id", "trigger_word"])

    # 4. Context Versions
    op.create_table(
        "context_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("context_id", sa.String(length=36), sa.ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("context_id", "version_number", name="uq_context_version"),
    )
    op.create_index("idx_versions_context_num", "context_versions", ["context_id", "version_number"])

    # 5. Context Relationships
    op.create_table(
        "context_relationships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_context_id", sa.String(length=36), sa.ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_context_id", sa.String(length=36), sa.ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False, server_default="related_to"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_context_id", "target_context_id", name="uq_context_rel"),
    )

    # 6. Context Access Logs
    op.create_table(
        "context_access_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("context_id", sa.String(length=36), sa.ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_used", sa.String(length=100), nullable=True),
        sa.Column("accessed_via", sa.String(length=50), nullable=False, server_default="exact_trigger"),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_access_logs_timestamp", "context_access_logs", ["timestamp"])

    # 7. Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context_id", sa.String(length=36), sa.ForeignKey("contexts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("context_access_logs")
    op.drop_table("context_relationships")
    op.drop_table("context_versions")
    op.drop_table("context_triggers")
    op.drop_table("contexts")
    op.drop_table("users")
