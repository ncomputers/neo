# Multi-Tenant Security

This document outlines mechanisms used to harden the platform in a multi-tenant environment.

## Schema Isolation
Each tenant's data resides in its own database schema or dedicated database.
Connections are derived from `POSTGRES_TENANT_DSN_TEMPLATE` where `{tenant_id}` ensures queries stay within tenant scope.
No cross-tenant tables are shared, and migrations operate per schema to prevent leakage.

## Key Scopes
API keys and JWT claims include a `tenant` identifier.
Runtime access checks validate that keys only operate on their tenant's resources.
Super-admin keys are issued separately and are never repurposed across tenants.

## Signed URLs
Object storage and webhook callbacks rely on expiring signed URLs.
Signatures include tenant ID and optional allowed paths.
The signature window is short-lived to limit misuse, and URLs are regenerated whenever secrets rotate.

## Limits
Per-tenant quotas reduce "noisy neighbor" issues.
Rate limiting uses Redis to cap requests per IP and per tenant.
Export and storage quotas enforce maximum size (`EXPORT_MAX_ROWS`, plan-specific file caps).

## Soft Delete
Resources use `deleted_at` to hide items instead of hard deletion.
Indexes enforce uniqueness only on active records and endpoints allow restore operations.
See [soft_delete.md](soft_delete.md) for APIs and behavior.

## Audit Trails
All privileged actions emit audit events tagged with tenant and actor identifiers.
Logs are immutable and stored centrally.
Administrators can filter audits by tenant during investigations.

