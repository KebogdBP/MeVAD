"use client";

import {
  normalizeTelemetryRoute,
  parseTelemetryEnvelope,
  type TelemetryEventName,
  type TelemetryProperties,
} from "@/lib/telemetry";

const telemetryEnabled =
  process.env.NEXT_PUBLIC_MEVAD_TELEMETRY_ENABLED === "true";

export function trackTelemetry(
  name: TelemetryEventName,
  properties: TelemetryProperties = {},
): void {
  if (!telemetryEnabled || typeof window === "undefined") return;

  const envelope = parseTelemetryEnvelope({
    version: 1,
    name,
    route: normalizeTelemetryRoute(window.location.pathname),
    properties,
  });
  if (!envelope) return;

  try {
    void fetch("/api/telemetry", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(envelope),
      cache: "no-store",
      credentials: "same-origin",
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    // Observability must never interrupt the product workflow.
  }
}

export function telemetryDuration(startedAt: number): number {
  const elapsed = Math.max(0, performance.now() - startedAt);
  return Math.min(300_000, Math.round(elapsed / 100) * 100);
}

export function telemetryFailureKind(
  cause: unknown,
): "api_error" | "network_error" | "unknown" {
  if (cause instanceof TypeError) return "network_error";
  if (cause instanceof Error) return "api_error";
  return "unknown";
}
