import React from "react";
import { clsx } from "clsx";

interface Props extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "prefix"> {
  label?: string;
  hint?: string;
  error?: string;
  startIcon?: React.ReactNode;
}

export function Input({ label, hint, error, startIcon, className, id, ...props }: Props) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-neutral-700">
          {label}
        </label>
      )}
      <div className="relative">
        {startIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 pointer-events-none">
            {startIcon}
          </div>
        )}
        <input
          id={inputId}
          {...props}
          className={clsx(
            "w-full h-9 rounded-lg border bg-white text-sm text-neutral-900",
            "placeholder:text-neutral-400",
            "transition-colors duration-100",
            "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-0 focus:border-brand-500",
            error
              ? "border-red-400 focus:ring-red-500 focus:border-red-500"
              : "border-neutral-200 hover:border-neutral-300",
            "disabled:bg-neutral-50 disabled:text-neutral-400 disabled:cursor-not-allowed",
            startIcon ? "pl-9 pr-3" : "px-3",
            className
          )}
        />
      </div>
      {hint && !error && <p className="text-xs text-neutral-400">{hint}</p>}
      {error && <p className="text-xs text-red-600 flex items-center gap-1">{error}</p>}
    </div>
  );
}

export function Textarea({
  label, hint, error, className, id, ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; hint?: string; error?: string }) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-neutral-700">
          {label}
        </label>
      )}
      <textarea
        id={inputId}
        {...props}
        className={clsx(
          "w-full rounded-lg border bg-white text-sm text-neutral-900 px-3 py-2",
          "placeholder:text-neutral-400 resize-none",
          "transition-colors duration-100",
          "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-0 focus:border-brand-500",
          error
            ? "border-red-400"
            : "border-neutral-200 hover:border-neutral-300",
          "disabled:bg-neutral-50 disabled:cursor-not-allowed",
          className
        )}
      />
      {hint && !error && <p className="text-xs text-neutral-400">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
