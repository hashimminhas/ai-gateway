# AI-Gateway — Progress Log

## Completed Steps

### Step 1 — Project Scaffolding ✅
- Created full project directory structure
- Files created:
  - `app/__init__.py` — Flask app factory (placeholder)
  - `app/config.py` — Configuration class
  - `app/routes.py` — API routes (placeholder)
  - `app/models.py` — Database models (placeholder)
  - `app/orchestrator.py` — Multi-provider orchestration (placeholder)
  - `app/circuit_breaker.py` — Circuit breaker (placeholder)
  - `app/decision.py` — Structured decision output (placeholder)
  - `app/metrics.py` — Prometheus metrics (placeholder)
  - `app/logging_config.py` — Logging setup (placeholder)
  - `app/providers/__init__.py`
  - `app/providers/base.py` — Abstract base provider (placeholder)
  - `app/providers/openai_provider.py` — OpenAI provider (placeholder)
  - `app/providers/gemini_provider.py` — Gemini provider (placeholder)
  - `app/providers/huggingface_provider.py` — HuggingFace provider (placeholder)
  - `tests/__init__.py`
  - `tests/test_routes.py` — Route tests (placeholder)
  - `tests/test_orchestrator.py` — Orchestrator tests (placeholder)
  - `tests/test_circuit_breaker.py` — Circuit breaker tests (placeholder)
  - `requirements.txt` — Pinned Python dependencies
  - `run.py` — App entry point
  - `Dockerfile` — Python 3.11-slim + gunicorn
  - `docker-compose.yml` — App + PostgreSQL services
  - `.github/workflows/ci.yml` — Lint → Test → Build pipeline
  - `.flake8` — Linter config
  - `.env.example` — Environment variable template
  - `README.md` — Project overview
  - `LICENSE` — MIT License
- Renamed project from "ai-pass" to **ai-gateway** everywhere
- Moved all files to workspace root (no subfolder)

### Step 2 — Flask App Factory & Config ✅
- Implemented `app/config.py` with `Config` class
  - Loads from environment variables: DATABASE_URL, OPENAI_API_KEY, GEMINI_API_KEY, HF_API_KEY, TIMEOUT_SECONDS, MAX_RETRIES, CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_RESET_TIMEOUT, API_KEY
  - All values use `os.getenv()` with sensible defaults
  - Integer configs are cast with `int()`
- Implemented `app/__init__.py` with `create_app()` app factory
  - Creates Flask app instance
  - Loads `Config.DATABASE_URL` into `SQLALCHEMY_DATABASE_URI`
  - Initializes SQLAlchemy (`db` exported for use by models)
  - Calls `setup_logging(app)` from `logging_config.py`
  - Registers `api_bp` blueprint from `routes.py`
  - Runs `db.create_all()` inside app context to auto-create tables
- `run.py` imports `create_app()` and starts the server on port 5000

---

## Remaining Steps

### Step 3 — Database Model ✅
- Implemented `AIRequest` model in `app/models.py`
- Table `ai_requests` with columns: id (UUID), timestamp, task, input_text, provider, latency_ms, status, result_summary, user_id (default "anonymous"), error_message
- `to_dict()` method serializes all fields (timestamp as ISO format)
- `init_db()` function calls `db.create_all()`

### Step 4 — AI Provider Modules ✅
- Implemented `app/providers/base.py`:
  - Abstract `AIProvider` base class with `name` attribute and abstract `call(task, text) -> dict`
  - Custom `ProviderError(provider, message)` exception for all provider failures
- Implemented `app/providers/gemini_provider.py`:
  - `GeminiProvider` calls Google Gemini API (`generativelanguage.googleapis.com/v1beta`)
  - Model: `gemini-pro`, sends task+text as prompt
  - Returns `{"result": ..., "confidence": 0.85}`
  - Handles Timeout, RequestException, and unexpected response formats
- Implemented `app/providers/openai_provider.py`:
  - `OpenAIProvider` calls OpenAI Chat Completions API
  - Model: `gpt-3.5-turbo`, temperature: 0.3
  - Returns `{"result": ..., "confidence": 0.90}`
  - Handles Timeout, RequestException, and unexpected response formats
