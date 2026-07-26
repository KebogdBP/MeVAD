interface ProgressProps {
  value: number;
  label: string;
  className?: string;
}

export function Progress({ value, label, className }: ProgressProps) {
  const normalizedValue = Math.min(100, Math.max(0, value));
  const classes = ["ui-progress", "progress-track", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={classes}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={normalizedValue}
    >
      <span style={{ width: `${normalizedValue}%` }} />
    </div>
  );
}
