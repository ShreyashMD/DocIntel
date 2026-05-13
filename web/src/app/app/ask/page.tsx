"use client";
import { useEffect, useRef, useState } from "react";
import {
  Send, Sparkles, User, FileText, ChevronDown, ChevronUp,
  CircleDot, Filter, CheckSquare, Square, X, ExternalLink,
} from "lucide-react";
import { queryApi, docApi, docFileUrl } from "@/lib/api";
import { Markdown } from "@/components/ui/Markdown";
import type { QueryResult, Document } from "@/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  result?: QueryResult;
  timestamp: Date;
}

// ── Source card ───────────────────────────────────────────────────────────────
function SourceCard({ source }: { source: QueryResult["sources"][0] }) {
  const [open, setOpen] = useState(false);
  const page     = source.chunk.metadata?.page as number | undefined;
  const section  = source.chunk.metadata?.breadcrumb as string | undefined;
  const filename = source.document_path.split(/[\\/]/).pop() ?? "";
  const score    = Math.round(source.score * 100);
  const isPdf    = filename.toLowerCase().endsWith(".pdf");

  function openFile(e: React.MouseEvent) {
    e.stopPropagation();
    if (!source.doc_id) return;
    window.open(docFileUrl(source.doc_id, page), "_blank", "noopener,noreferrer");
  }

  return (
    <div className="rounded-lg border border-neutral-200 overflow-hidden text-xs bg-white">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-neutral-50 text-left transition-colors"
        onClick={() => setOpen(!open)}
      >
        <FileText className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
        <span className="truncate text-neutral-600 flex-1">{filename}{page ? ` · p. ${page}` : ""}</span>
        <span className="font-medium text-brand-600 flex-shrink-0">{score}%</span>
        {source.doc_id && (
          <button
            onClick={openFile}
            title={isPdf && page ? `Open PDF at page ${page}` : "Open file"}
            className="p-0.5 rounded text-neutral-300 hover:text-brand-500 transition-colors flex-shrink-0"
          >
            <ExternalLink className="w-3 h-3" />
          </button>
        )}
        {open
          ? <ChevronUp  className="w-3 h-3 text-neutral-400 flex-shrink-0" />
          : <ChevronDown className="w-3 h-3 text-neutral-400 flex-shrink-0" />
        }
      </button>
      {open && (
        <div className="px-3 py-2.5 bg-neutral-50 border-t border-neutral-100 text-neutral-600 leading-relaxed">
          {section && (
            <p className="font-medium text-neutral-400 text-[11px] mb-1 uppercase tracking-wider">{section}</p>
          )}
          <p className="line-clamp-4">{source.chunk.text}</p>
        </div>
      )}
    </div>
  );
}

