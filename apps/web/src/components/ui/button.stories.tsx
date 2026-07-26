import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { Button } from "./button";

const meta = {
  title: "Components/Button",
  component: Button,
  args: {
    children: "Analyze media",
  },
  argTypes: {
    onClick: { action: "clicked" },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: { variant: "primary", size: "lg" },
};

export const Secondary: Story = {
  args: { variant: "secondary" },
};

export const Ghost: Story = {
  args: { variant: "ghost" },
};

export const Loading: Story = {
  args: {
    variant: "primary",
    loading: true,
    loadingLabel: "Analyzing…",
  },
};

export const Disabled: Story = {
  args: { disabled: true },
};

export const Icon: Story = {
  args: {
    variant: "icon",
    children: "☾",
    "aria-label": "Switch color theme",
  },
};
