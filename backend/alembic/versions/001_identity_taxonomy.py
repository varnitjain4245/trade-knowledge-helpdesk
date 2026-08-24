"""Identity and taxonomy.

Revision ID: 001
Revises:
Implements lld-backend-pass3.md §2.2 (app_user, user_role_grant) and
lld-backend.md §2.3 (taxonomy, issuing_authority).
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('agent','knowledge_manager','supervisor','administrator')")

    op.create_table(
        "app_user",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("external_id", sa.Text, nullable=False, unique=True),
        sa.Column("display_name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("primary_language", sa.CHAR(3), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("deactivated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deactivated_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        # Deactivation is never deletion: every audit record references an actor, and a
        # deleted user would orphan the attribution REQ-014 exists to preserve.
        sa.CheckConstraint(
            "is_active OR (deactivated_at IS NOT NULL AND deactivated_by IS NOT NULL)",
            name="ck_deactivation_complete",
        ),
    )

    op.create_table(
        "user_role_grant",
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("role", sa.Enum(name="user_role", create_type=False), primary_key=True),
        sa.Column("granted_by", sa.BigInteger, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("granted_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "taxonomy_sector",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        # `code` is immutable by contract; `display_name` may be renamed freely.
        # Classifications reference id, which is what makes a rename preserve every
        # existing classification (REQ-003's last criterion).
        sa.Column("code", sa.Text, nullable=False, unique=True),
        sa.Column("display_name", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "taxonomy_topic",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("sector_id", sa.BigInteger, sa.ForeignKey("taxonomy_sector.id"), nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("display_name", sa.Text, nullable=False),
        # Feeds the REQ-023 coverage floor: every must-have topic needs an approved item
        # before the public assistant opens.
        sa.Column("is_must_have", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("sector_id", "code", name="uq_topic_sector_code"),
    )

    op.create_table(
        "issuing_authority",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("code", sa.Text, nullable=False, unique=True),
        sa.Column("display_name", sa.Text, nullable=False),
    )

    # Language enablement (amendment §G). Enabling requires an acceptance score — an
    # enablement with no recorded score is indistinguishable from ignoring REQ-001's gate.
    op.create_table(
        "language",
        sa.Column("code", sa.CHAR(3), primary_key=True),
        sa.Column("bcp47", sa.Text, nullable=False),
        sa.Column("script", sa.Text, nullable=False),
        sa.Column("display_name", sa.Text, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("acceptance_score", sa.Numeric(4, 3)),
        sa.Column("acceptance_run_id", sa.Text),
        sa.Column("enabled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("enabled_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.CheckConstraint(
            "NOT enabled OR acceptance_score IS NOT NULL", name="ck_enable_needs_score"
        ),
    )

    # Canonical ISO 639-3 -> BCP-47 + script map (amendment §D). Hindi and Marathi share
    # Devanagari, which is why the frontend's type-scale tokens key on script.
    op.execute(
        """
        INSERT INTO language (code, bcp47, script, display_name, enabled, acceptance_score) VALUES
          ('eng','en','latin','English', TRUE, 1.000),
          ('hin','hi','devanagari','हिन्दी', TRUE, 1.000),
          ('ben','bn','bengali','বাংলা', FALSE, NULL),
          ('tam','ta','tamil','தமிழ்', FALSE, NULL),
          ('tel','te','telugu','తెలుగు', FALSE, NULL),
          ('mar','mr','devanagari','मराठी', FALSE, NULL)
        """
    )

    # Runtime settings that are neither product thresholds nor deployment config:
    # the coverage-floor declaration is a recorded human judgement (REQ-023).
    op.create_table(
        "app_setting",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_by", sa.BigInteger, sa.ForeignKey("app_user.id")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("INSERT INTO app_setting (key, value) VALUES ('self_serve_open','false')")


def downgrade() -> None:
    for table in ("app_setting", "language", "issuing_authority", "taxonomy_topic",
                  "taxonomy_sector", "user_role_grant", "app_user"):
        op.drop_table(table)
    op.execute("DROP TYPE user_role")