- Implemented `app/providers/huggingface_provider.py`:
  - `HuggingFaceProvider` calls HuggingFace Inference API
  - Model: `facebook/bart-large-cnn` (summarization)
  - Returns `{"result": ..., "confidence": 0.75}`
  - Handles list/dict response formats, Timeout, RequestException
- All providers: use `requests` with configurable timeout, raise `ProviderError` on failure, log attempts

### Step 5 — Circuit Breaker ✅
- Implemented `CircuitBreaker` class in `app/circuit_breaker.py`
- Three states: CLOSED (normal), OPEN (blocking), HALF_OPEN (testing)
- `__init__(name, failure_threshold=3, reset_timeout=60)` — one instance per provider
- `can_execute()` — returns True if CLOSED or HALF_OPEN; if OPEN and timeout expired, transitions to HALF_OPEN
- `record_success()` — resets failure count, sets state to CLOSED
- `record_failure()` — increments failures, transitions to OPEN when threshold reached
- Logs all state transitions with provider name

### Step 6 — Orchestrator (Core Logic) ✅
- Implemented `Orchestrator` class in `app/orchestrator.py`
- Initializes 3 providers (Gemini → OpenAI → HuggingFace) with one `CircuitBreaker` each
- `execute(task, text, preferred_provider="auto")`:
  - If specific provider requested, tries it first then falls back to others
  - If "auto", iterates priority order: Gemini → OpenAI → HuggingFace
  - For each provider: checks circuit breaker, skips if OPEN
  - On failure: retries once (configurable via `MAX_RETRIES`)
  - On second failure: records circuit breaker failure, moves to next provider
  - On success: records circuit breaker success, returns result
  - Tracks failover_count across the chain
- Returns: `{provider_used, result, confidence, latency_ms, failover_count}`
- If all providers fail: returns error response with details list

### Step 7 — Structured Decision Output ✅
- Implemented `make_decision(task, text, ai_result)` in `app/decision.py`
- Only triggers for tasks: `invoice_check`, `document_review`
- Scans combined text + AI result (case-insensitive) for keywords
- FAIL: if suspicious keywords found (fraud, unauthorized, forged, fake, illegal)
- PASS: if ≥2 required financial keywords found (amount, total, paid, due, invoice)
- NEEDS_INFO: if fewer than 2 required keywords found
- Returns `{decision, reasons, evidence}` — or `None` for non-decision tasks

### Step 8 — API Routes ✅
- Implemented Flask blueprint `api_bp` in `app/routes.py`
- **POST /ai/task**:
  - Accepts JSON `{task, text, provider}` (provider defaults to "auto")
  - Validates: returns 400 if task or text missing, or body not JSON
  - Calls `orchestrator.execute()` for multi-provider routing
  - Saves request to `ai_requests` table (task, provider, latency, status, result summary, error)
  - For `invoice_check`/`document_review` tasks, appends decision output via `make_decision()`
  - Returns 200 with `{provider_used, result, confidence, latency_ms}` on success
  - Returns 503 with error details if all providers fail
- **GET /health**: returns `{status: "healthy", timestamp: ISO UTC}`
- **GET /metrics**: returns Prometheus metrics via `generate_latest()`
- **GET /history**: returns last 50 requests from DB as JSON array

### Step 9 — Prometheus Metrics ✅
- Defined 4 metrics in `app/metrics.py`:
  - `ai_request_count` (Counter) — labels: task, provider, status
  - `ai_error_count` (Counter) — labels: provider
  - `ai_provider_latency_ms` (Histogram) — labels: provider, custom buckets [50–10000ms]
  - `ai_failover_count` (Counter) — labels: from_provider, to_provider
- Instrumented `app/orchestrator.py`:
  - On success: records request_count (success), latency histogram
  - On failure: records error_count, latency histogram
  - On failover: records failover_count with from→to provider pair
  - On all-fail: records request_count (error, provider=none)
- `/metrics` endpoint already wired in routes.py via `generate_latest()`

### Step 10 — Logging Configuration ✅
- Implemented `JSONFormatter` class in `app/logging_config.py`
  - Each log entry is a JSON object with: timestamp (ISO UTC), level, logger, message
  - Optional fields included when present: provider, latency_ms, status, user_id, request_id
  - Exception tracebacks included when applicable
