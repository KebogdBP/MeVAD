import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { CheckboxField, NumberField, SelectField } from "./field";

function NumberFieldDemo() {
  const [value, setValue] = useState(30);
  return (
    <NumberField
      label="Clip start"
      value={value}
      min={0}
      max={120}
      hint="Time in seconds."
      onChange={setValue}
    />
  );
}

function CheckboxFieldDemo() {
  const [checked, setChecked] = useState(true);
  return (
    <CheckboxField
      label="Extract audio only"
      checked={checked}
      onChange={setChecked}
    />
  );
}

const meta = {
  title: "Components/Fields",
  component: SelectField,
  args: {
    label: "Quality",
    value: "best",
    values: ["best", "1080p", "720p"],
    onChange: () => undefined,
  },
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof SelectField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Select: Story = {
  args: {
    label: "Quality",
    value: "best",
    values: ["best", "1080p", "720p"],
    hint: "Best available quality is selected by default.",
    onChange: () => undefined,
  },
};

export const SelectError: Story = {
  args: {
    label: "Format",
    value: "",
    values: ["", "mp4", "webm"],
    error: "Choose an output format.",
    onChange: () => undefined,
  },
};

export const Number = {
  render: () => <NumberFieldDemo />,
} satisfies Story;

export const Checkbox = {
  render: () => <CheckboxFieldDemo />,
} satisfies Story;
