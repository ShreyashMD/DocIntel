"use client";
import { useEffect, useState } from "react";
import {
  Save, Key, Cpu, CheckCircle2, XCircle, Loader2,
  Eye, EyeOff, ShieldCheck, Vault, GitMerge,
} from "lucide-react";
import { adminApi } from "@/lib/api";
import type { Org } from "@/types";

const PROVIDERS = [
  { value: "gemini",    label: "Google Gemini",  desc: "gemini-2.5-flash + gemini-embedding-001" },
  { value: "openai",    label: "OpenAI",          desc: "GPT-4o + text-embedding-3-large" },
  { value: "anthropic", label: "Anthropic",       desc: "Claude Opus 4 (needs companion embedder)" },
  { value: "nvidia",    label: "NVIDIA NIM",      desc: "Llama 3.1 70B + nv-embedqa-e5-v5" },
  { value: "ollama",    label: "Ollama (local)",  desc: "Self-hosted, no API key needed" },
];

const PIPELINE_MODES = [
  {
    value: "single",
    label: "Single LLM",
    badge: "Default",
    desc: "One model generates the answer directly from the retrieved context. Fast and cost-efficient.",
    detail: [
      "Question + context → LLM → Answer",
    ],
  },
  {
    value: "writer_reviewer",
    label: "Writer + Reviewer",
    badge: "More accurate",
    desc: "Two sequential LLM calls: a writer drafts the answer, then a reviewer fact-checks, fills gaps, and corrects citations.",
    detail: [
      "Question + context → Writer LLM → Draft",
      "Draft + context → Reviewer LLM → Final answer",
    ],
  },
] as const;

const KEY_PROVIDERS = [
  { value: "openai",    label: "OpenAI",       hasKey: (o: Org) => o.has_openai_key,    field: "openai_api_key",    placeholder: "sk-…" },
  { value: "gemini",    label: "Google Gemini",hasKey: (o: Org) => o.has_gemini_key,    field: "gemini_api_key",    placeholder: "AIza…" },
  { value: "anthropic", label: "Anthropic",    hasKey: (o: Org) => o.has_anthropic_key, field: "anthropic_api_key", placeholder: "sk-ant-…" },
  { value: "nvidia",    label: "NVIDIA NIM",   hasKey: (o: Org) => o.has_nvidia_key,    field: "nvidia_api_key",    placeholder: "nvapi-…" },
] as const;

type KeyStatus = "idle" | "testing" | "valid" | "invalid";

// Small saved/not-set badge
function KeyBadge({ saved }: { saved: boolean }) {
  return saved ? (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full ring-1 ring-emerald-200 flex-shrink-0">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Saved
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-400 bg-neutral-100 px-2 py-0.5 rounded-full flex-shrink-0">
      Not set
    </span>
  );
}

