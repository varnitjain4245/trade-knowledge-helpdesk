"""Knowledge core.

Revision ID: 002
Revises: 001
Implements lld-backend.md §2.3. Every index carries the query it serves — an index
without a stated query is an index nobody can safely drop later.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

EMBEDDING_DIMS = 1024  # bge-m3; a model change is a re-embed, never a silent mix.


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "CREATE TYPE knowledge_status AS ENUM ('processing','failed','duplicate_hold',"
        "'pending_review','approved','stale','retired','rejected','superseded')"
    )
    op.execute(
        "CREATE TYPE knowledge_source_type AS ENUM "
        "('document','manual_entry','ticket_export','crawled_page')"
    )
    op.execute(
        "CREATE TYPE classification_source AS ENUM "
        "('proposed','human_confirmed','human_corrected','manual')"
    )
    op.execute(
        "CREATE TYPE ingestion_stage AS ENUM ('queued','extracting','ocr','metadata',"
        "'duplicate_check','chunking','embedding','classifying','complete','failed')"
    )

    op.create_table(
        "source_document",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("object_key", sa.Text, nullable=False, unique=True),
        sa.Column("original_name", sa.Text, nullable=False),
        sa.Column("mime_type", sa.Text, nullable=False),
        sa.Column("byte_size", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.LargeBinary, nullable=False),
        sa.Column("uploaded_by", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("byte_size > 0", name="ck_document_nonempty"),
    )
    # Serves: exact-duplicate short-circuit before the expensive near-duplicate check.
    op.create_index("idx_source_document_sha", "source_document", ["sha256"])

    op.create_table(
        "knowledge_item",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("status", sa.Enum(name="knowledge_status", create_type=False), nullable=False),
        sa.Column("source_type", sa.Enum(name="knowledge_source_type", create_type=False), nullable=False),
        sa.Column("source_document_id", sa.Uuid, sa.ForeignKey("source_document.id")),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("language", sa.CHAR(3), sa.ForeignKey("language.code"), nullable=False),
        sa.Column("issuing_authority_id", sa.BigInteger, sa.ForeignKey("issuing_authority.id")),
        sa.Column("issued_on", sa.Date),
        sa.Column("review_due_on", sa.Date),
        sa.Column("supersedes_id", sa.Uuid, sa.ForeignKey("knowledge_item.id")),
        sa.Column("superseded_by_id", sa.Uuid, sa.ForeignKey("knowledge_item.id")),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("submitted_by", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("approved_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("status_reason", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        # BR-11: an approved item always has an approver, a time and a review date.
        sa.CheckConstraint(
            "status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL "
            "AND review_due_on IS NOT NULL)",
            name="ck_approved_completeness",
        ),
        # BR-2: a citable item must be able to produce a complete citation. This is the
        # database half of the guarantee that no answer can cite an incomplete source.
        sa.CheckConstraint(
            "status NOT IN ('approved','stale') OR "
            "(issuing_authority_id IS NOT NULL AND issued_on IS NOT NULL)",
            name="ck_citable_completeness",
        ),
        sa.CheckConstraint(
            "status NOT IN ('rejected','retired') OR status_reason IS NOT NULL",
            name="ck_reason_required",
        ),
        sa.CheckConstraint("supersedes_id IS DISTINCT FROM id", name="ck_no_self_supersede"),
    )

    # Serves: the retrieval filter. Partial, so it stays small as retired items accumulate.
    op.execute(
        "CREATE INDEX idx_ki_answerable ON knowledge_item (status) "
        "WHERE status IN ('approved','stale')"
    )
    # Serves: the daily staleness sweep and REQ-010's "due within 30 days" list.
    op.execute(
        "CREATE INDEX idx_ki_review_due ON knowledge_item (review_due_on) "
        "WHERE status IN ('approved','stale')"
    )
    # Serves: supersession-chain walk (A superseded by B superseded by C).
    op.execute(
        "CREATE INDEX idx_ki_superseded_by ON knowledge_item (superseded_by_id) "
        "WHERE superseded_by_id IS NOT NULL"
    )
    # Serves: the curation console's default list view.
    op.create_index("idx_ki_status_updated", "knowledge_item", ["status", sa.text("updated_at DESC")])

    op.create_table(
        "knowledge_item_version",
        sa.Column("item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id"), primary_key=True),
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("issuing_authority_id", sa.BigInteger),
        sa.Column("issued_on", sa.Date),
        sa.Column("edited_by", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("edited_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("change_note", sa.Text),
    )
    # Full snapshot per version, not a diff: reconstructing "what did this say when it
    # was cited" by replaying diffs is not worth the risk on an evidence path.

    op.create_table(
        "chunk",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_version", sa.Integer, nullable=False),
        sa.Column("ordinal", sa.Integer, nullable=False),
        # 'Chapter 3 > 3.2 Licensing' — a clause split from its heading is an uncitable
        # chunk, so heading context travels with the passage (BR-2).
        sa.Column("heading_path", sa.Text),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("char_start", sa.Integer, nullable=False),
        sa.Column("char_end", sa.Integer, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.UniqueConstraint("item_id", "item_version", "ordinal", name="uq_chunk_ordinal"),
    )
    # 'simple' rather than 'english': the corpus is six languages, and applying English
    # stemming rules to Tamil text is worse than no stemming at all.
    op.execute(
        "ALTER TABLE chunk ADD COLUMN lexeme TSVECTOR "
        "GENERATED ALWAYS AS (to_tsvector('simple', body)) STORED"
    )
    # Serves: the lexical leg of hybrid search — notification numbers, tariff codes.
    op.execute("CREATE INDEX idx_chunk_lexeme ON chunk USING GIN (lexeme)")
    op.create_index("idx_chunk_item", "chunk", ["item_id", "item_version"])

    op.create_table(
        "chunk_embedding",
        sa.Column("chunk_id", sa.BigInteger, sa.ForeignKey("chunk.id", ondelete="CASCADE"), primary_key=True),
        # Denormalised on purpose: lets the hot retrieval query filter on item status with
        # one join instead of two. Costs 16 bytes per chunk on a path that runs per query.
        sa.Column("item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_tag", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMS), nullable=False),
    )
    op.execute(
        "CREATE INDEX idx_chunk_embedding_hnsw ON chunk_embedding "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    op.create_table(
        "item_classification",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.BigInteger, sa.ForeignKey("taxonomy_topic.id"), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("source", sa.Enum(name="classification_source", create_type=False), nullable=False),
        sa.Column("decided_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True)),
        # REQ-003 allows multiple topics, but not the same topic twice.
        sa.UniqueConstraint("item_id", "topic_id", name="uq_classification"),
    )
    # Serves: the REQ-023 coverage-floor check.
    op.create_index("idx_classification_topic", "item_classification", ["topic_id"])

    op.create_table(
        "ingestion_job",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("item_id", sa.Uuid, sa.ForeignKey("knowledge_item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.Enum(name="ingestion_stage", create_type=False), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_stage", sa.Enum(name="ingestion_stage", create_type=False)),
        sa.Column("failure_reason", sa.Text),
        sa.Column("dead_lettered", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Serves: the curation console's processing view and the dead-letter surface.
    op.execute("CREATE INDEX idx_ingestion_open ON ingestion_job (stage) WHERE stage <> 'complete'")

    op.create_table(
        "threshold",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("updated_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Tier 1 (guardrail G6): every value here gates a stated requirement, so each change
    # is audited. Change history lives in audit_record, not duplicated in this table.
    op.execute(
        """
        INSERT INTO threshold (name, value) VALUES
          ('answer_bar', 0.70),
          ('classification_bar', 0.60),
          ('low_volume_threshold', 100),
          ('gap_group_size', 5),
          ('masking_min_confidence', 0.85),
          ('inactivity_boundary_minutes', 15),
          ('fair_use_per_hour', 30)
        """
    )

    # Exactly one row. Bumped inside the same transaction as any approval, edit,
    # retirement or supersession — which is what makes cache invalidation atomic and
    # closes hld-review High-1.
    op.create_table(
        "knowledge_generation",
        sa.Column("id", sa.Boolean, primary_key=True, server_default=sa.true()),
        sa.Column("generation", sa.BigInteger, nullable=False, server_default="1"),
        sa.CheckConstraint("id", name="ck_single_generation_row"),
    )
    op.execute("INSERT INTO knowledge_generation (id, generation) VALUES (TRUE, 1)")


def downgrade() -> None:
    for table in ("knowledge_generation", "threshold", "ingestion_job", "item_classification",
                  "chunk_embedding", "chunk", "knowledge_item_version", "knowledge_item",
                  "source_document"):
        op.drop_table(table)
    for enum in ("ingestion_stage", "classification_source", "knowledge_source_type", "knowledge_status"):
        op.execute(f"DROP TYPE {enum}")
