import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { SiteHeaderView } from "./site-header";

const meta = {
  title: "Patterns/Site Header",
  component: SiteHeaderView,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    menuOpen: false,
    onMenuToggle: () => undefined,
    onNavigate: () => undefined,
  },
} satisfies Meta<typeof SiteHeaderView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Desktop: Story = {};

export const MenuClosed: Story = {};

export const MenuOpen: Story = {
  args: {
    menuOpen: true,
  },
};
