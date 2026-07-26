import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { Badge } from "./badge";
import { Progress } from "./progress";

const meta = {
  title: "Components/Feedback",
  component: Badge,
  args: {
    children: "Queued",
  },
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const BadgeTones: Story = {
  render: () => (
    <div className="storybook-row">
      <Badge>Queued</Badge>
      <Badge tone="accent">Analyzing</Badge>
      <Badge tone="success">Ready</Badge>
      <Badge tone="warning">Processing</Badge>
      <Badge tone="danger">Failed</Badge>
    </div>
  ),
};

export const JobProgress: Story = {
  render: () => (
    <div className="storybook-progress">
      <Badge tone="warning">Processing · 64%</Badge>
      <Progress value={64} label="Media job progress" />
    </div>
  ),
};
