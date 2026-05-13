"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  MessageSquare, FileText, Search, History,
  ArrowRight, Clock, Network, TrendingUp,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { queryApi, docApi } from "@/lib/api";
import { StatusBadge } from "@/components/ui/Badge";
import type { Document, HistoryEntry } from "@/types";

const actions = [
  {
    href:  "/app/ask",
    icon:  MessageSquare,
    label: "Ask AI",
    desc:  "Get answers with citations",
    primary: true,
  },
  {
    href:  "/app/documents",
    icon:  FileText,
    label: "Documents",
    desc:  "Upload & manage files",
    primary: false,
  },
  {
    href:  "/app/search",
    icon:  Search,
    label: "Semantic Search",
    desc:  "Similarity-based search",
    primary: false,
  },
  {
    href:  "/app/graph",
    icon:  Network,
    label: "Knowledge Graph",
    desc:  "Visual entity explorer",
    primary: false,
  },
];

function EmptyState({ icon: Icon, label, action, href }: {
  icon: React.ElementType; label: string; action: string; href: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center mb-3">
        <Icon className="w-4.5 h-4.5 text-neutral-300" />
      </div>
      <p className="text-sm text-neutral-400 mb-2">{label}</p>
      <Link href={href} className="text-xs text-brand-600 hover:text-brand-700 font-semibold transition-colors">
        {action} →
      </Link>
    </div>
  );
}

export default function AppHome() {
  const { user } = useAuth();
  const [recentDocs, setRecentDocs]       = useState<Document[]>([]);
  const [recentHistory, setRecentHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    docApi.list().then((d) => setRecentDocs(d.slice(0, 5))).catch(() => {});
    queryApi.history(5).then(setRecentHistory).catch(() => {});
  }, []);

  const firstName = user?.full_name?.split(" ")[0] || "there";
  const hour      = new Date().getHours();
  const greeting  = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const readyDocs     = recentDocs.filter((d) => d.status === "ready").length;
  const totalDocs     = recentDocs.length;
  const totalQueries  = recentHistory.length;

  return (
    <div className="flex flex-col min-h-full">

      {/* ── Page header ──────────────────────────────────────────────── */}
      <div className="bg-white border-b border-neutral-200 px-8 py-5 flex-shrink-0">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-6">
          <div>
            <p className="text-xs font-medium text-neutral-400 mb-1">
              {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            </p>
            <h1 className="text-xl font-bold text-neutral-900 tracking-tight">
              {greeting}, {firstName}
            </h1>
          </div>

          <div className="hidden sm:flex items-center divide-x divide-neutral-200 bg-neutral-50 border border-neutral-200 rounded-lg overflow-hidden">
            {[
              { label: "Total Documents",  value: totalDocs,    icon: FileText },
              { label: "Ready",            value: readyDocs,    icon: TrendingUp },
              { label: "Recent Queries",   value: totalQueries, icon: MessageSquare },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center gap-2.5 px-4 py-3">
                <Icon className="w-4 h-4 text-brand-500" />
                <div>
                  <p className="text-lg font-bold text-neutral-900 tabular-nums leading-none">{value}</p>
                  <p className="text-[10px] text-neutral-400 leading-none mt-0.5">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Content ──────────────────────────────────────────────────── */}
      <div className="flex-1 px-8 py-7 max-w-5xl mx-auto w-full">

        {/* Quick actions */}
        <div className="mb-8">
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Quick actions</h2>
          <div className="grid grid-cols-4 gap-3">
            {actions.map((a) => (
              <Link
                key={a.href}
                href={a.href}
                className={`group flex flex-col gap-3 p-5 rounded-lg border transition-all duration-150 hover:shadow-elevated hover:-translate-y-px ${
                  a.primary
                    ? "bg-brand-600 border-brand-700 hover:bg-brand-700"
                    : "bg-white border-neutral-200 hover:border-brand-200"
                }`}
              >
                <div className={`w-8 h-8 rounded-md flex items-center justify-center ${
                  a.primary ? "bg-white/20" : "bg-brand-50"
                }`}>
                  <a.icon className={`w-4 h-4 ${a.primary ? "text-white" : "text-brand-600"}`} />
                </div>
                <div>
                  <p className={`text-sm font-semibold ${a.primary ? "text-white" : "text-neutral-800"}`}>
                    {a.label}
                  </p>
                  <p className={`text-xs mt-0.5 ${a.primary ? "text-blue-200" : "text-neutral-400"}`}>
                    {a.desc}
                  </p>
                </div>
                <ArrowRight className={`w-3.5 h-3.5 mt-auto self-end opacity-40 group-hover:opacity-80 transition-opacity ${
                  a.primary ? "text-white" : "text-neutral-400"
                }`} />
              </Link>
            ))}
          </div>
        </div>

        {/* Recent panels */}
        <div className="grid grid-cols-2 gap-6">

          {/* Recent documents */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Recent documents</h2>
              <Link
                href="/app/documents"
                className="text-xs text-brand-600 hover:text-brand-700 font-semibold transition-colors"
              >
                View all →
              </Link>
            </div>

            <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden shadow-card">
              {recentDocs.length === 0 ? (
                <EmptyState
                  icon={FileText}
                  label="No documents uploaded yet"
                  action="Upload your first file"
                  href="/app/documents"
                />
              ) : (
                <table className="w-full">
                  <tbody className="divide-y divide-neutral-100">
                    {recentDocs.map((d) => (
                      <tr key={d.id} className="hover:bg-neutral-50 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <div className="w-6 h-6 rounded bg-brand-50 flex items-center justify-center flex-shrink-0">
                              <FileText className="w-3 h-3 text-brand-500" />
                            </div>
                            <span className="text-sm text-neutral-800 truncate max-w-[180px] font-medium">
                              {d.filename}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <StatusBadge status={d.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Recent queries */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Recent queries</h2>
              <Link
                href="/app/history"
                className="text-xs text-brand-600 hover:text-brand-700 font-semibold transition-colors"
              >
                View all →
              </Link>
            </div>

            <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden shadow-card">
              {recentHistory.length === 0 ? (
                <EmptyState
                  icon={History}
                  label="No queries yet"
                  action="Ask your first question"
                  href="/app/ask"
                />
              ) : (
                <div className="divide-y divide-neutral-100">
                  {recentHistory.map((h) => (
                    <div key={h.id} className="px-4 py-3 hover:bg-neutral-50 transition-colors">
                      <p className="text-sm text-neutral-800 truncate font-medium">{h.question}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Clock className="w-3 h-3 text-neutral-300" />
                        <p className="text-xs text-neutral-400">
                          {new Date(h.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
