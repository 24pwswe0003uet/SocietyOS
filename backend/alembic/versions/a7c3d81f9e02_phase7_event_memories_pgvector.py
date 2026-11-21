"""Phase 7: event_memories table for semantic retrieval.

Uses pgvector (Vector column + HNSW index) when available,
falls back to JSONB storage with Python-side similarity when not.

Revision ID: a7c3d81f9e02
Revises: bec41ca3af34
Create Date: 2026-11-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a7c3d81f9e02"
down_revision: str = "bec41ca3af34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_pgvector(connection) -> bool:
    """Check if pgvector extension is available."""
    try:
        result = connection.execute(sa.text(
            "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
        ))
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    connection = op.get_bind()
    use_pgvector = _has_pgvector(connection)

    if use_pgvector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create verification status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE verification_status_enum AS ENUM ('unverified', 'verified', 'disputed', 'excluded');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Build column list — embedding column depends on pgvector availability
    columns = [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("event_records.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("event_outcomes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("universities.id"), nullable=False),
        sa.Column("society_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_title", sa.String(500), nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("lessons", postgresql.JSONB, nullable=True),
        sa.Column("risk_flags", postgresql.JSONB, nullable=True),
        sa.Column("success_factors", postgresql.JSONB, nullable=True),
        sa.Column("budget_variance_pct", sa.Float, nullable=True),
        sa.Column("attendance_variance_pct", sa.Float, nullable=True),
        sa.Column("sponsor_conversion_rate", sa.Float, nullable=True),
        sa.Column("approval_days", sa.Integer, nullable=True),
    ]

    if use_pgvector:
        from pgvector.sqlalchemy import Vector
        columns.append(sa.Column("embedding", Vector(768), nullable=False))
    else:
        # Fallback: store embedding as JSONB array
        columns.append(sa.Column("embedding", postgresql.JSONB, nullable=False))

    columns.extend([
        sa.Column("verification_status",
                  postgresql.ENUM("unverified", "verified", "disputed", "excluded",
                                  name="verification_status_enum", create_type=False),
                  nullable=False, server_default="unverified"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    ])

    op.create_table("event_memories", *columns)

    # Indexes
    op.create_index("ix_event_memories_event_id", "event_memories", ["event_id"])
    op.create_index("ix_event_memories_outcome_id", "event_memories", ["outcome_id"])
    op.create_index("ix_event_memories_university_id", "event_memories", ["university_id"])
    op.create_index("ix_event_memories_society_id", "event_memories", ["society_id"])
    op.create_index("ix_event_memories_event_type", "event_memories", ["event_type"])
    op.create_index("ix_event_memories_is_active", "event_memories", ["is_active"])

    # HNSW index only if pgvector available
    if use_pgvector:
        op.execute("""
            CREATE INDEX ix_event_memories_embedding_hnsw
            ON event_memories
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

    # Add verification columns to event_outcomes
    op.add_column("event_outcomes",
                  sa.Column("is_verified", sa.Boolean, server_default="false", nullable=False))
    op.add_column("event_outcomes",
                  sa.Column("verified_by", postgresql.UUID(as_uuid=True),
                            sa.ForeignKey("users.id"), nullable=True))
    op.add_column("event_outcomes",
                  sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("event_outcomes", "verified_at")
    op.drop_column("event_outcomes", "verified_by")
    op.drop_column("event_outcomes", "is_verified")
    op.drop_table("event_memories")
    op.execute("DROP TYPE IF EXISTS verification_status_enum")
