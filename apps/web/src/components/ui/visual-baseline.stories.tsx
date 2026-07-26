import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { Badge } from "./badge";
import { Button } from "./button";
import { CheckboxField, NumberField, SelectField } from "./field";
import { Progress } from "./progress";

const meta = {
  title: "Patterns/Visual Baseline",
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const ComponentMatrix: Story = {
  render: () => (
    <main className="storybook-baseline">
      <section className="workspace-card storybook-baseline__card">
        <div>
          <p className="eyebrow">Phase 7 quality baseline</p>
          <h1>Reusable workspace states</h1>
          <p className="support-copy">
            A deterministic surface for light/dark review and responsive snapshots.
          </p>
        </div>

        <div className="storybook-row">
          <Button variant="primary">Analyze media</Button>
          <Button variant="secondary">Download</Button>
          <Button variant="ghost">Reset</Button>
          <Button loading loadingLabel="Analyzing…">
            Analyze
          </Button>
          <Button disabled>Unavailable</Button>
        </div>

        <div className="storybook-form-grid">
          <SelectField
            label="Quality"
            value="best"
            values={["best", "1080p", "720p"]}
            onChange={() => undefined}
          />
          <NumberField
            label="Clip start"
            value={30}
            onChange={() => undefined}
          />
          <CheckboxField
            label="Extract audio"
            checked
            onChange={() => undefined}
          />
        </div>

        <div className="storybook-row">
          <Badge>Queued</Badge>
          <Badge tone="accent">Analyzing</Badge>
          <Badge tone="success">Ready</Badge>
          <Badge tone="warning">Processing</Badge>
          <Badge tone="danger">Failed</Badge>
        </div>

        <div className="storybook-progress">
          <span>Conversion progress</span>
          <Progress value={64} label="Conversion progress" />
        </div>
      </section>
    </main>
  ),
};
