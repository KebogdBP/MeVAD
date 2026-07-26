import { safeErrorName } from "@/lib/telemetry";
import { trackTelemetry } from "@/lib/telemetry-client";

if (process.env.NEXT_PUBLIC_MEVAD_TELEMETRY_ENABLED === "true") {
  try {
    window.addEventListener("error", (event) => {
      trackTelemetry("client_error", {
        source: "window",
        error_name: safeErrorName(event.error),
      });
    });

    window.addEventListener("unhandledrejection", (event) => {
      trackTelemetry("client_error", {
        source: "promise",
        error_name: safeErrorName(event.reason),
      });
    });
  } catch {
    // Early monitoring must not delay or prevent hydration.
  }
}
