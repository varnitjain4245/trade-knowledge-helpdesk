---
title: "Tech Stack — Smart Contact-Center Knowledge Platform"
stage: 3a
skill: backend-hld-architect
scope: fullstack
version: "1.0"
note: "Backend portion written at Stage 3a. Frontend portion appended at Stage 3b."
---

# Tech Stack

Every choice below traces to a constraint in `hld-backend.md` §1. Where a choice is not obvious, the rejected alternative is named.

## Backend Portion (Stage 3a)

### Runtime and API

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| Language | Python 3.12 | User decision; also the only ecosystem where the embedding, reranking, OCR and PII components are first-class rather than bindings | Node.js — would have forced a second Python service for the AI pipeline, i.e. the split we avoided |
| API framework | FastAPI + Uvicorn | Async I/O suits a workload dominated by waiting on model calls; native SSE support for §16; typed request models reduce the Stage 5a-to-Stage 8 drift the workflow's review stage looks for | Django — heavier, and its synchronous ORM fights an inference-bound workload |
| Task queue | Celery with a Redis broker | Boring, well-understood, survives worker restarts mid-document | Custom asyncio workers — cheaper to write, worse to operate when a 200-page OCR job dies halfway |
| Process manager | systemd units per process (API, worker, model server) | Single VM; no orchestrator needed to run three processes | Kubernetes — §4's rejected-alternatives reasoning applies |

### Data

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| Primary store | PostgreSQL 16 | Governance, versioning and audit must commit in one transaction (HLD §8) | Separate document store — creates the answerable-but-unaudited window |
| Vector index | pgvector with HNSW | 50k items is well inside its range; keeps embeddings transactionally consistent with the status column that decides answerability (HLD §8 invariant) | Qdrant/Weaviate — a second store to keep in sync for capability this scale does not need. Trigger to revisit is in HLD §26 |
| Lexical search | PostgreSQL full-text search | Needed for notification numbers and tariff codes (HLD §13); already present, no new component | Elasticsearch — an entire cluster for one hybrid-search leg |
| Cache / queue / rate limit | Redis 7 | Ephemeral, rebuildable; nothing here is a source of truth | In-process cache — breaks the moment a second Uvicorn worker exists |
| Object storage | MinIO (S3-compatible) on the VM volume | Keeps large immutable documents out of the transactional store while retaining the S3 interface, so moving to real S3 later is a config change | Filesystem paths — works, but bakes a migration in |
| Migrations | Alembic | Standard with SQLAlchemy; the review at Stage 9 can diff schema against the Stage 5a LLD | — |

### Models — all freely licensed, all self-hosted

| Role | Choice | Why | Note |
|---|---|---|---|
| Multilingual embedding | BGE-M3 | Genuinely multilingual and trained for cross-language retrieval, which is what REQ-001 needs; handles long passages | Alternative if it underperforms per-language: multilingual-e5-large. Per-language measurement is required before enablement either way (HLD T-2) |
| Reranker | bge-reranker-v2-m3 | Cross-encoder precision is what makes the confidence signal meaningful (HLD §12.3) | — |
| Generator | Llama 3.1 8B Instruct, or Qwen2.5 7B Instruct | Both are permissively licensed, both handle Indic languages materially better than smaller options, both fit a single mid-range GPU | Pick between them by measured Indic quality on the acceptance set, not by benchmark reputation |
| Inference server | vLLM (GPU) or llama.cpp (CPU fallback) | vLLM's batching is what makes 200 concurrent conversations viable on one GPU; llama.cpp is the honest CPU-only path from HLD §12.5 | This choice is contingent on T-1 (GPU availability) |
| OCR | Tesseract with Indic language packs, PaddleOCR where Tesseract underperforms | Free, local, script coverage | Cloud OCR — breaks the data-control NFR outright |
| PII detection | Presidio with custom Indian-identifier recognisers (PAN, Aadhaar, GSTIN, IEC, phone) | Extensible rule + NER hybrid; recall-tunable, which matters because REQ-015 weights recall over precision | Regex alone — would miss names and addresses entirely |
| Language detection | fastText lid.176 | Fast, offline, covers all six launch languages | — |

**Licensing note:** every model above is usable without per-query cost, satisfying the cost constraint. Llama 3.1's community licence carries a usage-scale condition that this deployment sits far below, but it should be read once by whoever signs off, rather than assumed — Qwen2.5 (Apache 2.0) is the cleaner path if that review is unwelcome.

### Document processing

