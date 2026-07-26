import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Badge } from "./badge";
import { Button } from "./button";
import { SelectField } from "./field";
import { Progress } from "./progress";

describe("UI primitives", () => {
  it("exposes a disabled busy state for loading buttons", () => {
    const markup = renderToStaticMarkup(
      <Button loading loadingLabel="Analyzing">
        Analyze
      </Button>,
    );

    expect(markup).toContain('aria-busy="true"');
    expect(markup).toContain("disabled");
    expect(markup).toContain("Analyzing");
  });

  it("clamps progress values and exposes progress semantics", () => {
    const markup = renderToStaticMarkup(<Progress value={140} label="Job progress" />);

    expect(markup).toContain('role="progressbar"');
    expect(markup).toContain('aria-valuenow="100"');
    expect(markup).toContain("width:100%");
  });

  it("connects field labels to their controls", () => {
    const markup = renderToStaticMarkup(
      <SelectField
        label="Quality"
        value="best"
        values={["best", "1080"]}
        onChange={() => undefined}
      />,
    );

    const labelTarget = markup.match(/<label for="([^"]+)"/)?.[1];
    expect(labelTarget).toBeTruthy();
    expect(markup).toContain(`id="${labelTarget}"`);
  });

  it("renders semantic badge variants", () => {
    const markup = renderToStaticMarkup(<Badge tone="success">Ready</Badge>);

    expect(markup).toContain("ui-badge--success");
    expect(markup).toContain("Ready");
  });
});
