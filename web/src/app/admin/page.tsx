"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, FileText, MessageSquare, Database, ArrowRight, AlertTriangle, Settings } from "lucide-react";
import { adminApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { OrgStats } from "@/types";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats]       = useState<OrgStats | null>(null);
  const [settings, setSettings] = useState<{ name?: string; llm_provider?: string; has_llm_key?: boolean } | null>(null);

  useEffect(() => {
    adminApi.stats().then(setStats).catch(() => {});
    adminApi.settings().then(setSettings).catch(() => {});
  }, []);

  const statCards = [
    { label: "Team Members",   value: stats?.users   ?? "—", icon: Users },
    { label: "Documents",      value: stats?.docs    ?? "—", icon: FileText },
    { label: "Chunks Indexed", value: stats?.chunks  ?? "—", icon: Database },
    { label: "Total Queries",  value: stats?.queries ?? "—", icon: MessageSquare },
  ];

  const orgName = settings?.name ?? "Your organization";

  return (
    <div className="flex flex-col min-h-full">

      {/* Page header */}
      <div className="page-header">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-brand-600 mb-0.5">Admin Console</p>
            <h1 className="page-header-title">{orgName}</h1>
            <p className="page-header-desc">
              Welcome back, {user?.full_name?.split(" ")[0]}. Here&apos;s your workspace overview.
            </p>
          </div>
        </div>
      </div>

      <div className="px-8 py-7 max-w-5xl mx-auto w-full">

        {/* LLM warning */}
        {settings && !settings.has_llm_key && (
          <div className="mb-6 flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg px-5 py-4">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-amber-900">LLM API key required</p>
              <p className="text-sm text-amber-700 mt-0.5">
                Add your {settings.llm_provider ?? "LLM"} API key in Settings to start analyzing documents.
              </p>
            </div>
            <Link href="/admin/settings">
              <button className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 hover:text-amber-900 flex-shrink-0 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-md transition-colors">
                <Settings className="w-3.5 h-3.5" /> Configure
              </button>
            </Link>
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {statCards.map((c) => (
            <div key={c.label} className="bg-white rounded-lg border border-neutral-200 shadow-card p-5">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-neutral-500">{c.label}</p>
                <div className="w-7 h-7 rounded-md bg-brand-50 flex items-center justify-center">
                  <c.icon className="w-3.5 h-3.5 text-brand-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-neutral-900 tracking-tight">{c.value}</p>
            </div>
          ))}
        </div>

        {/* Quick actions */}
        <div>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Quick actions</h2>
          <div className="grid grid-cols-3 gap-3">
            {[
              { href: "/admin/users",    label: "Manage Team",        desc: "Invite members, manage roles and access", icon: Users },
              { href: "/admin/settings", label: "LLM Settings",       desc: "Configure AI provider and API credentials", icon: Settings },
              { href: "/app",            label: "User Workspace",      desc: "Switch to the document analysis workspace", icon: MessageSquare },
            ].map((item) => (
              <Link key={item.href} href={item.href}
                className="group bg-white border border-neutral-200 rounded-lg p-5 hover:border-brand-200 hover:shadow-elevated transition-all duration-150">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-8 h-8 rounded-md bg-neutral-50 flex items-center justify-center border border-neutral-200">
                    <item.icon className="w-4 h-4 text-neutral-500" />
                  </div>
                  <ArrowRight className="w-4 h-4 text-neutral-200 group-hover:text-brand-500 transition-colors" />
                </div>
                <p className="text-sm font-semibold text-neutral-900 mb-0.5">{item.label}</p>
                <p className="text-xs text-neutral-400">{item.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
