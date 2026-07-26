import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { Skeleton } from "./skeleton";

const meta = {
  title: "Components/Skeleton",
  component: Skeleton,
  args: {
    width: "260px",
  },
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Text: Story = {};

export const Control: Story = {
  args: {
    className: "skeleton-control",
    width: "320px",
  },
};

export const Card: Story = {
  args: {
    className: "skeleton-thumbnail",
    width: "320px",
  },
};
