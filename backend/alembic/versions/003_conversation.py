"""Conversation, presence, queue, assignment.

Revision ID: 003
Revises: 002
Implements lld-backend-pass2.md §2.3. conversation and message are range-partitioned
monthly so the 12-month transcript retention is a partition DROP rather than a mass
DELETE (guardrail G1 / NFR Compliance).
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE conversation_surface AS ENUM ('self_serve','agent')")
    op.execute(
        "CREATE TYPE conversation_state AS ENUM ('active_self_serve','active_agent','queued',"
        "'assigned','escalated','self_resolved','agent_resolved','callback_recorded','abandoned')"
    )
    op.execute("CREATE TYPE message_author AS ENUM ('customer','assistant','agent')")
    op.execute("CREATE TYPE presence_state AS ENUM ('available','busy','away','offline')")
    op.execute("CREATE TYPE assignment_end AS ENUM ('resolved','released','abandoned','failed')")

    op.execute(
        """
        CREATE TABLE conversation (
            id                  UUID        NOT NULL,
            surface             conversation_surface NOT NULL,
            state               conversation_state   NOT NULL,
            detected_language   CHAR(3)     NOT NULL,
            chosen_language     CHAR(3),
            customer_token_hash BYTEA,
            -- Pseudonymous browser key (pass 3 §2.3). Links a returning customer on the
            -- SAME browser and nothing else, which is why every figure derived from it
            -- is reported as a lower bound.
            customer_key_hash   BYTEA,
            started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_activity_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at            TIMESTAMPTZ,
            end_reason          TEXT,
            -- Stored rather than derived: "two consecutive below-bar answers" is
            -- ambiguous once a customer interleaves an unrelated message (REQ-007).
            below_bar_streak    SMALLINT    NOT NULL DEFAULT 0,
            retired_source_flag BOOLEAN     NOT NULL DEFAULT FALSE,
            PRIMARY KEY (id, started_at),
            CONSTRAINT ck_terminal_has_end CHECK (
                state NOT IN ('self_resolved','agent_resolved','callback_recorded','abandoned')
                OR ended_at IS NOT NULL
            )
        ) PARTITION BY RANGE (started_at)
        """
    )
    # Serves: the inactivity sweep. Partial, so it stays small as terminal rows accumulate.
    op.execute(
        "CREATE INDEX idx_conv_active_inactivity ON conversation (last_activity_at) "
        "WHERE state IN ('active_self_serve','active_agent','queued','assigned')"
    )
    op.execute("CREATE INDEX idx_conv_state_started ON conversation (state, started_at DESC)")
    # Serves: the repeat-contact guardrail (a lower bound, by construction).
    op.execute(
        "CREATE INDEX idx_conv_customer_key ON conversation (customer_key_hash, started_at DESC) "
        "WHERE customer_key_hash IS NOT NULL"
    )

    op.execute(
        """
        CREATE TABLE message (
            id              BIGINT GENERATED ALWAYS AS IDENTITY,
            conversation_id UUID        NOT NULL,
            author          message_author NOT NULL,
            agent_id        BIGINT      REFERENCES app_user(id),
            body            TEXT        NOT NULL,
            language        CHAR(3)     NOT NULL,
            answer_id       UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT ck_agent_attribution CHECK ((author = 'agent') = (agent_id IS NOT NULL))
        ) PARTITION BY RANGE (created_at)
        """
    )
    op.execute("CREATE INDEX idx_message_conv ON message (conversation_id, created_at)")

    op.create_table(
        "agent_presence",
        sa.Column("agent_id", sa.BigInteger, sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("state", sa.Enum(name="presence_state", create_type=False), nullable=False, server_default="offline"),
        sa.Column("last_heartbeat", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        # AS-P2-1: one conversation per agent at MVP. If that assumption falls, this
        # becomes a count against a capacity limit and the locking stays as it is.
        sa.Column("current_conversation_id", sa.Uuid),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Serves: candidate selection. Partial index keeps it to agents who can take work.
    op.execute(
        "CREATE INDEX idx_presence_available ON agent_presence (state, last_heartbeat) "
        "WHERE state = 'available'"
    )

    op.create_table(
        "agent_language",
        sa.Column("agent_id", sa.BigInteger, sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("language", sa.CHAR(3), sa.ForeignKey("language.code"), primary_key=True),
    )

    op.create_table(
        "queue_entry",
        sa.Column("conversation_id", sa.Uuid, primary_key=True),
        sa.Column("language", sa.CHAR(3), nullable=False),
        sa.Column("enqueued_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("attempts", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("escalated", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    # Serves: FIFO selection. Deliberately no priority column — REQ-008 specifies no
    # priority scheme, and inventing one has real fairness consequences.
    op.execute("CREATE INDEX idx_queue_fifo ON queue_entry (enqueued_at) WHERE escalated = FALSE")

    op.create_table(
        "assignment",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("conversation_id", sa.Uuid, nullable=False),
        sa.Column("agent_id", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("language_matched", sa.Boolean, nullable=False),
        sa.Column("wait_seconds", sa.Integer, nullable=False),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("end_state", sa.Enum(name="assignment_end", create_type=False)),
    )
    op.create_index("idx_assignment_conv", "assignment", ["conversation_id", sa.text("assigned_at DESC")])
    # Serves: "is this agent actually free" — the authoritative answer, against which
    # agent_presence is only an advisory fast path (pass 2 §7.2).
    op.execute("CREATE INDEX idx_assignment_agent_open ON assignment (agent_id) WHERE ended_at IS NULL")

    op.create_table(
        "assist_usage",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("conversation_id", sa.Uuid, nullable=False),
        sa.Column("agent_id", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("answer_id", sa.Uuid, nullable=False),
        sa.Column("accepted", sa.Boolean, nullable=False),
        # Server-determined, never the client's claim: a lying client would corrupt the
        # REQ-014 audit trail and the wrong-answer guardrail at once.
        sa.Column("edited_before_send", sa.Boolean),
        sa.Column("sent_message_id", sa.BigInteger),
        sa.Column("rating", sa.SmallInteger),
        sa.Column("rated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("rating IS NULL OR rating IN (-1, 1)", name="ck_rating_values"),
    )
    op.create_index("idx_assist_answer", "assist_usage", ["answer_id"])
    op.create_index("idx_assist_agent_created", "assist_usage", ["agent_id", sa.text("created_at DESC")])

    op.create_table(
        "callback_request",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("conversation_id", sa.Uuid, nullable=False, unique=True),
        # Personal data (AS-P2-4): masked on read everywhere except the agent working it.
        sa.Column("contact_detail", sa.Text, nullable=False),
        sa.Column("language", sa.CHAR(3), nullable=False),
        sa.Column("promised_window", sa.Text, nullable=False),
        sa.Column("fulfilled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("fulfilled_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX idx_callback_open ON callback_request (created_at) WHERE fulfilled_at IS NULL")


def downgrade() -> None:
    for table in ("callback_request", "assist_usage", "assignment", "queue_entry",
                  "agent_language", "agent_presence", "message", "conversation"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for enum in ("assignment_end", "presence_state", "message_author",
                 "conversation_state", "conversation_surface"):
        op.execute(f"DROP TYPE {enum}")
