"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const current = document.documentElement.dataset.theme;
    const frame = window.requestAnimationFrame(() => {
      setTheme(current === "dark" ? "dark" : "light");
    });

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleSystemTheme = (event: MediaQueryListEvent) => {
      if (window.localStorage.getItem("mevad-theme")) return;
      const nextTheme = event.matches ? "dark" : "light";
      applyTheme(nextTheme);
      setTheme(nextTheme);
    };

    media.addEventListener("change", handleSystemTheme);
    return () => {
      window.cancelAnimationFrame(frame);
      media.removeEventListener("change", handleSystemTheme);
    };
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "light" ? "dark" : "light";
    window.localStorage.setItem("mevad-theme", nextTheme);
    applyTheme(nextTheme);
    setTheme(nextTheme);
  }

  return (
    <Button
      className="theme-toggle"
      variant="icon"
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
      title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
    >
      <span aria-hidden="true">{theme === "light" ? "◐" : "☼"}</span>
    </Button>
  );
}