- `setup_logging(app)` function:
  - Creates `logs/` directory if missing
  - Attaches `JSONFormatter` to both console and file (`logs/app.log`) handlers
  - Sets root logger level to INFO

### Step 11 — Unit Tests ✅
- Created `tests/conftest.py`:
  - Sets `DATABASE_URL=sqlite:///:memory:` before app imports
  - `app` fixture creates Flask app with in-memory SQLite, creates/drops tables
  - `client` fixture provides test client
- Implemented `tests/test_routes.py` (6 tests):
  - GET /health returns 200 with status + timestamp
  - POST /ai/task with missing fields returns 400
  - POST /ai/task with non-JSON body returns 400
  - POST /ai/task with valid input returns 200 (mocked orchestrator)
  - POST /ai/task returns 503 when all providers fail
  - POST /ai/task with invoice_check includes decision output
- Implemented `tests/test_orchestrator.py` (4 tests):
  - All providers mocked with `unittest.mock.patch` — no real API calls
  - Falls back to next provider when first fails
  - Skips provider when circuit breaker is OPEN
  - Result structure contains provider_used, result, confidence, latency_ms
  - All providers fail returns error response
- Implemented `tests/test_circuit_breaker.py` (6 tests):
  - Starts in CLOSED state
  - Opens after 3 consecutive failures
  - Blocks calls when OPEN
  - Transitions to HALF_OPEN after reset timeout expires
  - Returns to CLOSED on success in HALF_OPEN
  - Reopens on failure in HALF_OPEN

### Step 12 — Docker ✅
- `Dockerfile`: python:3.11-slim, installs deps, copies app, exposes 5000, runs gunicorn with 2 workers
- `docker-compose.yml`:
  - Service `app`: builds from Dockerfile, port 5000, env vars (DATABASE_URL, OPENAI_API_KEY, GEMINI_API_KEY, HF_API_KEY)
  - Service `db`: postgres:15, port 5432, persistent volume `pgdata`
  - Fixed env var name: `HF_API_KEY` (matches config.py)
  - Added `aigateway-net` bridge network for both services

### Step 13 — CI/CD Pipeline ✅
- Updated `.github/workflows/ci.yml` with 3 jobs:
  - **lint**: checkout → Python 3.11 → flake8 on app/ and tests/
  - **test**: checkout → Python 3.11 → PostgreSQL 15 service container (with health check) → pip install deps → pytest with `DATABASE_URL` pointing to service container
  - **build**: only on push to main → builds Docker image → logs in to Docker Hub via secrets → pushes image
- Pipeline order: lint → test → build (each depends on previous)
- DB name uses `aigateway_test` (matches project naming)

### Step 14 — Deployment ✅
- Created `render.yaml` (Render Blueprint):
  - Web service `ai-gateway-api`: Docker runtime, free plan, health check at `/health`
  - Environment variables: DATABASE_URL (linked from DB), OPENAI_API_KEY, GEMINI_API_KEY, HF_API_KEY, API_KEY
  - PostgreSQL database `ai-gateway-db`: free plan, db name `aigateway`
- **Manual Deployment Steps:**
  1. Push code to GitHub
  2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect your repo
  3. `render.yaml` is auto-detected — click **Deploy**
  4. After deploy succeeds, go to **Settings** → **Deploy Hook** → copy the URL
  5. Add that URL as a GitHub secret named `RENDER_DEPLOY_HOOK_URL`
  6. Every push to main now triggers a redeploy automatically
  7. Note the public URL from Render dashboard (format: `https://ai-gateway-api.onrender.com`)

### Step 15 — README ✅
- Wrote comprehensive `README.md` covering all 11 required sections:
  1. Project title, description, live URL
  2. Architecture diagram (ASCII) + component table
  3. Provider routing logic with fallback chain diagram
  4. Reliability features: retry, timeout, circuit breaker (with state diagram)
  5. Observability: 4 Prometheus metrics table + structured logging example
  6. API documentation: all 4 endpoints with request/response examples
  7. How to run locally with Docker Compose
  8. How to run tests (pytest with mocks)
  9. Deployment process (Render one-click + CI/CD)
  10. Live API URL: https://ai-gateway-api-9sm2.onrender.com
  11. Environment variables table with defaults
