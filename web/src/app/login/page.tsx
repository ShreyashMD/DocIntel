"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText, BarChart2, Shield } from "lucide-react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login }               = useAuth();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-white">

      {/* ── Left brand panel ─────────────────────────────────────────── */}
      <div
        className="hidden lg:flex lg:w-[460px] flex-col relative overflow-hidden flex-shrink-0"
        style={{ background: "linear-gradient(160deg, #1e40af 0%, #1d4ed8 50%, #2563eb 100%)" }}
      >
        {/* Subtle pattern overlay */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              "radial-gradient(circle at 2px 2px, rgba(255,255,255,0.5) 1px, transparent 0)",
            backgroundSize: "28px 28px",
          }}
        />

        <div className="relative z-10 flex flex-col h-full p-12">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
              <svg className="w-4.5 h-4.5 text-white w-5 h-5" viewBox="0 0 16 16" fill="none">
                <path d="M3 4h10M3 8h10M3 12h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <span className="font-bold text-white text-base tracking-tight">DocIntel</span>
          </div>

          {/* Middle — value props */}
          <div className="flex-1 flex flex-col justify-center gap-8">
            <div>
              <h2 className="text-3xl font-bold text-white leading-tight tracking-tight">
                Intelligent document<br />analysis at scale
              </h2>
              <p className="text-blue-200 text-sm mt-3 leading-relaxed max-w-xs">
                Extract insights from thousands of documents in seconds with AI-powered search and analysis.
              </p>
            </div>

            <div className="space-y-4">
              {[
                { icon: FileText,  title: "Smart Document Ingestion",    desc: "PDF, Word, Excel, and more — indexed automatically" },
                { icon: BarChart2, title: "AI-Powered Q&A",               desc: "Natural language questions with source citations" },
                { icon: Shield,    title: "Enterprise Security",          desc: "Per-organisation isolation with encrypted key storage" },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{title}</p>
                    <p className="text-xs text-blue-200 mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom attribution */}
          <div className="flex items-center gap-3 pt-6 border-t border-white/15">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center ring-2 ring-white/20">
              <span className="text-xs font-bold text-white">SD</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Shreyash Deokate</p>
              <p className="text-xs text-blue-200">Platform Administrator</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-neutral-50">
        <div className="w-full max-w-[400px] animate-fade-in">

          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="none">
                <path d="M3 4h10M3 8h10M3 12h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <span className="font-bold text-neutral-900 text-base">DocIntel</span>
          </div>

          {/* Form card */}
          <div className="bg-white rounded-xl border border-neutral-200 shadow-card p-8">

            <div className="mb-7">
              <h1 className="text-xl font-bold text-neutral-900 tracking-tight">Sign in to DocIntel</h1>
              <p className="text-neutral-500 text-sm mt-1">Enter your credentials to access your workspace</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-neutral-600">Work email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    autoComplete="email"
                    className="input-base"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-neutral-600">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                    className="input-base"
                  />
                </div>
              </div>

              {error && (
                <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2.5">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full h-10 rounded-md bg-brand-600 hover:bg-brand-700 active:bg-brand-800 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-xs"
              >
                {loading ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : (
                  <>Sign in <ArrowRight className="w-4 h-4" /></>
                )}
              </button>
            </form>
          </div>

          <p className="text-center text-sm text-neutral-500 mt-5">
            No workspace?{" "}
            <Link href="/register" className="text-brand-600 hover:text-brand-700 font-semibold transition-colors">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
