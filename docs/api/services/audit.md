# Audit

> Audit service for tamper evident event recording and chain integrity verification.

## Overview

Audit is the append only audit log service in the platform. It receives structured audit events from all services via NATS, persists them in a tamper evident log, and verifies the chain integrity periodically. It does not publish events, take business actions, or modify data in other services.

## Responsibilities

1. Receives and persists audit events from all platform services.
2. Exposes a paginated query endpoint for audit log inspection.
3. Verifies the integrity of the audit chain periodically.
4. Does not publish events, take business actions, or modify data in other services.

## HTTP API

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/audit` | Query the audit log with filters, paginated | Internal |

Full spec: [`docs/openapi/audit/openapi.yaml`](../openapi/audit/openapi.yaml)

## Events

### Published

This service does not publish domain events.

### Consumed

| Event | NATS Subject | Action |
|-------|-------------|--------|
| All audit events | `audit.events.v1` | Persists the event to the append only audit log. |

> All services publish audit events through the shared `auditor` package. The subject and schema are defined centrally in that package. Audit does not need to know which service emitted each event.

## Background Workers

| Worker | Type | Description |
|--------|------|-------------|
| `audit-events-handler` | NATS subscriber | Receives audit events from all services and writes them to the audit table. |
| `chain_verifier` | arq job | Verifies the cryptographic integrity of the audit chain. |

## Internal Dependencies

| Package | Purpose |
|---------|---------|
| `auditor` | Shared audit event schema and NATS subject definitions |
| `exceptions` | Shared HTTP exception types |
| `idempotency` | Redis backed idempotency keys |
| `locking` | Redis distributed locks |
| `middleware` | Request ID, correlation, and security headers |
| `observability` | OpenTelemetry setup |
| `worker` | arq worker bootstrap |

## External Dependencies

| Service | Purpose |
|---------|---------|
| PostgreSQL | Append only audit log store |
| Redis | Idempotency keys and rate limiting |
| NATS JetStream | Consuming audit events from all services |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string. |
| `REDIS_URL` | Redis connection URL. |
| `NATS_URL` | NATS server address. |
| `INTERNAL_API_KEY` | Shared secret for the internal audit query endpoint. |
| `IDEMPOTENCY_ENABLED` | Flag to enable idempotency key enforcement. Defaults to true. |
| `RATELIMIT_ENABLED` | Flag to enable API rate limiting. Defaults to true. |
| `OTEL_ENABLED` | Flag to enable OpenTelemetry tracing. |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint. Defaults to `http://localhost:4317`. |
