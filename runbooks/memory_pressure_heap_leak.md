# SRE Runbook: Memory Pressure & Heap Leak

## Metadata
- Service: product-service
- Category: Memory
- Severity: P2_HIGH
- Runbook ID: RB-MEM-003

## Symptoms & Detection Signals
- Resident set size (RSS) or JVM heap utilization exceeding 90%.
- Elevated garbage collection (GC) pause times causing periodic latency spikes.
- OutOfMemoryError exceptions in service logs.

## Root Cause Analysis
1. Unbounded in-memory caching of product catalog items without TTL eviction.
2. Static collection retaining object references across requests.
3. Rapid memory allocation rate surpassing GC collection throughput.

## Diagnostic Verification Steps
1. Verify memory utilization trend via `get_service_metrics('product-service')`.
2. Search error logs for `OutOfMemoryError` via `search_logs('product-service', level='ERROR')`.

## Remediation & Recovery Procedure
1. [Action]: Execute graceful service container restart: `restart_service('product-service')`.
2. [Verification]: Validate memory utilization drops back to baseline ~35% and error rate returns to 0%.
