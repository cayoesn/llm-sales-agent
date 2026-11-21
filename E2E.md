# E2E Testing Guide

This document describes how to run the project end-to-end using Docker and verify the complete behavior of the API and observability stack.

## Prerequisites
- Docker and Docker Compose installed.
- `make` installed (optional, but recommended).

## Starting the full stack

1. Copy the example environment file: `cp .env.example .env`
2. Start the stack: `docker compose up --build`

### What happens on startup (Lifespan)
When starting the `api` container, the system runs a `lifespan` manager (`app/main.py`). If `LLM_PROVIDER` is configured as `ollama`, the API enters a wait loop until the `ollama-pull-model` service finishes downloading the required model (`llama3.1`), ensuring the API does not serve requests before it is ready to process them.

Started services include the API, Ollama, Redis, Langfuse (optional), and the observability stack (Prometheus, Loki, Promtail, Grafana).

## Chat flow testing

Below are examples of core interactions via `curl`. Use the same `session_id` to preserve context within a session.

### 1. Add and manage cart items

```bash
# Add
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"I want 2 sneakers for $100 each"}'

# View
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Show my cart"}'

# Remove
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Remove the sneakers"}'
```

### 2. Checkout and Order Status

```bash
# Checkout
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Complete purchase"}'

# Check Status (use the ID returned at checkout)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-1","message":"Order status <ORDER_ID>"}'
```

## Monitoring

1. Open Grafana at `http://localhost:3001` (login: `admin` / `admin`).
2. Explore dashboards for Loki (API logs) and Prometheus (request metrics).

## Quality validation

To validate the system locally according to the project quality rules:

```bash
# Run unit/integration tests with coverage > 90%
make coverage

# Run lint, mypy, and security checks
make lint
```

To tear down: `docker compose down -v`.
