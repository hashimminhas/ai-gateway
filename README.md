# AI-Gateway — Autonomous AI Orchestration Platform

> Resilient multi-provider AI orchestration service with automatic fallback, circuit breaker, retry logic, and Prometheus observability. Built with Flask, PostgreSQL, and Docker.

**Live API:** [https://ai-gateway-api-9sm2.onrender.com](https://ai-gateway-api-9sm2.onrender.com)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Provider Routing Logic](#provider-routing-logic)
3. [Reliability Features](#reliability-features)
4. [Observability](#observability)
5. [API Documentation](#api-documentation)
6. [How to Run Locally](#how-to-run-locally) ← **Start here if you're new**
7. [How to Run Tests](#how-to-run-tests)
8. [Deployment Process](#deployment-process)
9. [Environment Variables](#environment-variables)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                      Client / User                       │
└────────────────────────┬─────────────────────────────────┘
                         │  POST /ai/task
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    Flask API (routes.py)                  │
│ /ai/task /health /metrics /history /provider/status       │
└────────┬──────────────┬──────────────┬───────────────────┘
         │              │              │
         ▼              ▼              ▼
┌────────────┐  ┌──────────────┐  ┌────────────────┐
│ Orchestrator│  │  Prometheus  │  │   PostgreSQL   │
│             │  │  Metrics     │  │   (ai_requests │
│ ┌─────────┐│  │              │  │    table)      │
│ │Circuit  ││  └──────────────┘  └────────────────┘
│ │Breakers ││
│ └─────────┘│
└──┬────┬────┬────┬────┬───────────────────────────────────┘
  │    │    │    │    │
  ▼    ▼    ▼    ▼    ▼
┌───────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────────────┐
│Mistral│ │Gemini│ │OpenAI│ │Claude│ │ HuggingFace │
│(pri 1)│ │(pri 2)│ │(pri 3)│ │(pri 4)│ │  (pri 5)    │
└───────┘ └──────┘ └──────┘ └──────┘ └─────────────┘
```

**Components:**

| Component | File | Purpose |
|-----------|------|---------|
| App Factory | `app/__init__.py` | Flask app creation, DB init, blueprint registration |
| Config | `app/config.py` | Environment-based configuration |
| Routes | `app/routes.py` | REST API endpoints |
| Orchestrator | `app/orchestrator.py` | Multi-provider routing with retry + fallback |
| Circuit Breaker | `app/circuit_breaker.py` | Per-provider failure tracking and blocking |
| Decision Engine | `app/decision.py` | Rule-based structured output for invoice/document tasks |
| Metrics | `app/metrics.py` | Prometheus counters and histograms |
| Logging | `app/logging_config.py` | Structured JSON logging to console + file |
| Models | `app/models.py` | SQLAlchemy model for request history |
| Providers | `app/providers/` | Mistral, Gemini, OpenAI, Claude, HuggingFace integrations with NVIDIA fallback |

---

## Provider Routing Logic

When a request is received with `"provider": "auto"` (default), the orchestrator tries providers in priority order:

```
1. Mistral      (confidence: 0.88)  ──fail──▶ retry once ──fail──▶
2. Gemini       (confidence: 0.85)  ──fail──▶ retry once ──fail──▶
3. OpenAI       (confidence: 0.89)  ──fail──▶ retry once ──fail──▶
4. Claude       (confidence: 0.90)  ──fail──▶ retry once ──fail──▶
5. HuggingFace  (confidence: 0.75)  ──fail──▶ retry once ──fail──▶ Error 503
```

- If a specific provider is requested (e.g. `"provider": "claude"`), only that provider is attempted (no silent fallback).
- Each provider's circuit breaker is checked before attempting a call — if a provider has failed 3+ times recently, it is skipped entirely.
- The `provider_used` field in the response tells you which provider actually handled the request.

Provider key behavior:
- `mistral` uses `MISTRAL_API_KEY` (NVIDIA endpoint)
- `gemini` prefers `NVIDIA_API_KEY` and falls back to native `GEMINI_API_KEY`
- `openai` uses native `OPENAI_API_KEY` only when it starts with `sk-`; otherwise it uses `NVIDIA_API_KEY`
- `claude` prefers `CLAUDE_API_KEY`; if absent, it uses `NVIDIA_API_KEY`
- `huggingface` uses `NVIDIA_API_KEY`

---

## Reliability Features

### Retry Mechanism
- On failure, each provider is retried **once** before moving to the next (configurable via `MAX_RETRIES`).

### Timeout Handling
- Every API call has a **10-second timeout** (configurable via `TIMEOUT_SECONDS`).
- If a provider doesn't respond in time, it's treated as a failure.

### Circuit Breaker

Each provider has its own circuit breaker with three states:

```
CLOSED ──(3 failures)──▶ OPEN ──(60s timeout)──▶ HALF_OPEN ──(success)──▶ CLOSED
                                                      │
                                                  (failure)
                                                      │
                                                      ▼
                                                    OPEN
```

| Parameter | Default | Env Var |
|-----------|---------|---------|
| Failure threshold | 3 | `CIRCUIT_BREAKER_THRESHOLD` |
| Reset timeout | 60s | `CIRCUIT_BREAKER_RESET_TIMEOUT` |

**Behavior:**
- **CLOSED** — normal operation, requests go through
- **OPEN** — provider is blocked, requests skip to next provider
- **HALF_OPEN** — after timeout expires, one test request is allowed; success → CLOSED, failure → OPEN

---

## Observability

### Prometheus Metrics

Available at `GET /metrics` in Prometheus exposition format.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ai_request_count` | Counter | task, provider, status | Total requests processed |
| `ai_error_count` | Counter | provider | Total provider errors |
| `ai_provider_latency_ms` | Histogram | provider | Provider response latency (ms) |
| `ai_failover_count` | Counter | from_provider, to_provider | How often fallbacks occur |

### Structured Logging

Every log entry is a JSON object with:

```json
{
  "timestamp": "2026-03-11T12:00:00+00:00",
  "level": "INFO",
  "logger": "app.orchestrator",
  "message": "Provider gemini succeeded in 230ms",
  "provider": "gemini",
  "latency_ms": 230,
  "status": "success"
}
```

Logs are written to both **console** and **`logs/app.log`**.

---

## API Documentation

### POST /ai/task

Submit a task to the AI orchestration service.

**Request:**

```json
{
  "task": "summarize",
  "text": "Invoice for services rendered. Total amount: $5,000. Payment due: March 30, 2026.",
  "provider": "auto"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task | string | Yes | Task type (e.g. `summarize`, `invoice_check`, `document_review`) |
| text | string | Yes | Input text to process |
| provider | string | No | `auto` (default), `mistral`, `gemini`, `openai`, `claude`, `huggingface` |

**Response (200):**

```json
{
  "provider_used": "gemini",
  "result": "This invoice is for $5,000 in services, with payment due March 30, 2026.",
  "confidence": 0.85,
  "latency_ms": 450
}
```

**Response with Decision (for `invoice_check` or `document_review` tasks):**

```json
{
  "provider_used": "claude",
  "result": "...",
  "confidence": 0.90,
  "latency_ms": 300,
  "decision": {
    "decision": "PASS",
    "reasons": ["Key financial fields present in document"],
    "evidence": ["amount", "total", "due"]
  }
}
```

Decision values: `PASS` | `FAIL` | `NEEDS_INFO`

**Error Responses:**

| Code | Condition |
|------|-----------|
| 400 | Missing `task` or `text`, or body is not JSON |
| 503 | All providers failed |

---

### GET /health

```json
{
  "status": "healthy",
  "timestamp": "2026-03-11T12:00:00+00:00"
}
```

### GET /metrics

Returns Prometheus-format metrics (text/plain).

### GET /history

Returns the last 50 requests from the database:

```json
[
  {
    "id": "uuid",
    "timestamp": "2026-03-11T12:00:00",
    "task": "summarize",
    "provider": "gemini",
    "latency_ms": 450,
    "status": "success",
    "result_summary": "...",
    "user_id": "anonymous",
    "error_message": null
  }
]
```

### GET /provider/status

Returns key-based provider/fallback status flags for the dashboard.

```json
{
  "nvidia_fallback_enabled": true,
  "openai_native_enabled": false,
  "claude_native_enabled": false,
  "gemini_native_enabled": false,
  "huggingface_native_enabled": false
}
```

### POST /history/cleanup

Deletes rows with `status=error` from request history.

Rate limit: 5 requests/minute.

**Request body (optional):**

```json
{
  "older_than_minutes": 60
}
```

If `older_than_minutes` is omitted, all error rows are removed.

### Dashboard API key helper

The frontend includes an API-key helper near the input field:
- A demo hint is displayed for first-time users
- A `Use Demo Key` button can auto-fill the key
- The key is persisted in browser localStorage as `aigw_api_key`

---

## How to Run Locally

There are two ways to run the project: **Option A** (plain Python, quickest — no Docker needed) and **Option B** (Docker Compose, mirrors production exactly).

---

### Option A — Plain Python (Recommended for first-timers)

#### 1. Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.10 or newer | `python --version` |
| pip | any recent | `pip --version` |
| Git | any | `git --version` |

No database server required — the app will use a local SQLite file automatically.

#### 2. Clone the repository

```bash
git clone https://github.com/hashimminhas/ai-gateway.git
cd ai-gateway
```

#### 3. Create and activate a virtual environment

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate.bat
```

> You should see `(.venv)` at the start of your terminal prompt.

#### 4. Install dependencies

```bash
pip install -r requirements.txt
```

> `psycopg2-binary` may show a warning if PostgreSQL isn't installed — that is fine for SQLite mode.

#### 5. Create your `.env` file

Copy the example below and save it as `.env` in the project root:

```env
# Minimum config — uses SQLite, no API keys needed to boot
DATABASE_URL=sqlite:///aigateway.db

# Optional — add real keys to actually call AI providers
# NVIDIA_API_KEY=nvapi-...           # preferred unified fallback key
# MISTRAL_API_KEY=nvapi-...          # backward-compatible fallback source
# OPENAI_API_KEY=sk-...              # native OpenAI (optional)
# CLAUDE_API_KEY=sk-ant-...          # native Claude (optional)
# GEMINI_API_KEY=AIza...             # native Gemini (optional)
# HF_API_KEY=hf_...                  # currently not required by provider implementation

# Optional — protect the API with a key
# API_KEY=my-secret-key
```

> Without real API keys the app will start fine and the UI will load, but `/ai/task` calls will return a 503 because no provider is reachable. Add at least one key to see real results.

#### 6. Start the server

```bash
# macOS / Linux
DATABASE_URL=sqlite:///aigateway.db python run.py

# Windows PowerShell
$env:DATABASE_URL="sqlite:///aigateway.db"; python run.py

# Or, if you added DATABASE_URL to your .env file (requires python-dotenv loaded):
python run.py
```

You should see:

```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

#### 7. Open the frontend

Navigate to **http://localhost:5000** in your browser — the AI Gateway dashboard will load.

#### 8. Quick smoke-test

```bash
# Health check
curl http://localhost:5000/health

# Submit a task (requires at least one API key configured)
curl -X POST http://localhost:5000/ai/task \
  -H "Content-Type: application/json" \
  -d '{"task": "summarize", "text": "The quick brown fox jumps over the lazy dog."}'
```

---

### Option B — Docker Compose (mirrors production)

#### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

#### 2. Clone and configure

```bash
git clone https://github.com/hashimminhas/ai-gateway.git
cd ai-gateway

# Create .env with your keys (PostgreSQL is started by Docker automatically)
cp .env.example .env   # or create .env manually — see table below
```

#### 3. Start everything

```bash
docker-compose up --build
```

This starts two containers: **app** (Flask on port 5000) and **db** (PostgreSQL).  
Wait for the line `Running on http://0.0.0.0:5000` before testing.

#### 4. Open the frontend

Navigate to **http://localhost:5000**.

#### 5. Stop the service

```bash
docker-compose down        # stop containers
docker-compose down -v     # also delete the database volume
```

---

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: No module named 'flask'` | venv not activated or deps not installed | Run `pip install -r requirements.txt` inside the activated venv |
| `ModuleNotFoundError: No module named 'psycopg2'` | Using PostgreSQL URL without the driver | Switch to `DATABASE_URL=sqlite:///aigateway.db` for local dev |
| `OperationalError: could not connect to server` | PostgreSQL isn't running | Use SQLite (Option A) or start Docker (Option B) |
| Port 5000 already in use | Another process on port 5000 | Change the port: `python run.py` → edit `run.py` and set `port=5001` |
| `/ai/task` returns 503 | No usable API keys configured | Set `NVIDIA_API_KEY` (recommended) or set native keys (`OPENAI_API_KEY`, `CLAUDE_API_KEY`, `GEMINI_API_KEY`) |
| Windows — `Activate.ps1 cannot be loaded` | PowerShell execution policy | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first |

---

## How to Run Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v
```

Tests use **SQLite in-memory** and **mocked provider calls** — no real API keys or PostgreSQL needed.

**Test coverage:**
- `test_routes.py` — API endpoint validation (8 tests)
- `test_orchestrator.py` — Fallback, circuit breaker, error handling (4 tests)
- `test_circuit_breaker.py` — State transitions CLOSED → OPEN → HALF_OPEN → CLOSED (6 tests)

---

## Deployment Process

### One-Click Deploy to Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo (`hashimminhas/ai-gateway`)
4. `render.yaml` is auto-detected — click **Deploy**
5. Set API keys in the environment variables form
6. Wait for build to complete (~2 minutes)
7. Your live URL: `https://ai-gateway-api-9sm2.onrender.com`

### CI/CD Pipeline (GitHub Actions)

Every push to `main` triggers:

```
Lint (flake8) → Test (pytest + PostgreSQL) → Build (Docker image)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql://localhost/aigateway` | PostgreSQL connection string |
| `NVIDIA_API_KEY` | No | `""` | Preferred NVIDIA key for unified fallback endpoint |
| `MISTRAL_API_KEY` | No | `""` | Backward-compatible fallback source for `NVIDIA_API_KEY` |
| `OPENAI_API_KEY` | No | `""` | Native OpenAI key (`sk-...`) when available |
| `CLAUDE_API_KEY` | No | `""` | Anthropic Claude API key |
| `GEMINI_API_KEY` | No | `""` | Google Gemini API key |
| `HF_API_KEY` | No | `""` | HuggingFace Inference API token |
| `API_KEY` | No | `""` | Optional auth key for API protection |
| `TIMEOUT_SECONDS` | No | `10` | Provider call timeout |
| `MAX_RETRIES` | No | `1` | Retries per provider before fallback |
| `CIRCUIT_BREAKER_THRESHOLD` | No | `3` | Failures before circuit opens |
| `CIRCUIT_BREAKER_RESET_TIMEOUT` | No | `60` | Seconds before circuit tries again |

---

## Security & Rate Limiting

### API Key Authentication

Protected endpoints (`POST /ai/task`, `GET /history`, `GET /provider/status`, `POST /history/cleanup`) require an `X-API-Key` header when the `API_KEY` environment variable is set.

```bash
curl -X POST https://ai-gateway-api-9sm2.onrender.com/ai/task \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"task": "summarize", "text": "Your text here"}'
```

If `API_KEY` is not set, authentication is disabled (open access).

### Rate Limiting

The `/ai/task` endpoint is rate-limited to **30 requests per minute** per IP address using `flask-limiter`. Exceeding the limit returns `429 Too Many Requests`.

---

## Horizontal Scaling

The service is designed for horizontal scaling:

- **Stateless application tier** — no in-memory session state; all request data is stored in PostgreSQL
- **Gunicorn workers** — the Docker image runs gunicorn with multiple workers (`-w 2`) for concurrent request handling; increase workers based on available CPU cores
- **Database-backed persistence** — circuit breaker state resets on restart, but request history is durable in PostgreSQL
- **Container-ready** — deploy multiple replicas behind a load balancer (e.g. Render, Kubernetes, ECS) with the same `DATABASE_URL`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.1 (Python 3.11) |
| Database | PostgreSQL 15 |
| ORM | Flask-SQLAlchemy |
| Monitoring | prometheus-client |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Hosting | Render (free tier) |
| HTTP Server | Gunicorn |

---

## License

MIT — see [LICENSE](LICENSE) for details.
