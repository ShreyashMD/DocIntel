import React from "react";
import { clsx } from "clsx";

export function Card({
  children,
  className,
  padding = true,
}: {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}) {
  return (
    <div
      className={clsx(
        "bg-white rounded-lg border border-neutral-200 shadow-card",
        padding && "p-5",
        className
      )}
    >
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  icon: Icon,
  delta,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  delta?: { value: number; label?: string };
  color?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-neutral-500">{label}</p>
        <div className="w-8 h-8 rounded-lg bg-neutral-50 flex items-center justify-center">
          <Icon className="w-4 h-4 text-neutral-400" />
        </div>
      </div>
      <p className="text-2xl font-semibold text-neutral-900 tracking-tight">{value}</p>
      {delta && (
        <p className={clsx(
          "text-xs mt-1.5 font-medium",
          delta.value >= 0 ? "text-emerald-600" : "text-red-600"
        )}>
          {delta.value >= 0 ? "↑" : "↓"} {Math.abs(delta.value)}%{" "}
          <span className="text-neutral-400 font-normal">{delta.label ?? "vs last week"}</span>
        </p>
      )}
    </div>
  );
}

export function Section({
  title,
  description,
  action,
  children,
  className,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("space-y-4", className)}>
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold text-neutral-900">{title}</h2>
          {description && <p className="text-sm text-neutral-500 mt-0.5">{description}</p>}
        </div>
        {action && <div>{action}</div>}
      </div>
      {children}
    </section>
  );
}
