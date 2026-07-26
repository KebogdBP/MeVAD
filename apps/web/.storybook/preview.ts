import { withThemeByDataAttribute } from "@storybook/addon-themes";
import type { Preview } from "@storybook/nextjs-vite";

import "../src/app/tokens.css";
import "../src/app/globals.css";

const preview: Preview = {
  decorators: [
    withThemeByDataAttribute({
      themes: {
        light: "light",
        dark: "dark",
      },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
  ],
  parameters: {
    a11y: {
      test: "error",
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    layout: "centered",
    options: {
      storySort: {
        order: ["Foundations", "Components", "Patterns"],
      },
    },
  },
  tags: ["autodocs"],
};

export default preview;
