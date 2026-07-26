import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { Input } from "./field";

const meta = {
  title: "Components/Input",
  component: Input,
  args: {
    type: "url",
    placeholder: "Paste a supported media URL",
    "aria-label": "Media URL",
  },
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Invalid: Story = {
  args: {
    invalid: true,
    defaultValue: "not-a-url",
    "aria-describedby": "input-error",
  },
  render: (args) => (
    <div className="storybook-input">
      <Input {...args} />
      <small id="input-error">Enter a complete URL.</small>
    </div>
  ),
};

export const Disabled: Story = {
  args: {
    disabled: true,
    defaultValue: "https://example.com/video",
  },
};
