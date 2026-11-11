# SRE Runbook: Deployment Regression & Configuration Rollback

## Metadata
- Service: user-service
- Category: Deployment
- Severity: P1_CRITICAL
- Runbook ID: RB-DEP-006

## Symptoms & Detection Signals
- Immediate error rate spike to > 90% immediately following a deployment event.
- Application logs showing missing environment configuration or null-pointer errors (e.g. `KeyError: 'JWT_SECRET_KEY'`).
- Healthcheck endpoints failing with HTTP 500.

## Root Cause Analysis
1. Deployment introduced code relying on new environment variables not yet provisioned in production.
2. Breaking schema migration or missing database column in new release.
3. Incompatible library version update causing runtime import errors.

## Diagnostic Verification Steps
1. Retrieve recent deployment history via `get_recent_deployments('user-service')`.
2. Search error logs for startup or configuration exceptions via `search_logs('user-service', level='ERROR')`.

## Remediation & Recovery Procedure
1. [Action]: Execute immediate rollback: `rollback_deployment('user-service', target_version='v2.4.0')`.
2. [Verification]: Confirm error rate returns to 0% and user authentication endpoints respond with HTTP 200.
