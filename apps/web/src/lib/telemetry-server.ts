import {
  parseTelemetryEnvelope,
  type TelemetryEventName,
  type TelemetryProperties,
} from "@/lib/telemetry";

export function recordTelemetry(
  name: TelemetryEventName,
  route: string,
  properties: TelemetryProperties,
): void {
  if (process.env.MEVAD_TELEMETRY_MODE !== "stdout") return;

  const envelope = parseTelemetryEnvelope({
    version: 1,
    name,
    route,
    properties,
  });
  if (!envelope) return;

  console.info(
    JSON.stringify({
      kind: "mevad.telemetry",
      received_at: new Date().toISOString(),
      ...envelope,
    }),
  );
}