// ── Chat message ──────────────────────────────────────────────────────────────
function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5 ${
        isUser ? "bg-neutral-700" : "bg-brand-600"
      }`}>
        {isUser
          ? <User     className="w-3.5 h-3.5 text-white" />
          : <Sparkles className="w-3.5 h-3.5 text-white" />
        }
      </div>
      <div className={`max-w-[80%] flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-neutral-900 text-white rounded-tr-sm"
            : "bg-white border border-neutral-200 text-neutral-800 rounded-tl-sm shadow-card"
        }`}>
          {isUser
            ? <p className="whitespace-pre-wrap">{msg.content}</p>
            : <div className="text-sm leading-relaxed prose-sm"><Markdown>{msg.content}</Markdown></div>
          }
        </div>
        {msg.result && msg.result.sources.length > 0 && (
          <div className="w-full space-y-1">
            <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400 px-0.5">
              {msg.result.sources.length} source{msg.result.sources.length !== 1 ? "s" : ""}
            </p>
            {msg.result.sources.map((s, i) => <SourceCard key={i} source={s} />)}
          </div>
        )}
        <p className="text-[10px] text-neutral-400 px-0.5">
          {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-slide-up">
      <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center flex-shrink-0">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="bg-white border border-neutral-200 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5 shadow-card">
        {[0, 150, 300].map((delay) => (
          <div
            key={delay}
            className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Doc filter popover ────────────────────────────────────────────────────────
function DocFilter({
  docs,
  selected,
  onChange,
}: {
  docs: Document[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const readyDocs = docs.filter((d) => d.status === "ready");
  const allSelected = selected.size === 0;
  const count = selected.size;

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    onChange(next);
  }

  function clearAll() { onChange(new Set()); }
  function selectAll() { onChange(new Set(readyDocs.map((d) => d.id))); }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 h-7 px-2.5 rounded-lg border text-xs transition-colors ${
          count > 0
            ? "border-brand-400 bg-brand-50 text-brand-700"
            : "border-neutral-200 bg-white text-neutral-500 hover:border-neutral-300"
        }`}
      >
        <Filter className="w-3 h-3" />
        {count > 0 ? `${count} doc${count !== 1 ? "s" : ""}` : "All docs"}
        <ChevronDown className="w-3 h-3 opacity-60" />
      </button>

      {open && (
        <div className="absolute right-0 top-9 z-50 w-72 bg-white border border-neutral-200 rounded-xl shadow-elevated overflow-hidden">
          <div className="px-3 py-2.5 border-b border-neutral-100 flex items-center justify-between">
            <span className="text-xs font-semibold text-neutral-700">Filter documents</span>
            <div className="flex gap-2">
              <button onClick={clearAll}  className="text-[11px] text-neutral-400 hover:text-neutral-600">All</button>
              <button onClick={selectAll} className="text-[11px] text-neutral-400 hover:text-neutral-600">Select all</button>
            </div>
          </div>

          {readyDocs.length === 0 ? (
            <p className="px-3 py-4 text-xs text-neutral-400 text-center">No ready documents</p>
          ) : (
            <div className="max-h-56 overflow-y-auto divide-y divide-neutral-50">
              {readyDocs.map((doc) => {
                const checked = selected.has(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => toggle(doc.id)}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 hover:bg-neutral-50 text-left transition-colors"
                  >
                    {checked
                      ? <CheckSquare className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
                      : <Square      className="w-3.5 h-3.5 text-neutral-300 flex-shrink-0" />
                    }
                    <span className="truncate text-xs text-neutral-700 flex-1">{doc.filename}</span>
                    <span className="text-[10px] text-neutral-400 flex-shrink-0">{doc.collection_id}</span>
                  </button>
                );
              })}
            </div>
          )}

          {count > 0 && (
            <div className="px-3 py-2 border-t border-neutral-100 flex items-center justify-between">
              <span className="text-[11px] text-brand-600">{count} selected</span>
              <button onClick={clearAll} className="flex items-center gap-1 text-[11px] text-neutral-400 hover:text-neutral-600">
                <X className="w-3 h-3" /> Clear
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AskPage() {
  const [messages, setMessages]       = useState<Message[]>([]);
  const [question, setQuestion]       = useState("");
  const [collection, setCollection]   = useState("default");
  const [loading, setLoading]         = useState(false);
  const [docs, setDocs]               = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    docApi.list().then(setDocs).catch(() => {});

    // Restore a conversation continued from history
    const raw = localStorage.getItem("docintel_continue");
    if (raw) {
      localStorage.removeItem("docintel_continue");
      try {
        const entry = JSON.parse(raw) as import("@/types").HistoryEntry;
        const ts = new Date(entry.created_at);
        const reconstructed: QueryResult = {
          question: entry.question,
          answer:   entry.answer,
          model:    entry.model ?? "",
          sources:  entry.sources.map((s) => ({
            chunk:         { id: "", text: "", metadata: { page: s.page } },
            score:         s.score,
            document_path: s.document_path,
            tenant_id:     "",
          })),
        };
        setMessages([
          { role: "user",      content: entry.question, timestamp: ts },
          { role: "assistant", content: entry.answer,   result: reconstructed, timestamp: ts },
        ]);
      } catch { /* malformed — ignore */ }
    }
  }, []);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userMsg: Message = { role: "user", content: question, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setLoading(true);

    const docIds = selectedDocs.size > 0 ? Array.from(selectedDocs) : undefined;

    try {
      const result = await queryApi.ask(question, collection, undefined, docIds);
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.answer,
        result,
        timestamp: new Date(),
      }]);
    } catch (err: unknown) {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: err instanceof Error ? err.message : "Something went wrong. Please try again.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        inputRef.current?.focus();
      }, 100);
    }
  }

  return (
    <div className="flex flex-col" style={{ height: "100vh" }}>

      {/* Header */}
      <div className="border-b border-neutral-200 bg-white px-6 py-4 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-base font-semibold text-neutral-900">Ask AI</h1>
          <p className="text-xs text-neutral-400">Answers sourced from your documents</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-neutral-400">Collection</span>
          <input
            value={collection}
            onChange={(e) => setCollection(e.target.value)}
            className="h-7 text-xs border border-neutral-200 rounded-lg px-2.5 bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 w-28 text-neutral-700"
          />
          <DocFilter docs={docs} selected={selectedDocs} onChange={setSelectedDocs} />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5 bg-neutral-50">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center pb-12 animate-fade-in">
            <div className="w-14 h-14 rounded-xl bg-brand-600 flex items-center justify-center mb-4 shadow-elevated">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h2 className="text-base font-semibold text-neutral-800 mb-1">Ask anything about your documents</h2>
            <p className="text-sm text-neutral-400 max-w-xs">
              Get AI-powered answers with page-level citations.
              {selectedDocs.size > 0
                ? ` Searching ${selectedDocs.size} selected document${selectedDocs.size !== 1 ? "s" : ""}.`
                : " Searching all documents."}
            </p>
            <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-sm">
              {[
                "Summarize the key findings",
                "What are the safety requirements?",
                "List all mentioned deadlines",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => { setQuestion(suggestion); inputRef.current?.focus(); }}
                  className="text-left px-3 py-2.5 rounded-lg border border-neutral-200 bg-white hover:border-brand-300 hover:bg-brand-50 text-sm text-neutral-600 hover:text-brand-700 transition-all"
                >
                  <CircleDot className="w-3.5 h-3.5 inline mr-2 text-neutral-300" />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => <ChatMessage key={i} msg={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-neutral-200 bg-white px-6 py-4 flex-shrink-0">
        {selectedDocs.size > 0 && (
          <div className="flex items-center gap-1.5 mb-2 flex-wrap">
            <span className="text-[11px] text-neutral-400">Asking about:</span>
            {Array.from(selectedDocs).map((id) => {
              const doc = docs.find((d) => d.id === id);
              return doc ? (
                <span key={id} className="inline-flex items-center gap-1 bg-brand-50 text-brand-700 text-[11px] px-2 py-0.5 rounded-full border border-brand-200">
                  {doc.filename}
                  <button onClick={() => {
                    const next = new Set(selectedDocs); next.delete(id); setSelectedDocs(next);
                  }}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </span>
              ) : null;
            })}
          </div>
        )}
        <form onSubmit={send} className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { send(e); } }}
              placeholder="Ask a question about your documents…"
              disabled={loading}
              className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 pr-12 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 focus:bg-white transition-all disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="h-10 w-10 rounded-md bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors flex-shrink-0"
          >
            {loading
              ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              : <Send className="w-4 h-4 text-white" />
            }
          </button>
        </form>
      </div>
    </div>
  );
}
