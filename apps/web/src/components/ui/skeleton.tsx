import type { HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLSpanElement> {
  width?: string;
}

export function Skeleton({
  width,
  className,
  style,
  ...props
}: SkeletonProps) {
  const classes = ["ui-skeleton", className].filter(Boolean).join(" ");

  return (
    <span
      className={classes}
      aria-hidden="true"
      style={{ ...style, width }}
      {...props}
    />
  );
}