| Need | Choice |
|---|---|
| PDF text extraction | PyMuPDF — fast, keeps layout information that chunking needs for heading context |
| DOCX / XLSX | python-docx, openpyxl |
| HTML (portal pages, Phase 2) | trafilatura — extracts main content and discards navigation chrome |
| Chunking | Custom heading-aware splitter over the extracted structure, not a fixed character window — a clause split from its heading is an uncitable chunk (HLD §7) |

### Operations

| Need | Choice |
|---|---|
| Reverse proxy / TLS | Caddy — automatic certificates, terse origin-allowlist configuration for the cross-origin split (HLD §11) |
| Packaging | Docker Compose on the VM — one file describing all processes; not an orchestrator, just reproducibility |
| Logging | structlog to JSON, shipped to files with rotation |
| Metrics | Prometheus + Grafana, scraped locally |
| Error tracking | Self-hosted GlitchTip (Sentry-compatible) — a hosted error tracker would receive query text, breaching the data-control NFR |
| Backups | pgBackRest for PostgreSQL, restic for object storage |
| CI | GitHub Actions running tests and building images; deployment to the VM by pull |

### Testing

| Layer | Choice |
|---|---|
| Unit / integration | pytest with pytest-asyncio |
| API contract | schemathesis against the generated OpenAPI schema — catches Stage 8 drift from the Stage 5a LLD automatically |
| Retrieval quality | A held-out acceptance question set scored per language; this is the artifact the REQ-001 enablement gate depends on, so it is test infrastructure, not a document |
| Load | Locust against the answer path, targeting 200 concurrent conversations |

## Frontend Portion (Stage 3b)

Every choice traces to a decision in `hld-frontend.md`.

### Core

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| Framework | React 18 + TypeScript | Three surfaces share the citation, confidence and language components; widest accessible-primitive ecosystem for a WCAG AA government service | Vue 3 — smaller, comparable DX, loses on a11y primitives and hiring for a full engineering org |
| Build | Vite 5, three entry points | Static output for Vercel/Netlify; per-surface bundles so a customer never downloads the agent console | Next.js — SSR strengths this system explicitly does not need (hld-frontend.md §3), and a Node tier would put query text on a third-party platform |
| Routing | React Router 6 (data routers) | Route-level splitting and role guards per surface | TanStack Router — good, but no advantage that repays a less familiar API here |
| Server state | TanStack Query | Retirement of an item must invalidate every view showing it; query-key invalidation makes that structural | Redux Toolkit Query — comparable; loses on ceremony for the small amount of genuinely global state |
| Client state | Zustand | Session, role, enabled languages, chosen language — small, global, read everywhere | Context — broad re-renders on language-set change; Redux — reducers over fetched data solve the wrong problem |
| Styling | Tailwind CSS with logical properties, plus CSS custom properties for the per-script type scale | Script-aware typography must live in the design tokens, not in per-screen fixes; logical properties make future RTL (Urdu) a config change | CSS-in-JS — runtime cost for no benefit here |
| Accessible primitives | Radix UI | Unstyled, keyboard-complete, correct ARIA — the agent console's keyboard-complete requirement is a performance requirement too | Hand-rolled — a reliable way to ship subtly inaccessible dialogs |

### Supporting

| Need | Choice | Note |
|---|---|---|
| API client | openapi-typescript + openapi-fetch, regenerated in CI | The mechanism that stops Stage 8 drifting from the Stage 5a contract |
| Streaming | Native EventSource with a typed wrapper | Matches the backend's SSE choice; the wrapper enforces the "never paint an ungrounded answer" rule (hld-frontend.md §7) |
| i18n | i18next + react-i18next, per-locale chunks | Enabled-language set fetched from the backend so a gated language never appears in the switcher |
| Fonts | Noto Sans family, subset per script, loaded on demand | Indic glyph sets are large; a Tamil user must not download Bengali glyphs |
| Virtualisation | TanStack Virtual | Agent queue and the 50,000-row curation table |
| Forms | React Hook Form + Zod | Zod schemas derived from the generated types keep client validation aligned with server contracts |
| Charts | Recharts | Analytics tiles and period comparison; small, accessible-enough with explicit labelling |
| Testing | Vitest + Testing Library, Playwright | Accessible-role queries make the a11y contract a test failure; Playwright covers the six PRD flows including error paths |
| Client error reporting | GlitchTip SDK pointed at the self-hosted instance | A hosted tracker would receive query text in breadcrumbs — forbidden by the data-control NFR |
| Hosting | Vercel or Netlify, static only | Holds no data and runs no application logic (hld-backend.md §10) |
