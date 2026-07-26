import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SiteHeaderView } from "./site-header";

describe("SiteHeaderView", () => {
  it("connects the mobile trigger to the navigation", () => {
    const markup = renderToStaticMarkup(
      <SiteHeaderView
        menuOpen={false}
        onMenuToggle={() => undefined}
        onNavigate={() => undefined}
      />,
    );

    expect(markup).toContain('aria-controls="main-navigation"');
    expect(markup).toContain('aria-expanded="false"');
    expect(markup).toContain('aria-label="Open navigation menu"');
  });

  it("exposes the open state and an accessible close label", () => {
    const markup = renderToStaticMarkup(
      <SiteHeaderView
        menuOpen
        onMenuToggle={() => undefined}
        onNavigate={() => undefined}
      />,
    );

    expect(markup).toContain('data-open="true"');
    expect(markup).toContain('aria-expanded="true"');
    expect(markup).toContain('aria-label="Close navigation menu"');
  });
});
