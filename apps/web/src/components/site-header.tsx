"use client";

import {
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

const navigation = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#safety", label: "Safety" },
] as const;

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    const desktop = window.matchMedia("(min-width: 901px)");
    const handleDesktop = (event: MediaQueryListEvent) => {
      if (event.matches) setMenuOpen(false);
    };

    document.addEventListener("keydown", handleKeyDown);
    desktop.addEventListener("change", handleDesktop);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      desktop.removeEventListener("change", handleDesktop);
    };
  }, [menuOpen]);

  return (
    <SiteHeaderView
      menuOpen={menuOpen}
      menuButtonRef={menuButtonRef}
      onMenuToggle={() => setMenuOpen((current) => !current)}
      onNavigate={() => setMenuOpen(false)}
    />
  );
}

interface SiteHeaderViewProps {
  menuOpen: boolean;
  menuButtonRef?: RefObject<HTMLButtonElement | null>;
  onMenuToggle: () => void;
  onNavigate: () => void;
}

export function SiteHeaderView({
  menuOpen,
  menuButtonRef,
  onMenuToggle,
  onNavigate,
}: SiteHeaderViewProps) {
  return (
    <header className="site-header">
      <a className="brand" href="#" aria-label="MeVAD home">
        <span className="brand-mark" aria-hidden="true">
          ↓
        </span>
        <span className="brand-copy">
          <strong>MeVAD</strong>
          <small>Video · Audio · Clips</small>
        </span>
      </a>

      <nav
        className="main-nav"
        id="main-navigation"
        aria-label="Main navigation"
        data-open={menuOpen || undefined}
      >
        {navigation.map((item) => (
          <a
            key={item.href}
            href={item.href}
            onClick={onNavigate}
          >
            {item.label}
          </a>
        ))}
        <a
          className="mobile-nav-cta"
          href="#workspace"
          onClick={onNavigate}
        >
          Open workspace
        </a>
      </nav>

      <ThemeToggle />
      <a className="header-cta" href="#workspace">
        Open workspace
        <span aria-hidden="true">↘</span>
      </a>
      <Button
        ref={menuButtonRef}
        className="mobile-nav-toggle"
        variant="icon"
        type="button"
        aria-expanded={menuOpen}
        aria-controls="main-navigation"
        aria-label={`${menuOpen ? "Close" : "Open"} navigation menu`}
        onClick={onMenuToggle}
      >
        <span aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
      </Button>
    </header>
  );
}
