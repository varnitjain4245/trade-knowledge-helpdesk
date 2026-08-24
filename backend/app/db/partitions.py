"""Monthly range partitions for the high-volume tables.

Retention (NFR Compliance, amendment §O) is executed as a partition DROP, never a mass
DELETE: dropping is O(1) and idempotent, whereas deleting hundreds of millions of rows
under load is the operation that turns a retention job into an outage.

Called by the retention job and at deployment to pre-create the next months.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection

#: Partitioned tables and the column each is ranged on.
PARTITIONED: dict[str, str] = {
    "conversation": "started_at",
    "message": "created_at",
    "answer_record": "created_at",
    "gap_entry": "created_at",
    "audit_record": "occurred_at",
}


def _bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def partition_name(table: str, year: int, month: int) -> str:
    return f"{table}_p{year:04d}{month:02d}"


def ensure_partition(conn: Connection, table: str, year: int, month: int) -> str:
    """Create one monthly partition if absent. Idempotent by ``IF NOT EXISTS``."""
    if table not in PARTITIONED:
        raise ValueError(f"{table!r} is not partitioned")
    name = partition_name(table, year, month)
    start, end = _bounds(year, month)
    conn.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {name} PARTITION OF {table} "
            f"FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')"
        )
    )
    return name


def ensure_upcoming(conn: Connection, today: date, months_ahead: int = 3) -> list[str]:
    """Pre-create partitions so a month boundary never fails an insert.

    Three months ahead by default: a partition created only at the boundary is a
    scheduled outage waiting for the job that creates it to fail.
    """
    created: list[str] = []
    year, month = today.year, today.month
    for _ in range(months_ahead + 1):
        for table in PARTITIONED:
            created.append(ensure_partition(conn, table, year, month))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return created


def drop_partitions_before(conn: Connection, table: str, cutoff: date) -> list[str]:
    """Drop whole partitions that end at or before ``cutoff``.

    Returns the names dropped. A partition that is only partly older than the cutoff is
    left alone — dropping it would erase data still inside the retention window, which
    is a worse failure than retaining a few extra weeks.
    """
    rows = conn.execute(
        text(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_inherits i ON i.inhrelid = c.oid
            JOIN pg_class p ON p.oid = i.inhparent
            WHERE p.relname = :table
            """
        ),
        {"table": table},
    ).scalars().all()

    dropped: list[str] = []
    for name in rows:
        suffix = name.rsplit("_p", 1)[-1]
        if len(suffix) != 6 or not suffix.isdigit():
            continue
        year, month = int(suffix[:4]), int(suffix[4:])
        _, end = _bounds(year, month)
        if end <= cutoff:
            conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
            dropped.append(name)
    return dropped
