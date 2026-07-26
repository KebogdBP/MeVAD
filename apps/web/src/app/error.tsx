"use client";

import { useEffect } from "react";

import { trackTelemetry } from "@/lib/telemetry-client";
import { safeErrorName } from "@/lib/telemetry";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    trackTelemetry("client_error", {
      source: "react-boundary",
      error_name: safeErrorName(error),
    });
  }, [error]);

  return (
    <main className="error-page">
      <div>
        <span>Workspace interrupted</span>
        <h1>Something went wrong.</h1>
        <p>
          Monitoring never includes the submitted media URL. You can safely retry
          the current screen.
        </p>
        <button type="button" className="hero-primary" onClick={reset}>
          Try again
        </button>
      </div>
    </main>
  );
}
