"use client";
import { useState } from "react";
import { Search, FileText } from "lucide-react";
import { queryApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { SearchResult } from "@/types";

export default function SearchPage() {
  const [query, setQuery]         = useState("");
  const [collection, setCollection] = useState("default");
  const [results, setResults]     = useState<SearchResult[]>([]);
  const [loading, setLoading]     = useState(false);
  const [searched, setSearched]   = useState(false);

  async function doSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await queryApi.search(query, collection, 10);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-neutral-900">Search</h1>
        <p className="text-neutral-500 mt-1">Semantic similarity search across your documents</p>
      </div>

      <form onSubmit={doSearch} className="flex gap-3 mb-8">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your documents…"
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-neutral-300 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <input
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          placeholder="Collection"
          className="w-32 px-3 py-3 rounded-xl border border-neutral-300 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <Button type="submit" loading={loading}>Search</Button>
      </form>

      {loading && (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-center py-12 text-neutral-400">
          <Search className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>No results found for &ldquo;{query}&rdquo;</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-neutral-500">{results.length} results</p>
          {results.map((r, i) => {
            const filename = r.document_path.split(/[\\/]/).pop();
            const page     = r.chunk.metadata?.page;
            const section  = r.chunk.metadata?.breadcrumb as string | undefined;
            return (
              <Card key={i} className="p-5">
                <div className="flex items-center gap-3 mb-3">
                  <FileText className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-900 truncate">{filename}</p>
                    {section && <p className="text-xs text-neutral-500">{section}</p>}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {page != null && <span className="text-xs text-neutral-400 bg-neutral-100 px-2 py-0.5 rounded">p. {String(page)}</span>}
                    <span className="text-xs font-semibold text-brand-600 bg-brand-50 px-2 py-0.5 rounded">
                      {(r.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <p className="text-sm text-neutral-700 line-clamp-3">{r.chunk.text}</p>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
