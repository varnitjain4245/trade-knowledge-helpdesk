# API Contract Design — Production-Ready Auto-Serving OpenAPI / Swagger

Every HTTP/REST-exposed service boundary on this platform (order gateway, risk service, settlement service, trading APIs) requires a production-grade OpenAPI (Swagger) contract and **auto-bootstrapped interactive Swagger UI**.

## 1. Zero-Config Auto-Serving Swagger UI

Whenever a backend service is built, scaffolded, or modified:
- **Swagger UI starts automatically** when the backend starts.
- **Zero manual configuration by the user**: Middleware, routes, and annotation handlers are generated into the codebase automatically.
- **Standard Endpoint Routes**:
  - Node / Express / Fastify / Nest: `/docs` or `/swagger`
  - Python / FastAPI / Django / Flask: `/docs` or `/swagger`
  - Go / Gin / Echo / Chi: `/swagger/index.html` or `/docs`
  - Rust / Axum / Actix / Poem: `/swagger-ui` or `/docs`
  - Java / Spring Boot: `/swagger-ui/index.html` or `/v3/api-docs`

---

## 2. Complete Production-Grade OpenAPI Specification Rules

Every generated OpenAPI document and code annotation set must comprehensively specify:

### General Metadata & Servers
- `title`, `description`, `version`, and `servers` list (local, staging, production URLs).

### Authentication & Security Schemes
- Global and operation-level `security` declarations (JWT Bearer Token, OAuth2 flows, API Keys).
- Standardized `401 Unauthorized` and `403 Forbidden` response schemas.

### Operations & Endpoints
Every operation must include:
- `operationId`: Stable, camelCase verb-noun identifier (`submitLimitOrder`, `getAccountPositions`).
- `summary` & `description`: Clear description of business logic and constraints.
- `tags`: Grouped logically by domain (e.g. `Orders`, `Positions`, `Risk`, `Account`).
- `parameters`: Query parameters, path parameters, header parameters (with pagination `page`/`limit`, filtering, sorting fields).
- `requestBody`: Full schema validation, `required` flags, content types (`application/json`, `multipart/form-data` for file uploads).
- `responses`: Documented status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `422 Unprocessable Entity`, `500 Internal Server Error`).
- `examples`: Concrete, realistic success and error payload examples for every endpoint.

### Data Schemas & Trading Precision
- Reusable schemas in `components/schemas` referenced via `$ref`.
- **Trading Precision**: Monetary and volume values use `type: string` with explicit decimal format specifications (`"142.50"`), never floating-point numbers.
- Explicit `enum` declarations for order types (`LIMIT`, `MARKET`), sides (`BUY`, `SELL`), and statuses (`PENDING`, `FILLED`, `CANCELLED`).
- RFC 3339 / ISO 8601 timestamps (`format: date-time`).

---

## 3. Language & Framework Auto-Bootstrapping Directives

### Rust (Axum / Actix-web / Poem)
- Auto-generate annotations using `utoipa` + `utoipa-swagger-ui` or `poem-openapi`.
- Mount Swagger UI route automatically on server initialization.

### Go (Gin / Echo / Chi)
- Auto-generate OpenAPI spec via `swag` annotations (e.g. `@Summary`, `@Param`, `@Success`, `@Failure`, `@Router`).
- Auto-mount `http-swagger` or `echo-swagger` handlers.

### Java (Spring Boot)
- Include `springdoc-openapi-starter-webmvc-ui` dependency.
- Auto-configure OpenAPI `OpenAPI` bean with SecurityScheme definitions.

### Node.js / TypeScript (Express / NestJS)
- NestJS: Use `@nestjs/swagger` `SwaggerModule.setup('docs', app, document)`.
- Express: Auto-generate spec with `swagger-jsdoc` and serve via `swagger-ui-express` on `/docs`.

### Python (FastAPI / DRF)
- FastAPI: Native auto-serving at `/docs` with custom `openapi()` schema enrichment for security and examples.

---

## 4. OpenAPI Review Checklist
- [ ] Swagger UI route (`/swagger` or `/docs`) mounts and serves automatically on backend start.
- [ ] Every operation includes `summary`, `description`, `tags`, `operationId`, and explicit `responses`.
- [ ] JWT/Bearer security schemes defined and attached to protected endpoints.
- [ ] Price and quantity fields specified as `type: string` with decimal precision.
- [ ] Realistic success and error JSON payload examples attached to every response schema.
- [ ] Pagination, filtering, sorting, and rate-limit headers documented where applicable.
