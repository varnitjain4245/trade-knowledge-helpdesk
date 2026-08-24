"""Append-only grants and the maintenance role (guardrail G1).

REQ-014 requires audit immutability from every role **including administrator**. The
cheapest way to guarantee that is to never grant the capability: enforcement is the
absence of a grant, not application discipline.

Retention still needs to remove old data. It does so as a separate `scc_maintenance`
role via partition DROP — whose credentials are not present on the running host
(lld-backend.md §2.6). That separation is what stops "retention" becoming a general
delete capability held by the application.

Revision ID: 005
Revises: 004
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

#: Evidence tables. Adding a new one means adding it here, to the repository interface
#: shape, and to the test that asserts the revoke holds — all three, per guardrail G1.
APPEND_ONLY = ("audit_record", "answer_record", "answer_citation", "assist_usage")


def upgrade() -> None:
    op.execute("DO $$ BEGIN CREATE ROLE scc_app NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE ROLE scc_maintenance NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scc_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scc_app")

    for table in APPEND_ONLY:
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM scc_app")

    # assist_usage is append-only except for the rating columns, which are set once by a
    # separate path. An assist record must not be rewritten after the fact — it is
    # evidence for the wrong-answer-versus-adoption guardrail.
    op.execute("GRANT UPDATE (rating, rated_at) ON assist_usage TO scc_app")

    # Only maintenance may drop partitions, and only DDL — never row-level deletes.
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO scc_maintenance")


def downgrade() -> None:
    for table in APPEND_ONLY:
        op.execute(f"GRANT UPDATE, DELETE, TRUNCATE ON {table} TO scc_app")
