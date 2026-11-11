# SRE Runbook: Database Connection Pool Exhaustion

## Metadata
- Service: order-service
- Category: Database
- Severity: P1_CRITICAL
- Runbook ID: RB-DB-001

## Symptoms & Detection Signals
- Sudden spike in PostgreSQL connection count reaching 100% of `max_connections` (or pool cap `100/100`).
- Application logs emitting `ConnectionPoolTimeoutError: Could not obtain connection within 3.00s`.
- Upstream HTTP 500 errors propagating to checkout-service and api-gateway.
- Latency p95/p99 climbing from baseline 70ms to > 2500ms.

## Root Cause Analysis
1. Idle in transaction connections held by long-running transactions.
2. Sudden burst of concurrent checkout operations exceeding pool sizing without queue throttling.
3. Missing database index causing slow table scans holding locks.
4. Connection leak where connections are acquired but not released in exception blocks.

## Diagnostic Verification Steps
1. Query active pool metrics via `get_service_metrics('order-service')`.
2. Inspect application logs for `ConnectionPoolTimeoutError` using `search_logs('order-service', level='ERROR')`.
3. Verify downstream dependencies using `get_service_map()`.

## Remediation & Recovery Procedure
1. [Precondition]: Verify order-service is rejecting transactions due to connection starvation.
2. [Action]: Execute controlled pool reset: `reset_db_pool_limit('order-service', new_limit=150)` or gracefully restart `order-service` to terminate leaked connections.
3. [Post-Action Verification]: Confirm `db_connections` metric returns to < 40% and p95 latency drops below 100ms.
