# AI-Gateway — Autonomous AI Orchestration Platform

> Resilient multi-provider AI orchestration service with fallback, circuit breaker, and observability.

## Quick Start

```bash
docker-compose up --build
```

API available at `http://localhost:5000`

## API Endpoints

| Method | Path        | Description              |
|--------|-------------|--------------------------|
| POST   | /ai/task    | Submit an AI task        |
| GET    | /health     | Health check             |
| GET    | /metrics    | Prometheus metrics       |
| GET    | /history    | Recent request history   |

## Architecture

*Details to be added as features are implemented.*
