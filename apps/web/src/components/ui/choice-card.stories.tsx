import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { ChoiceCard } from "./choice-card";

const meta = {
  title: "Components/Choice Card",
  component: ChoiceCard,
  args: {
    selected: false,
    icon: "↓",
    label: "Video",
    description: "MP4, WebM or source quality",
  },
} satisfies Meta<typeof ChoiceCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Selected: Story = {
  args: {
    selected: true,
  },
};

export const Disabled: Story = {
  args: {
    disabled: true,
    description: "Not available",
  },
};
