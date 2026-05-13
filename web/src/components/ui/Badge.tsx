import React from "react";
import { clsx } from "clsx";

type Color = "violet" | "green" | "amber" | "red" | "gray" | "blue" | "orange";

const dot: Record<Color, string> = {
  violet: "bg-brand-500",
  blue:   "bg-blue-500",
  green:  "bg-emerald-500",
  amber:  "bg-amber-400",
  orange: "bg-orange-500",
  red:    "bg-red-500",
  gray:   "bg-neutral-400",
};

const pill: Record<Color, string> = {
  violet: "bg-brand-50 text-brand-700 ring-brand-200",
  blue:   "bg-blue-50 text-blue-700 ring-blue-200",
  green:  "bg-emerald-50 text-emerald-700 ring-emerald-200",
  amber:  "bg-amber-50 text-amber-700 ring-amber-200",
  orange: "bg-orange-50 text-orange-700 ring-orange-200",
  red:    "bg-red-50 text-red-700 ring-red-200",
  gray:   "bg-neutral-100 text-neutral-600 ring-neutral-200",
};

export function Badge({
  children,
  color = "gray",
  dot: showDot = false,
  className,
}: {
  children: React.ReactNode;
  color?: Color;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5",
        "rounded-full text-xs font-medium ring-1 ring-inset",
        pill[color],
        className
      )}
    >
      {showDot && (
        <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", dot[color])} />
      )}
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: Color; label: string }> = {
    ready:     { color: "green",  label: "Ready" },
    ingesting: { color: "blue",   label: "Processing" },
    pending:   { color: "amber",  label: "Pending" },
    failed:    { color: "red",    label: "Failed" },
    active:    { color: "green",  label: "Active" },
    suspended: { color: "red",    label: "Suspended" },
  };
  const info = map[status] ?? { color: "gray" as Color, label: status };
  return <Badge color={info.color} dot>{info.label}</Badge>;
}

export function RoleBadge({ role }: { role: string }) {
  const map: Record<string, Color> = {
    superadmin: "violet",
    org_admin:  "blue",
    manager:    "orange",
    user:       "gray",
    viewer:     "gray",
  };
  const labels: Record<string, string> = {
    superadmin: "Super Admin",
    org_admin:  "Admin",
    manager:    "Manager",
    user:       "Member",
    viewer:     "Viewer",
  };
  return <Badge color={map[role] ?? "gray"}>{labels[role] ?? role}</Badge>;
}
