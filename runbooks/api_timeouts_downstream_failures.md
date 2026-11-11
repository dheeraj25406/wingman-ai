# SRE Runbook: Downstream API Timeouts & Provider Failures

## Metadata
- Service: payment-service
- Category: Downstream Dependency
- Severity: P1_CRITICAL
- Runbook ID: RB-EXT-004

## Symptoms & Detection Signals
- HTTP 502 Bad Gateway or 503 Service Unavailable returned by payment-service.
- Client requests timing out after 3500ms timeout window.
- Elevated error rates (> 80%) on checkout-service and api-gateway.

## Root Cause Analysis
1. 3rd-party banking acquirer endpoint latency degradation or outright outage.
2. TLS certificate expiry or handshake failure with external API gateway.
3. Network egress routing partition or rate-limiting block from external provider.

## Diagnostic Verification Steps
1. Inspect payment trace details via `get_trace(trace_id)`.
2. Check for `PaymentGatewayUnavailableException` in logs via `search_logs('payment-service', level='ERROR')`.

## Remediation & Recovery Procedure
1. [Action]: Enable payment provider fallback route or restart payment service circuit-breaker: `restart_service('payment-service')`.
2. [Mitigation]: Enable degraded payment mode (asynchronous checkout queueing).
3. [Verification]: Confirm checkout error rate drops below 1% and downstream spans succeed.
