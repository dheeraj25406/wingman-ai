# SRE Runbook: CPU Saturation & Compute Starvation

## Metadata
- Service: checkout-service
- Category: Compute
- Severity: P2_HIGH
- Runbook ID: RB-CPU-002

## Symptoms & Detection Signals
- Service container CPU utilization sustained above 95%.
- Severe degradation in request processing duration (latency p95 > 1200ms).
- Host throttling flags appearing in telemetry metrics.
- Upstream HTTP 504 Gateway Timeout on api-gateway.

## Root Cause Analysis
1. Inefficient recursive algorithm or unthrottled cryptographic hashing loop.
2. Thread starvation caused by high thread contention on shared locks.
3. Sudden traffic surge without horizontal auto-scaling (HPA) kicking in.

## Diagnostic Verification Steps
1. Fetch CPU utilization metrics using `get_service_metrics('checkout-service')`.
2. Inspect trace durations for compute spans using `get_trace(trace_id)`.
3. Compare against 24-hour baseline using `compare_service_baseline('checkout-service')`.

## Remediation & Recovery Procedure
1. [Action]: Execute `restart_service('checkout-service')` to clear runaway processes.
2. [Mitigation]: Temporarily throttle incoming traffic load via `throttle_traffic_load('checkout-service', factor=0.5)`.
3. [Verification]: Ensure CPU utilization stabilizes below 40% and p95 latency normalizes.