- Also added tech stack table and license reference

### Post-Completion — Provider & CI Fixes ✅
- **Gemini provider**: Updated model from `gemini-pro` → `gemini-2.0-flash` → `gemini-1.5-flash` → back to `gemini-pro` (most stable/available model)
- **HuggingFace provider**: Changed model from `facebook/bart-large-cnn` → `google/flan-t5-base` → `gpt2` → `distilgpt2` (smaller, more reliable); response field: `generated_text`
- **OpenAI → Claude replacement**: Replaced OpenAI provider with Claude (Anthropic) API - uses `claude-3-5-haiku-20241022` model, environment variable: `CLAUDE_API_KEY`
- **Indentation fixes**: Normalized indentation in provider files (mangled by GitHub web editor)
- **CI build step**: Fixed Docker build tag — builds as `ai-gateway:latest` first, conditionally tags/pushes to Docker Hub only when `DOCKERHUB_USERNAME` secret is set; reverted to original working format

**Live Testing Results (2026-03-11):**
- Service health: ✅ Working
- Orchestrator & failover: ✅ Working (gemini→claude→huggingface chain executing)
- Database & metrics: ✅ Working (requests logged, Prometheus counters active)
- Provider status:
  - Gemini: Testing with `gemini-pro` model (most stable)
  - Claude: Testing with `claude-3-5-haiku-20241022` model
  - HuggingFace: Testing with `distilgpt2` model

---

## 🎉 PROJECT COMPLETE

All 15 steps finished. Service is live at:
**https://ai-gateway-api-9sm2.onrender.com**

### Post-Completion — Mistral (NVIDIA) Provider Integration ✅
- Added new provider module: `app/providers/mistral_provider.py`
  - Uses NVIDIA OpenAI-compatible endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
  - Model: `mistralai/mistral-small-3.1-24b-instruct`
  - Auth via `MISTRAL_API_KEY` env variable (Bearer token)
- Updated `app/config.py` to load `MISTRAL_API_KEY`
- Updated `app/orchestrator.py` to register Mistral and make it highest priority in auto order:
  - `mistral -> gemini -> claude -> huggingface`
- Updated UI provider dropdown in `app/templates/index.html` to include `mistral`
- Updated deployment/runtime env templates:
  - `render.yaml` adds `MISTRAL_API_KEY`
  - `docker-compose.yml` adds `MISTRAL_API_KEY`
  - `.env.example` adds `MISTRAL_API_KEY` and aligns HF key name to `HF_API_KEY`
- Updated orchestrator unit tests to patch/mock `MistralProvider` in all scenarios

### Post-Completion — Frontend API Key Header Support ✅
- Diagnosed live Render behavior at `https://ai-gateway-api-9sm2.onrender.com`:
  - `/health` returns healthy
  - `/ai/task` returns `{"error":"Invalid or missing API key"}` without `X-API-Key` header
- Updated `app/templates/index.html`:
  - Added optional API key input field
  - Sends `X-API-Key` header for `/ai/task` when provided
  - Sends `X-API-Key` header for `/history`
  - Stores key in browser localStorage (`aigw_api_key`) and restores on reload for convenience

### Post-Completion — Live Provider Failure Diagnosis & Fix ✅
- Live endpoint diagnostics from Render `/ai/task` showed provider-specific failures:
  - Mistral: `404` with previous model slug
  - Gemini: `404` (old model) / key currently quota exhausted
  - Claude: `401 Unauthorized` (key/account issue)
  - HuggingFace: `410 Gone` on legacy inference endpoint/model
- Verified NVIDIA endpoint works with:
  - Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
  - Model: `mistralai/devstral-2-123b-instruct-2512`
- Updated `app/providers/mistral_provider.py` model to `mistralai/devstral-2-123b-instruct-2512`
- Updated UI error rendering in `app/templates/index.html` to show first backend detail message for faster troubleshooting

