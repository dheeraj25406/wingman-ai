# SRE Runbook: Queue Backlog & Worker Starvation

## Metadata
- Service: order-service
- Category: Async Processing
- Severity: P3_MEDIUM
- Runbook ID: RB-Q-005

## Symptoms & Detection Signals
- Message queue depth exceeding 10,000 pending items.
- Order confirmation latency p95 > 800ms.
- Asynchronous event processing delay increasing monotonically.

## Root Cause Analysis
1. Worker thread pool deadlock or unhandled consumer exceptions crashing consumer loops.
2. Ingestion rate significantly exceeding single-consumer processing throughput.
3. Slow consumer downstream database lock contention.

## Diagnostic Verification Steps
1. Retrieve queue depth metrics via `get_service_metrics('order-service')`.
2. Inspect worker logs for consumer thread state via `search_logs('order-service', query='queue')`.

## Remediation & Recovery Procedure
1. [Action]: Execute queue backlog drain & worker reset: `drain_queue_backlog('order-service')`.
2. [Verification]: Confirm queue depth reduces to < 50 items and processing lag returns to normal.
