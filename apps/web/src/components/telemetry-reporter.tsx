"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useReportWebVitals } from "next/web-vitals";

import { trackTelemetry } from "@/lib/telemetry-client";

export function TelemetryReporter() {
  const pathname = usePathname();

  useEffect(() => {
    trackTelemetry("page_view");
  }, [pathname]);

  useReportWebVitals((metric) => {
    if (!["CLS", "FCP", "INP", "LCP", "TTFB"].includes(metric.name)) return;

    trackTelemetry("web_vital", {
      metric: metric.name,
      rating: metric.rating,
      value: Math.max(0, Math.min(600_000, metric.value)),
      navigation_type: metric.navigationType ?? "unknown",
    });
  });

  return null;
}