### Post-Completion — OpenAI Provider Re-Integration ✅
- Added new provider module: `app/providers/openai_provider.py`
  - Endpoint: `https://api.openai.com/v1/chat/completions`
  - Model: `gpt-4o-mini`
  - Env var: `OPENAI_API_KEY`
- Updated `app/config.py` to load `OPENAI_API_KEY`
- Updated `app/orchestrator.py` to register OpenAI and include it in fallback order:
  - `mistral -> gemini -> openai -> claude -> huggingface`
- Updated UI provider dropdown in `app/templates/index.html` to include `openai`
- Updated `tests/test_orchestrator.py` to mock `OpenAIProvider` in all orchestrator tests

### Post-Completion — Dashboard Hardening Pass ✅
- Added provider/fallback status API in `app/routes.py`:
  - `GET /provider/status` returns booleans for native keys and NVIDIA fallback availability
- Added protected history cleanup API in `app/routes.py`:
  - `POST /history/cleanup` deletes `status=error` rows
  - Optional payload field `older_than_minutes` for targeted cleanup
  - Rate-limited to `5/minute`
- Updated dashboard UI in `app/templates/index.html`:
  - New live badge: `Fallback: NVIDIA enabled/disabled`
  - New `Clear Error Rows` button to clean historical error entries from the DB
- Added route tests in `tests/test_routes.py`:
  - `test_provider_status`
  - `test_cleanup_history_errors`
- Synced deployment/runtime env templates:
  - `render.yaml` adds `NVIDIA_API_KEY`
  - `docker-compose.yml` adds `NVIDIA_API_KEY` and `OPENAI_API_KEY`
  - `.env.example` adds `NVIDIA_API_KEY` and `OPENAI_API_KEY`
- Updated `README.md` with new endpoints and environment variable documentation

### Post-Completion — README Sync with Current Code ✅
- Refreshed provider architecture/routing in `README.md` to match current orchestrator order:
  - `mistral -> gemini -> openai -> claude -> huggingface`
- Clarified current behavior for provider selection:
  - explicit provider selection tries only that provider (no silent fallback)
- Updated API docs for supported provider values and cleanup endpoint details
- Updated auth section to include `GET /provider/status` and `POST /history/cleanup`
- Updated troubleshooting and local `.env` examples to recommend `NVIDIA_API_KEY`
- Updated test coverage count in README (`test_routes.py`: 8 tests)

### Post-Completion — Dashboard UI Refresh + API Key UX ✅
- Redesigned `app/templates/index.html` with a modern visual style:
  - Gradient background, glass cards, improved typography, stronger color contrast
  - Refined status pills, metrics cards, table styling, and responsive behavior
- Added clear first-time key guidance in the UI:
  - Shows demo key hint text near API key input
  - Added `Use Demo Key` button to auto-fill key
  - Prefills key on first load when no key exists in localStorage

### Post-Completion — Grafana + Prometheus Stack ✅
- Added full observability services to `docker-compose.yml`:
  - `prometheus` on port `9090`
  - `grafana` on port `3000`
- Added Prometheus scrape config:
  - `monitoring/prometheus.yml` scraping `app:5000/metrics`
- Added Grafana provisioning:
  - Datasource config at `monitoring/grafana/provisioning/datasources/datasource.yml`
  - Dashboard provider config at `monitoring/grafana/provisioning/dashboards/dashboard.yml`
- Added ready dashboard JSON:
  - `monitoring/grafana/dashboards/ai-gateway-overview.json`
  - Includes requests, errors, failovers, request-rate-by-provider, and p95 latency panels
- Updated README Option-B docs with observability URLs and troubleshooting steps

### Post-Completion — Docker Startup Reliability Fix ✅
- Fixed root cause of empty Grafana dashboard and `localhost:5000` down in local Docker runs:
  - `app` container was crashing because `db.create_all()` ran before PostgreSQL accepted connections
- Updated `app/__init__.py`:
  - Added retry loop around `db.create_all()` (30 attempts, 2s delay)
- Updated `docker-compose.yml`:
  - Added PostgreSQL healthcheck (`pg_isready`)
  - Changed app `depends_on` to wait for `db` health
  - Added `restart: unless-stopped` for `app` and `db`
