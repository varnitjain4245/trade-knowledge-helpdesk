"""Application settings.

Guardrail G6 defines two tiers of tunables:

* **Tier 1 — product thresholds** that gate a stated requirement. These live in the
  ``threshold`` database table and are changed through an audited endpoint, not here.
  See ``app.services.thresholds``.
* **Tier 2 — operational tunables** that change by deployment. Those are the ones in
  this module.

Nothing that a person may need to change in production is a code constant. If a value
below turns out to gate a requirement, it belongs in tier 1 instead.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # --- Environment -----------------------------------------------------------------
    environment: Literal["local", "staging", "production"] = "local"
    api_origin: str = "http://localhost:8000"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Data stores -----------------------------------------------------------------
    database_url: PostgresDsn = "postgresql+psycopg://scc:scc@localhost:5432/scc"  # type: ignore[assignment]
    redis_url: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]
    database_path: str = "data/scc.db"
    """Accounts, preferences and question history.

    SQLite because this is a single-process deployment and a file is the honest fit. The
    schema is written as it would be for PostgreSQL, so moving is a migration rather than
    a rewrite.
    """
    # --- Bhashini (MeitY National Language Translation Mission) -----------------------
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""
    bhashini_pipeline_id: str = ""
    """Credentials from bhashini.gov.in. Empty means the client reports itself
    unavailable and speech falls back to the browser's own recognition, which covers
    fewer languages and only in some browsers. The desk must work without a key."""

    # --- Open government data and verification ---------------------------------------
    data_gov_api_key: str = ""
    """Key from data.gov.in. Absent, ingestion refuses rather than inventing records."""
    apisetu_api_key: str = ""
    apisetu_client_id: str = ""
    """API Setu credentials for Udyam and GSTIN verification. Absent, a well-formed
    number reports as 'unavailable' — never as verified, and never as invalid."""

    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "scc-documents"

    # --- Model runtime ---------------------------------------------------------------
    embedding_endpoint: str = "http://localhost:8080"
    embedding_model_tag: str = "bge-m3@v1"
    embedding_dimensions: int = 1024
    rerank_endpoint: str = "http://localhost:8081"
    generation_endpoint: str = "http://localhost:8082"
    generation_enabled: bool = True
    generation_provider: Literal["extractive", "vllm", "groq"] = "extractive"
    """Which generation strategy is bound.

    ``extractive`` is the default and the only one that keeps every byte of query and
    document content on the operator's host. ``groq`` sends both to a third party and
    therefore breaches the Cost & data-control requirement — it exists for demonstration
    and must be turned on deliberately (guardrail G4 does not apply to a choice the
    operator makes with their eyes open; it applies to silent degradations).
    """
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    """When False the answer path runs extractive-only (hld-backend.md §12.5, AS-L1)."""

    # --- Deadlines, milliseconds (lld-backend.md §4.6) -------------------------------
    #
    # Two different things, and conflating them is how a p95 target quietly fails:
    #
    # * The per-stage timeouts below are *ceilings* on one stage. Each has a defined
    #   degradation, and every degradation lands on the safe side (guardrail G4).
    # * `answer_deadline_ms` is the ceiling on the WHOLE request. The stage budgets in
    #   §4.6 sum to 4,300 ms, but the stage *timeouts* sum to far more — so a chain of
    #   slow-but-not-timing-out stages would exceed the 5 s p95 target with nothing to
    #   stop it. The deadline is what stops it: once it passes, the answer path takes
    #   the shortest safe exit available rather than continuing.
    #
    # This deadline is not in the LLD; it was found during implementation and is
    # recorded as an upstream gap in the Stage 8 verification report.
    answer_deadline_ms: int = 5000
    answer_deadline_public_ms: int = 8000

    timeout_detect_ms: int = 200
    timeout_embed_ms: int = 500
    timeout_retrieve_ms: int = 1000
    timeout_rerank_ms: int = 1200
    timeout_conflict_ms: int = 200
    timeout_generate_first_token_ms: int = 2000
    timeout_generate_complete_ms: int = 4000
    timeout_ground_ms: int = 500
    timeout_persist_ms: int = 1000

    # --- Tier 2 operational tunables (amendment §Q) ----------------------------------
    ingestion_max_attempts_extract: int = 3
    ingestion_max_attempts_ocr: int = 2
    ingestion_max_attempts_embed: int = 5
    ingestion_max_attempts_classify: int = 3
    queue_max_attempts: int = 5
    heartbeat_ttl_seconds: int = 60
    heartbeat_interval_seconds: int = 20
    gap_similarity_threshold: float = 0.85
    analytics_max_period_days: int = 366
    answer_cache_ttl_seconds: int = 3600
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_half_open_seconds: int = 30

    # --- Retrieval shape -------------------------------------------------------------
    retrieval_candidate_count: int = 50
    rerank_top_n: int = 8
    grounding_min_coverage: float = 0.80

    # --- Auth ------------------------------------------------------------------------
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 14
    jwt_algorithm: str = "HS256"
    jwt_secret: str = "change-me-in-deployment"
    """Loaded via systemd LoadCredential in deployment (lld-backend.md §2.6), never
    from an environment variable in a Compose file."""

    # --- Uploads ---------------------------------------------------------------------
    max_upload_bytes: int = 100 * 1024 * 1024
    allowed_upload_mime: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
        ]
    )

    # --- Languages (amendment §D) ----------------------------------------------------
    supported_languages: list[str] = Field(
        default_factory=lambda: ["eng", "hin", "ben", "tam", "tel", "mar"]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
