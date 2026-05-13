"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Users, FileText, MessageSquare, ArrowUpRight, Activity, Zap } from "lucide-react";
import { superApi } from "@/lib/api";
import type { PlatformStats } from "@/types";

export default function SuperAdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);

  useEffect(() => {
    superApi.stats().then(setStats).catch(() => {});
  }, []);

  const statCards = [
    { label: "Organizations", value: stats?.orgs    ?? "—", icon: Building2 },
    { label: "Total users",   value: stats?.users   ?? "—", icon: Users },
    { label: "Documents",     value: stats?.docs    ?? "—", icon: FileText },
    { label: "Queries run",   value: stats?.queries ?? "—", icon: MessageSquare },
  ];

  const metrics = stats?.runtime_metrics ?? {};

  return (
    <div className="px-8 py-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-medium text-emerald-600 uppercase tracking-widest">Live</span>
          </div>
          <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">Platform Overview</h1>
          <p className="text-neutral-500 text-sm mt-1">Monitor all organizations and platform health</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-8 px-3 rounded-lg bg-neutral-100 flex items-center gap-2 text-xs text-neutral-500">
            <Zap className="w-3.5 h-3.5 text-brand-500" />
            Super Admin
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-9">
        {statCards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-neutral-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium text-neutral-500">{c.label}</p>
              <div className="w-7 h-7 rounded-md bg-neutral-50 flex items-center justify-center">
                <c.icon className="w-3.5 h-3.5 text-neutral-400" />
              </div>
            </div>
            <p className="text-2xl font-semibold text-neutral-900 tracking-tight">{c.value}</p>
          </div>
        ))}
      </div>

      {/* Runtime metrics */}
      {Object.keys(metrics).length > 0 && (
        <div className="mb-9">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-neutral-400" />
            <h2 className="text-sm font-semibold text-neutral-700">Runtime metrics</h2>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(metrics).map(([k, v]) => (
              <div key={k} className="bg-white border border-neutral-200 rounded-xl px-4 py-3.5">
                <p className="text-[11px] font-medium text-neutral-400 uppercase tracking-wider mb-1">
                  {k.replace(/_/g, " ")}
                </p>
                <p className="text-xl font-semibold text-neutral-900 tracking-tight">{String(v)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div>
        <h2 className="text-sm font-semibold text-neutral-700 mb-4">Management</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            {
              href: "/superadmin/orgs",
              label: "Organizations",
              icon: Building2,
              desc: "Create, manage, or suspend company workspaces",
              stat: `${stats?.orgs ?? 0} orgs`,
            },
            {
              href: "/superadmin/users",
              label: "All users",
              icon: Users,
              desc: "View every user across all organizations",
              stat: `${stats?.users ?? 0} users`,
            },
          ].map((item) => (
            <Link key={item.href} href={item.href}
              className="group bg-white border border-neutral-200 rounded-xl p-6 hover:border-neutral-300 hover:shadow-elevated transition-all duration-150 flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-neutral-50 flex items-center justify-center flex-shrink-0">
                  <item.icon className="w-5 h-5 text-neutral-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-sm font-semibold text-neutral-900">{item.label}</p>
                    <span className="text-[11px] font-medium text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded-md">
                      {item.stat}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-400">{item.desc}</p>
                </div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-neutral-200 group-hover:text-neutral-400 transition-colors mt-0.5 flex-shrink-0" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
