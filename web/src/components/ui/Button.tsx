import React from "react";
import { clsx } from "clsx";

type Variant = "primary" | "secondary" | "danger" | "ghost" | "outline";
type Size    = "xs" | "sm" | "md" | "lg";

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 shadow-xs",
  secondary:
    "bg-neutral-800 text-white hover:bg-neutral-700 active:bg-neutral-900 shadow-xs",
  outline:
    "bg-white text-neutral-700 border border-neutral-300 hover:bg-neutral-50 hover:border-neutral-400 shadow-xs",
  danger:
    "bg-red-600 text-white hover:bg-red-700 active:bg-red-800 shadow-xs",
  ghost:
    "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 active:bg-neutral-200",
};

const sizes: Record<Size, string> = {
  xs: "h-7  px-2.5 text-xs  gap-1.5 rounded",
  sm: "h-8  px-3   text-xs  gap-2   rounded-md",
  md: "h-9  px-4   text-sm  gap-2   rounded-md",
  lg: "h-10 px-5   text-sm  gap-2.5 rounded-md font-semibold",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  icon,
  children,
  className,
  disabled,
  ...props
}: Props) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center font-medium select-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        "transition-colors duration-100",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {loading ? (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin flex-shrink-0" />
      ) : icon ? (
        <span className="flex-shrink-0">{icon}</span>
      ) : null}
      {children}
    </button>
  );
}
