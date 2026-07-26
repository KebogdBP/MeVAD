const PUBLIC_ROUTES = new Set([
  "/",
  "/video-downloader",
  "/audio-downloader",
  "/video-cutter",
  "/video-to-gif",
  "/how-it-works",
  "/supported-sites",
  "/privacy",
  "/terms",
  "/copyright",
]);

export const TELEMETRY_EVENT_PROPERTIES = {
  page_view: [],
  analysis_started: [],
  analysis_succeeded: ["duration_ms", "available_actions"],
  analysis_failed: ["duration_ms", "failure_kind"],
  action_selected: ["action"],
  job_created: ["action"],
  job_terminal: ["action", "status"],
  job_cancel_requested: ["action"],
  web_vital: ["metric", "rating", "value", "navigation_type"],
  client_error: ["source", "error_name"],
  api_proxy_failed: ["operation", "status_class"],
} as const;

export type TelemetryEventName = keyof typeof TELEMETRY_EVENT_PROPERTIES;
export type TelemetryProperties = Record<string, string | number | boolean>;

export interface TelemetryEnvelope {
  version: 1;
  name: TelemetryEventName;
  route: string;
  properties: TelemetryProperties;
}

const ACTIONS = new Set([
  "download_video",
  "extract_audio",
  "cut_clip",
  "create_gif",
]);
const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"]);
const FAILURE_KINDS = new Set([
  "api_error",
  "network_error",
  "validation_error",
  "unavailable",
  "unknown",
]);
const WEB_VITALS = new Set(["CLS", "FCP", "INP", "LCP", "TTFB"]);
const RATINGS = new Set(["good", "needs-improvement", "poor"]);
const NAVIGATION_TYPES = new Set([
  "navigate",
  "reload",
  "back-forward",
  "back_forward",
  "prerender",
  "restore",
  "unknown",
]);
const ERROR_SOURCES = new Set(["window", "promise", "react-boundary"]);
const OPERATIONS = new Set([
  "analyze",
  "create-job",
  "job-status",
  "cancel-job",
  "result",
  "unknown",
]);
const STATUS_CLASSES = new Set(["network", "timeout", "4xx", "5xx", "unknown"]);
const ERROR_NAME = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/;

export function normalizeTelemetryRoute(input: string): string {
  try {
    const pathname = new URL(input, "https://telemetry.invalid").pathname;
    return PUBLIC_ROUTES.has(pathname) ? pathname : "/other";
  } catch {
    return "/other";
  }
}

export function safeErrorName(error: unknown): string {
  const name =
    error instanceof Error
      ? error.name
      : typeof error === "object" &&
          error !== null &&
          "name" in error &&
          typeof error.name === "string"
        ? error.name
        : "UnknownError";
  return ERROR_NAME.test(name) ? name : "UnknownError";
}

export function parseTelemetryEnvelope(input: unknown): TelemetryEnvelope | null {
  if (!isPlainObject(input)) return null;
  if (!hasExactKeys(input, ["version", "name", "route", "properties"])) return null;
  if (input.version !== 1 || typeof input.name !== "string") return null;
  if (!(input.name in TELEMETRY_EVENT_PROPERTIES)) return null;
  if (typeof input.route !== "string") return null;

  const route = normalizeTelemetryRoute(input.route);
  const properties = input.properties;
  if (route !== input.route || !isPlainObject(properties)) return null;

  const name = input.name as TelemetryEventName;
  const allowedKeys = TELEMETRY_EVENT_PROPERTIES[name] as readonly string[];
  if (!hasExactKeys(properties, allowedKeys)) return null;
  if (!allowedKeys.every((key) => isValidProperty(key, properties[key]))) {
    return null;
  }

  return {
    version: 1,
    name,
    route,
    properties: properties as TelemetryProperties,
  };
}

function isValidProperty(key: string, value: unknown): boolean {
  if (key === "action") return typeof value === "string" && ACTIONS.has(value);
  if (key === "status") {
    return typeof value === "string" && TERMINAL_STATUSES.has(value);
  }
  if (key === "failure_kind") {
    return typeof value === "string" && FAILURE_KINDS.has(value);
  }
  if (key === "metric") {
    return typeof value === "string" && WEB_VITALS.has(value);
  }
  if (key === "rating") {
    return typeof value === "string" && RATINGS.has(value);
  }
  if (key === "navigation_type") {
    return typeof value === "string" && NAVIGATION_TYPES.has(value);
  }
  if (key === "source") {
    return typeof value === "string" && ERROR_SOURCES.has(value);
  }
  if (key === "error_name") {
    return typeof value === "string" && ERROR_NAME.test(value);
  }
  if (key === "operation") {
    return typeof value === "string" && OPERATIONS.has(value);
  }
  if (key === "status_class") {
    return typeof value === "string" && STATUS_CLASSES.has(value);
  }
  if (key === "duration_ms") {
    return Number.isInteger(value) && Number(value) >= 0 && Number(value) <= 300_000;
  }
  if (key === "available_actions") {
    return Number.isInteger(value) && Number(value) >= 0 && Number(value) <= 4;
  }
  if (key === "value") {
    return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 600_000;
  }
  return false;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.getPrototypeOf(value) === Object.prototype
  );
}

function hasExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
): boolean {
  const keys = Object.keys(value).sort();
  const required = [...expected].sort();
  return keys.length === required.length && keys.every((key, index) => key === required[index]);
}
