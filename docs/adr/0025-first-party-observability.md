# ADR 0025: First-party production observability baseline

## Status

Accepted for Phase 8 launch hardening.

## Context

MeVAD needs enough operational evidence to diagnose launch failures before selecting an external
telemetry vendor. Media URLs and query strings are sensitive and must not enter access logs or
metric labels.

## Decision

- Every API response receives an `X-Request-ID`. A bounded caller-provided identifier is preserved;
  malformed values are replaced.
- The API emits structured JSON access events containing only request ID, method, path, status and
  duration. Bodies, query strings, media URLs and client IPs are excluded.
- A process-local Prometheus text endpoint exposes request totals and duration grouped only by HTTP
  method and status class. This avoids unbounded job-ID/path labels.
- `/metrics` is served by the API listener, which remains loopback/internal in the supported Compose
  topology and is not routed through the public Next.js application.
- External log and metric storage, alert routing, retention and incident ownership remain deployment
  decisions and must be documented before enabling third-party telemetry.

## Consequences

Operators get correlation and basic RED signals without adding cookies, fingerprinting, vendor SDKs
or a new runtime dependency. Metrics are process-local, so a future multi-replica deployment needs a
scraper that aggregates every replica.