export default function SettingsPage() {
  const [org, setOrg]         = useState<Org | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError]     = useState("");

  // Active provider config
  const [llmProvider, setLlmProvider]     = useState("gemini");
  const [embedProvider, setEmbedProvider] = useState("");
  const [ollamaUrl, setOllamaUrl]         = useState("http://localhost:11434");
  const [pipelineMode, setPipelineMode]   = useState("single");

  // Per-provider key inputs (only populated when user types a new key)
  const [keys, setKeys] = useState<Record<string, string>>({
    openai_api_key: "", gemini_api_key: "", anthropic_api_key: "", nvidia_api_key: "",
  });
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});

  // Validate state
  const [keyStatus, setKeyStatus] = useState<KeyStatus>("idle");
  const [keyError, setKeyError]   = useState<string | null>(null);

  useEffect(() => {
    adminApi.settings().then((o) => {
      setOrg(o);
      setLlmProvider(o.llm_provider ?? "gemini");
      setEmbedProvider(o.embedding_provider ?? "");
      setOllamaUrl(o.ollama_url ?? "http://localhost:11434");
      setPipelineMode(o.pipeline_mode ?? "single");
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  function setKey(field: string, value: string) {
    setKeys((prev) => ({ ...prev, [field]: value }));
  }

  function toggleShow(field: string) {
    setShowKey((prev) => ({ ...prev, [field]: !prev[field] }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setSuccess(false); setSaving(true); setKeyStatus("idle");
    try {
      const payload: Record<string, string> = {
        llm_provider:  llmProvider,
        pipeline_mode: pipelineMode,
      };
      if (embedProvider)              payload.embedding_provider = embedProvider;
      if (llmProvider === "ollama")   payload.ollama_url         = ollamaUrl;
      // Only include keys the user has actually typed
      for (const [field, val] of Object.entries(keys)) {
        if (val.trim()) payload[field] = val.trim();
      }
      const updated = await adminApi.updateSettings(payload);
      setOrg(updated);
      setKeys({ openai_api_key: "", gemini_api_key: "", anthropic_api_key: "", nvidia_api_key: "" });
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  async function testKey() {
    setKeyStatus("testing"); setKeyError(null);
    try {
      const res = await adminApi.validateKey();
      setKeyStatus(res.valid ? "valid" : "invalid");
      setKeyError(res.error);
    } catch {
      setKeyStatus("invalid");
      setKeyError("Could not reach the validation endpoint.");
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="w-5 h-5 text-brand-500 animate-spin" />
    </div>
  );

  const activeLabel = PROVIDERS.find((p) => p.value === llmProvider)?.label ?? llmProvider;

  return (
    <div className="flex flex-col min-h-full">
    <div className="page-header">
      <h1 className="page-header-title">LLM Settings</h1>
      <p className="page-header-desc">Configure AI providers for your organisation</p>
    </div>
    <div className="px-8 py-7 max-w-2xl mx-auto w-full space-y-5">

      <form onSubmit={save} className="space-y-6">

        {/* ── Active Provider ─────────────────────────────────────────────── */}
        <div className="bg-white border border-neutral-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-neutral-400" />
              <h2 className="text-sm font-semibold text-neutral-700">Active provider</h2>
            </div>
            <button
              type="button"
              onClick={testKey}
              disabled={keyStatus === "testing" || llmProvider === "ollama"}
              className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-neutral-200 text-xs font-medium text-neutral-600 hover:bg-neutral-50 hover:border-neutral-300 transition-all disabled:opacity-40"
            >
              {keyStatus === "testing"
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <ShieldCheck className="w-3.5 h-3.5" />}
              {keyStatus === "testing" ? "Testing…" : "Validate key"}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 mb-4">
            {PROVIDERS.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setLlmProvider(p.value)}
                className={`text-left px-3 py-3 rounded-lg border transition-all ${
                  llmProvider === p.value
                    ? "border-brand-500 bg-brand-50 ring-1 ring-brand-300"
                    : "border-neutral-200 hover:border-neutral-300 bg-white"
                }`}
              >
                <p className={`text-sm font-medium ${llmProvider === p.value ? "text-brand-700" : "text-neutral-800"}`}>
                  {p.label}
                </p>
                <p className="text-xs text-neutral-400 mt-0.5">{p.desc}</p>
              </button>
            ))}
          </div>

          {/* Validation result */}
          {keyStatus === "valid" && (
            <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2.5">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              {activeLabel} API key is valid and working.
            </div>
          )}
          {keyStatus === "invalid" && (
            <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>Validation failed{keyError ? `: ${keyError}` : "."}</span>
            </div>
          )}

          {/* Anthropic companion */}
          {llmProvider === "anthropic" && (
            <div className="mt-4 pt-4 border-t border-neutral-100 space-y-3">
              <p className="text-xs text-neutral-500">
                Anthropic doesn&apos;t provide embeddings. Select a companion embedding provider.
              </p>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-neutral-700">Embedding provider</label>
                <select
                  value={embedProvider}
                  onChange={(e) => setEmbedProvider(e.target.value)}
                  className="h-9 w-full rounded-lg border border-neutral-200 px-3 text-sm text-neutral-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="">Select…</option>
                  <option value="openai">OpenAI (uses saved OpenAI key)</option>
                  <option value="ollama">Ollama (local)</option>
                </select>
              </div>
            </div>
          )}

          {/* Ollama URL */}
          {llmProvider === "ollama" && (
            <div className="mt-4 pt-4 border-t border-neutral-100">
              <label className="text-sm font-medium text-neutral-700 block mb-1.5">Ollama server URL</label>
              <input
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://localhost:11434"
                className="h-9 w-full rounded-lg border border-neutral-200 bg-white px-3 text-sm text-neutral-700 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          )}
        </div>

        {/* ── API Key Vault ────────────────────────────────────────────────── */}
        <div className="bg-white border border-neutral-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-1">
            <Vault className="w-4 h-4 text-neutral-400" />
            <h2 className="text-sm font-semibold text-neutral-700">API key vault</h2>
          </div>
          <p className="text-xs text-neutral-400 mb-5">
            Store keys for multiple providers. Saved keys persist when you switch providers.
          </p>

          <div className="space-y-4">
            {KEY_PROVIDERS.map((kp) => {
              const saved = org ? !!kp.hasKey(org) : false;
              const isActive = llmProvider === kp.value;
              const val = keys[kp.field];
              const visible = showKey[kp.field];
              return (
                <div key={kp.value} className={`rounded-lg border p-4 transition-colors ${
                  isActive ? "border-brand-200 bg-brand-50/40" : "border-neutral-100 bg-neutral-50/50"
                }`}>
                  <div className="flex items-center gap-2 mb-3">
                    <Key className="w-3.5 h-3.5 text-neutral-400" />
                    <span className="text-sm font-medium text-neutral-700 flex-1">{kp.label}</span>
                    {isActive && (
                      <span className="text-[11px] font-medium text-brand-600 bg-brand-100 px-1.5 py-0.5 rounded">
                        Active
                      </span>
                    )}
                    <KeyBadge saved={saved} />
                  </div>
                  <div className="relative">
                    <input
                      type={visible ? "text" : "password"}
                      value={val}
                      onChange={(e) => setKey(kp.field, e.target.value)}
                      placeholder={saved ? "Enter new key to replace…" : kp.placeholder}
                      className="h-9 w-full rounded-lg border border-neutral-200 bg-white px-3 pr-10 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShow(kp.field)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                    >
                      {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-xs text-neutral-400 flex items-center gap-1 mt-4">
            <Key className="w-3 h-3" /> All keys encrypted with AES-128 before storage. Leave blank to keep existing.
          </p>
        </div>

        {/* ── Pipeline Configuration ──────────────────────────────────────── */}
        <div className="bg-white border border-neutral-200 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-1">
            <GitMerge className="w-4 h-4 text-neutral-400" />
            <h2 className="text-sm font-semibold text-neutral-700">Pipeline configuration</h2>
          </div>
          <p className="text-xs text-neutral-400 mb-5">
            Choose how LLM calls are orchestrated when answering questions.
          </p>

          <div className="grid grid-cols-1 gap-3">
            {PIPELINE_MODES.map((mode) => {
              const active = pipelineMode === mode.value;
              return (
                <button
                  key={mode.value}
                  type="button"
                  onClick={() => setPipelineMode(mode.value)}
                  className={`text-left p-4 rounded-lg border transition-all ${
                    active
                      ? "border-brand-500 bg-brand-50 ring-1 ring-brand-300"
                      : "border-neutral-200 hover:border-neutral-300 bg-white"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <p className={`text-sm font-semibold ${active ? "text-brand-700" : "text-neutral-800"}`}>
                      {mode.label}
                    </p>
                    <span className={`text-[11px] px-1.5 py-0.5 rounded font-medium ${
                      active ? "bg-brand-100 text-brand-600" : "bg-neutral-100 text-neutral-500"
                    }`}>
                      {mode.badge}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-500 mb-2">{mode.desc}</p>
                  <div className="space-y-1">
                    {mode.detail.map((step, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[11px] text-neutral-400 font-mono">
                        <span className="w-3.5 h-3.5 rounded-full bg-neutral-100 flex items-center justify-center text-[9px] font-sans font-semibold text-neutral-500 flex-shrink-0">
                          {i + 1}
                        </span>
                        {step}
                      </div>
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Feedback ─────────────────────────────────────────────────────── */}
        {success && (
          <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> Settings saved successfully.
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            <XCircle className="w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-2 h-9 px-4 rounded-md bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors disabled:opacity-50 shadow-xs"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save settings
        </button>
      </form>
    </div>
    </div>
  );
}
