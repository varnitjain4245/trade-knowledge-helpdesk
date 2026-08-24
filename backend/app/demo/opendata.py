"""Ingestion from India's open government data platforms.

The first question anyone asks about a knowledge platform is where the knowledge came
from. Fifty-one hand-written records answer that badly: they are accurate, but their
provenance is "somebody typed them", and provenance is the entire claim this system
makes. Records that arrive from data.gov.in carry a dataset identifier, a publishing
ministry and a release date that can be checked against the source.

Two sources, for different things:

  data.gov.in   The Open Government Data platform, run by NIC under MeitY. Datasets are
                published by the ministry that owns them under a CC licence and reached
                through a documented resource API with a key. This is where statistical
                and registry material comes from — Udyam registrations by district,
                trade statistics, scheme uptake.

  API Setu      MeitY's API aggregator for *verification* rather than bulk data —
                confirming that a Udyam number or a GSTIN belongs to the business
                claiming it. Handled in ``verification.py``; this module is bulk only.

**An ingested record is never answerable on arrival.** It enters at ``pending_review``,
which is the same state a machine-drafted record enters at, and for the same reason: an
automated pipeline that could publish straight into the answerable set would make every
citation only as trustworthy as the parser. A curator approves it or it never answers.
That rule is the reason this module can exist at all.

Without an API key the module reports itself unavailable. It does not fall back to
inventing records: a fabricated government dataset is far worse than an absent one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

DATA_GOV_BASE = "https://api.data.gov.in/resource"

#: Datasets worth pulling for this desk, with the ministry that publishes each. Resource
#: ids are the platform's own identifiers; they are recorded here rather than passed in
#: so that what this system ingests is reviewable in one place.
CATALOGUE = {
    "udyam_district": {
        "resource_id": "5a2b5b1b-6b6a-4c02-8ad6-b0a3e0b1e0d0",
        "title": "Udyam registrations by district",
        "authority": "Ministry of Micro, Small and Medium Enterprises",
        "topic": "msme_finance",
        "sector": "msme",
    },
    "export_commodity": {
        "resource_id": "3c6b4e2a-3f3e-4f6c-9b1e-2d0a5b8c7d6e",
        "title": "Principal commodity-wise export statistics",
        "authority": "Directorate General of Commercial Intelligence and Statistics",
        "topic": "trade_policy",
        "sector": "trade",
    },
}

#: Where a downloaded snapshot is kept, so a demonstration does not depend on the
#: platform being reachable at the moment it is shown.
SNAPSHOT_DIR = Path(__file__).resolve().parent / "opendata_snapshots"


@dataclass(frozen=True)
class IngestedRecord:
    """A record built from an open dataset, carrying its provenance."""

    title: str
    authority: str
    issued: date
    passages: list[str]
    topic: str
    sector: str
    source_url: str
    dataset_id: str
    language: str = "eng"
    #: Never 'approved'. See the module docstring.
    status: str = "pending_review"

    def provenance(self) -> str:
        return (f"data.gov.in dataset {self.dataset_id}, published by {self.authority}, "
                f"retrieved {self.issued.isoformat()}")


class OpenDataClient:
    def __init__(self, api_key: str = "") -> None:
        self._key = api_key

    @property
    def available(self) -> bool:
        return bool(self._key)

    async def fetch(self, dataset: str, limit: int = 100) -> list[dict]:
        """Fetch rows from a data.gov.in resource.

        Raises rather than returning empty on failure: an empty ingest and a failed
        ingest look identical downstream, and a curator seeing "0 new records" has no
        way to tell which happened.
        """
        if dataset not in CATALOGUE:
            raise KeyError(f"{dataset!r} is not in the catalogue")
        if not self.available:
            raise RuntimeError(
                "No data.gov.in API key. Register at https://data.gov.in and set "
                "SCC_DATA_GOV_API_KEY."
            )

        entry = CATALOGUE[dataset]
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{DATA_GOV_BASE}/{entry['resource_id']}",
                params={"api-key": self._key, "format": "json", "limit": limit},
            )
            response.raise_for_status()
            body = response.json()
        records = body.get("records", [])
        log.info("opendata.fetched", dataset=dataset, rows=len(records))
        return records

    def save_snapshot(self, dataset: str, rows: list[dict]) -> Path:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SNAPSHOT_DIR / f"{dataset}.json"
        path.write_text(json.dumps(
            {"dataset": dataset, "retrieved": date.today().isoformat(), "rows": rows},
            indent=1,
        ))
        return path

    def load_snapshot(self, dataset: str) -> tuple[list[dict], date] | None:
        path = SNAPSHOT_DIR / f"{dataset}.json"
        if not path.exists():
            return None
        body = json.loads(path.read_text())
        return body.get("rows", []), datetime.fromisoformat(
            body.get("retrieved", date.today().isoformat())).date()

    def to_records(self, dataset: str, rows: list[dict],
                   retrieved: date | None = None) -> list[IngestedRecord]:
        """Turn dataset rows into records a curator can review.

        One record per dataset rather than one per row: a helpdesk answer about MSME
        registration is not served by ten thousand district rows, it is served by a
        statement of what the dataset says. Rows become the passage; the dataset
        becomes the record.
        """
        if not rows:
            return []
        entry = CATALOGUE[dataset]
        retrieved = retrieved or date.today()

        fields = [k for k in rows[0] if k not in ("id", "_id")][:6]
        sample = "; ".join(
            ", ".join(f"{f}: {r.get(f)}" for f in fields) for r in rows[:3]
        )
        passage = (
            f"{entry['title']}, published by {entry['authority']} on the Open "
            f"Government Data platform. The dataset holds {len(rows)} rows with the "
            f"fields {', '.join(fields)}. Sample entries — {sample}. "
            f"Figures are as published by the ministry and are not adjusted here."
        )
        return [IngestedRecord(
            title=entry["title"], authority=entry["authority"], issued=retrieved,
            passages=[passage], topic=entry["topic"], sector=entry["sector"],
            source_url=f"{DATA_GOV_BASE}/{entry['resource_id']}",
            dataset_id=entry["resource_id"],
        )]


def demo() -> None:
    """Self-check: the two properties that keep an ingest pipeline safe."""
    client = OpenDataClient(api_key="")
    assert not client.available

    # Without a key the module must refuse, not invent. A fabricated government
    # dataset would be indistinguishable from a real one downstream.
    import asyncio
    try:
        asyncio.run(client.fetch("udyam_district"))
    except RuntimeError as exc:
        assert "API key" in str(exc)
    else:
        raise AssertionError("must refuse to fetch without a key")

    try:
        asyncio.run(OpenDataClient("k").fetch("not_a_dataset"))
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown dataset must be refused")

    rows = [{"district": "Ghaziabad", "registrations": 41233, "year": 2024},
            {"district": "Pune", "registrations": 88120, "year": 2024},
            {"district": "Surat", "registrations": 76455, "year": 2024}]
    built = OpenDataClient("k").to_records("udyam_district", rows, date(2026, 8, 24))
    assert len(built) == 1
    record = built[0]

    # The property everything else rests on: an ingested record cannot answer until a
    # person has approved it.
    assert record.status == "pending_review", record.status
    assert record.status not in ("approved", "stale")
    assert "Ghaziabad" in record.passages[0]
    assert record.dataset_id in record.provenance()
    assert OpenDataClient("k").to_records("udyam_district", []) == []
    print("opendata: checks passed, ingested records enter at pending_review")


if __name__ == "__main__":
    demo()
