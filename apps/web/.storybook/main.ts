import type { StorybookConfig } from "@storybook/nextjs-vite";

const config = {
  stories: ["../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"],
  addons: [
    "@storybook/addon-docs",
    "@storybook/addon-a11y",
    "@storybook/addon-themes",
  ],
  framework: {
    name: "@storybook/nextjs-vite",
    options: {},
  },
  docs: {
    autodocs: "tag",
  },
} satisfies StorybookConfig;

export default config;
