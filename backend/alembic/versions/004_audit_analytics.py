"""Audit, answers, gaps, analytics, privacy.

Revision ID: 004
Revises: 003
Implements lld-backend-pass1 §2.3 (answer_record) and pass 3 §2.2.

Four tables here are partitioned monthly. That is not premature optimisation: audit is
retained 3 years and written on every answer, reply and access refusal, so it becomes
the largest table in the system within the first year and is the first thing that would
make REQ-012's 10-second analytics target fail.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

EMBEDDING_DIMS = 1024


def upgrade() -> None:
    op.execute(
        "CREATE TYPE answer_outcome AS ENUM "
        "('answered','no_answer','conflict','blocked_coverage','blocked_fair_use')"
    )
    op.execute(
        "CREATE TYPE gap_cause AS ENUM ('no_match','below_bar','grounding_failed',"
        "'conflict','rated_unhelpful','edited_before_send')"
    )
    op.execute(
        "CREATE TYPE gap_resolution AS ENUM ('open','resolved_with_item',"
        "'retrieval_failure','out_of_domain','pending_external')"
    )

    op.execute(
        """
        CREATE TABLE answer_record (
            id              UUID        NOT NULL,
            conversation_id UUID,
            -- Masked before write (pass 3 §6.5). The live transcript in `message` is
            -- NOT masked; this is a derived store, and REQ-015 draws the line there.
            query_text      TEXT        NOT NULL,
            query_language  CHAR(3)     NOT NULL,
            answer_language CHAR(3),
            outcome         answer_outcome NOT NULL,
            -- Exactly what was shown, not what would be shown today. Reconstructing
            -- from citations is impossible after an edit, and REQ-014 asks what the
            -- customer was actually told.
            answer_text     TEXT,
            confidence      NUMERIC(4,3),
            stale_sources   BOOLEAN     NOT NULL DEFAULT FALSE,
            generation      BIGINT      NOT NULL,
            latency_ms      INTEGER     NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )
    op.execute("CREATE INDEX idx_answer_conv ON answer_record (conversation_id, created_at)")
    op.execute("CREATE INDEX idx_answer_outcome_day ON answer_record (outcome, created_at)")

    op.create_table(
        "answer_citation",
        sa.Column("answer_id", sa.Uuid, primary_key=True),
        sa.Column("chunk_id", sa.BigInteger, sa.ForeignKey("chunk.id"), primary_key=True),
        sa.Column("item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id"), nullable=False),
        sa.Column("rank", sa.SmallInteger, nullable=False),
        sa.Column("rerank_score", sa.Numeric(6, 4), nullable=False),
    )
    # Serves: "which conversations cited this item" — required by BR-12's
    # mid-conversation retirement flagging and by the Pass 3 audit read.
    op.create_index("idx_answer_citation_item", "answer_citation", ["item_id"])

    op.create_table(
        "gap_group",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("centroid", Vector(EMBEDDING_DIMS), nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("entry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("language_spread", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("resolution", sa.Enum(name="gap_resolution", create_type=False), nullable=False, server_default="open"),
        sa.Column("resolved_item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id")),
        sa.Column("resolution_owner", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("resolved_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "resolution <> 'resolved_with_item' OR resolved_item_id IS NOT NULL",
            name="ck_resolution_complete",
        ),
        # REQ-011: pending_external stays visible in reporting, and a thing nobody owns
        # is not pending, it is forgotten.
        sa.CheckConstraint(
            "resolution <> 'pending_external' OR resolution_owner IS NOT NULL",
            name="ck_pending_has_owner",
        ),
    )
    # Serves: the ranked actionable queue. Partial, so resolved groups leave the hot
    # index — REQ-011 says a resolved group stops counting as an open gap.
    op.execute(
        "CREATE INDEX idx_gap_group_open ON gap_group (entry_count DESC) "
        "WHERE resolution = 'open'"
    )
    op.execute(
        "CREATE INDEX idx_gap_group_centroid ON gap_group USING hnsw "
        "(centroid vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    op.execute(
        """
        CREATE TABLE gap_entry (
            id              BIGINT GENERATED ALWAYS AS IDENTITY,
            group_id        BIGINT      REFERENCES gap_group(id),
            conversation_id UUID,
            answer_id       UUID,
            query_text      TEXT        NOT NULL,
            query_language  CHAR(3)     NOT NULL,
            cause           gap_cause   NOT NULL,
            embedding       VECTOR(1024),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )
    # Serves: the hourly clustering job, which only ever looks at unclustered entries.
    op.execute("CREATE INDEX idx_gap_ungrouped ON gap_entry (created_at) WHERE group_id IS NULL")
    op.execute("CREATE INDEX idx_gap_group_fk ON gap_entry (group_id)")

    op.execute(
        """
        CREATE TABLE audit_record (
            id              BIGINT GENERATED ALWAYS AS IDENTITY,
            action          TEXT        NOT NULL,
            actor_user_id   BIGINT      REFERENCES app_user(id),
            actor_kind      TEXT        NOT NULL,
            subject_type    TEXT        NOT NULL,
            subject_id      TEXT        NOT NULL,
            detail          JSONB       NOT NULL,
            occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, occurred_at)
        ) PARTITION BY RANGE (occurred_at)
        """
    )
    # Serves: "reconstruct this conversation" and "what happened to this item" (REQ-014).
    op.execute(
        "CREATE INDEX idx_audit_subject ON audit_record (subject_type, subject_id, occurred_at DESC)"
    )
    op.execute("CREATE INDEX idx_audit_actor ON audit_record (actor_user_id, occurred_at DESC)")
    op.execute("CREATE INDEX idx_audit_action ON audit_record (action, occurred_at DESC)")

    op.create_table(
        "analytics_daily",
        sa.Column("day", sa.Date, primary_key=True),
        sa.Column("language", sa.CHAR(3), primary_key=True),
        sa.Column("surface", sa.Enum(name="conversation_surface", create_type=False), primary_key=True),
        *[
            sa.Column(name, sa.Integer, nullable=False, server_default="0")
            for name in (
                "conversations_started", "self_resolved", "agent_resolved", "abandoned",
                "callback_recorded", "answers_shown", "no_answers", "conflicts",
                "assist_suggested", "assist_accepted", "assist_edited",
                "ratings_positive", "ratings_negative", "resolution_count",
                "handover_after_failed_self_serve", "handover_direct",
            )
        ],
        sa.Column("resolution_seconds_sum", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Sums and counts, never pre-divided averages: a mean of daily means is simply wrong,
    # and storing numerator and denominator separately makes every period exact.

    op.create_table(
        "analytics_gap_day",
        sa.Column("day", sa.Date, primary_key=True),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    # Records which days HAVE been computed. Its absence is how a missing interval gets
    # named instead of silently averaged across (REQ-012).

    op.create_table(
        "masking_check",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("sampled_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sample_size", sa.Integer, nullable=False),
        sa.Column("misses_found", sa.Integer, nullable=False),
        sa.Column("checked_by", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("notes", sa.Text),
        sa.CheckConstraint("sample_size > 0", name="ck_sample_nonempty"),
        sa.CheckConstraint("misses_found >= 0", name="ck_misses_nonneg"),
        sa.CheckConstraint("misses_found <= sample_size", name="ck_misses_within_sample"),
    )
    # The evidence artefact behind the >=98% recall claim. A claim with no stored
    # measurement is an assertion; this table makes it auditable.

    op.create_table(
        "deletion_request",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("customer_key_hash", sa.LargeBinary, nullable=False),
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("requester_note", sa.Text, nullable=False),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("executed_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("conversations_removed", sa.Integer),
        sa.Column("gap_entries_removed", sa.Integer),
        sa.Column("items_retained", sa.Integer),
    )

    # Idempotency keys (lld-backend.md §4.1). Stops a retried upload creating a duplicate
    # that then trips the near-duplicate flow and wastes a manager's time.
    op.create_table(
        "idempotency_key",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("actor_user_id", sa.BigInteger, primary_key=True),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("response_body", sa.JSON, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_idempotency_created", "idempotency_key", ["created_at"])


def downgrade() -> None:
    for table in ("idempotency_key", "deletion_request", "masking_check", "analytics_gap_day",
                  "analytics_daily", "audit_record", "gap_entry", "gap_group",
                  "answer_citation", "answer_record"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for enum in ("gap_resolution", "gap_cause", "answer_outcome"):
        op.execute(f"DROP TYPE {enum}")
