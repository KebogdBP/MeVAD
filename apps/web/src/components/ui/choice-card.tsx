import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ChoiceCardProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  selected: boolean;
  icon: ReactNode;
  label: string;
  description: string;
}

export function ChoiceCard({
  selected,
  icon,
  label,
  description,
  className,
  ...props
}: ChoiceCardProps) {
  const classes = [
    "ui-choice-card",
    "action-card",
    selected && "selected",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type="button"
      className={classes}
      aria-pressed={selected}
      {...props}
    >
      <b aria-hidden="true">{icon}</b>
      <span>{label}</span>
      <small>{description}</small>
    </button>
  );
}
