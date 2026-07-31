# ADR 0024: Public API abuse guard

## Status

Accepted for Phase 8 launch hardening.

## Context

Media analysis and conversion are anonymous, network-facing and materially more expensive than
ordinary page requests. A public launch without admission control would let one client exhaust the
analyzer, Redis queue or worker capacity.

## Decision

- Apply independent fixed-window limits to analysis and job creation.
- Limit active anonymous jobs per pseudonymous client identity.
- Derive that identity with HMAC-SHA-256 from the canonical client IP; never store the raw IP in
  abuse-control keys.
- Trust `X-Forwarded-For` only when explicitly configured behind the Caddy and Next.js proxy chain.
- Use atomic Redis scripts in shared deployments and an in-memory implementation for local work and
  tests.
- Fail closed with a stable `503 abuse_protection_unavailable` response when admission state cannot
  be checked. Return stable `429` errors and `Retry-After` when a limit is reached.
- Release active-job slots on terminal status observation, result download or completed cancellation;
  retain a bounded TTL as recovery when a client never polls again.

## Consequences

The guard protects application capacity across API replicas without introducing accounts before the
product needs them. It is not a replacement for edge DDoS protection, CAPTCHA escalation, or future
authenticated subscription quotas.
