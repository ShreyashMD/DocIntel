"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { History, FileText, ChevronDown, ChevronUp, MessageSquarePlus } from "lucide-react";
import { queryApi } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Markdown } from "@/components/ui/Markdown";
import type { HistoryEntry } from "@/types";

function HistoryCard({ entry }: { entry: HistoryEntry }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  function continueChat(e: React.MouseEvent) {
    e.stopPropagation();
    localStorage.setItem("docintel_continue", JSON.stringify(entry));
    router.push("/app/ask");
  }

  return (
    <Card className="overflow-hidden">
      <button
        className="w-full px-6 py-4 flex items-start gap-4 text-left hover:bg-neutral-50 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-neutral-900 truncate">{entry.question}</p>
          <p className="text-sm text-neutral-500 mt-1 line-clamp-2">{entry.answer}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs text-neutral-400">{new Date(entry.created_at).toLocaleString()}</span>
            {entry.duration_ms && <span className="text-xs text-neutral-400">{entry.duration_ms}ms</span>}
            {entry.model && <span className="text-xs text-brand-600 bg-brand-50 px-2 py-0.5 rounded">{entry.model}</span>}
            {entry.sources?.length > 0 && (
              <span className="text-xs text-neutral-400">{entry.sources.length} sources</span>
            )}
          </div>
        </div>
        <button
          onClick={continueChat}
          title="Continue this conversation"
          className="p-1 rounded-lg text-neutral-300 hover:text-brand-600 hover:bg-brand-50 transition-colors flex-shrink-0"
        >
          <MessageSquarePlus className="w-4 h-4" />
        </button>
        {open ? <ChevronUp className="w-4 h-4 text-neutral-400 flex-shrink-0 mt-0.5" />
              : <ChevronDown className="w-4 h-4 text-neutral-400 flex-shrink-0 mt-0.5" />}
      </button>
      {open && (
        <div className="border-t border-neutral-100 px-6 py-4 bg-neutral-50">
          <div className="text-sm text-neutral-700 mb-4">
            <Markdown>{entry.answer}</Markdown>
          </div>
          {entry.sources?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">Sources</p>
              <div className="space-y-1">
                {entry.sources.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-neutral-600 bg-white border border-neutral-200 rounded px-3 py-2">
                    <FileText className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
                    <span className="truncate">{String(s.document_path).split(/[\\/]/).pop()}</span>
                    {s.page && <span className="text-neutral-400 flex-shrink-0">p. {s.page}</span>}
                    <span className="text-brand-600 flex-shrink-0">{((s.score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    queryApi.history(100).then(setEntries).catch(() => setEntries([])).finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col min-h-full">
      <div className="page-header">
        <h1 className="page-header-title">Query History</h1>
        <p className="page-header-desc">All your past questions and answers</p>
      </div>

      <div className="px-8 py-7 max-w-3xl w-full">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-16 text-neutral-400">
            <History className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-semibold">No history yet</p>
            <p className="text-sm mt-1">Your queries will appear here after you ask a question.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {entries.map((e) => <HistoryCard key={e.id} entry={e} />)}
          </div>
        )}
      </div>
    </div>
  );
}
