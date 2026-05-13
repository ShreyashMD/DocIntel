"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import {
  Network, Search, ZoomIn, ZoomOut, Maximize2, RefreshCw,
  Loader2, AlertTriangle, FileText, CheckSquare, Square,
  RotateCcw, ChevronDown, ChevronUp,
} from "lucide-react";
import { graphApi, GraphNode, GraphEdge, docApi } from "@/lib/api";
import type { Document } from "@/types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const TYPE_COLORS: Record<string, string> = {
  person:       "#818cf8",
  organization: "#34d399",
  concept:      "#fb923c",
  event:        "#f472b6",
  geo:          "#22d3ee",
  category:     "#a78bfa",
  product:      "#facc15",
  unknown:      "#94a3b8",
};

function typeColor(type: string): string {
  return TYPE_COLORS[type.toLowerCase()] ?? TYPE_COLORS.unknown;
}

function uniqueTypes(nodes: GraphNode[]): string[] {
  const seen = new Set<string>();
  nodes.forEach((n) => seen.add(n.type.toLowerCase()));
  return Array.from(seen).sort();
}

interface TooltipState { x: number; y: number; node: GraphNode; }

// ── Doc selector panel ────────────────────────────────────────────────────────
function DocPanel({
  docs,
  selected,
  onChange,
  onRebuild,
  rebuilding,
}: {
  docs: Document[];
  selected: Set<string>;
  onChange: (s: Set<string>) => void;
  onRebuild: () => void;
  rebuilding: boolean;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const readyDocs = docs.filter((d) => d.status === "ready");

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    onChange(next);
  }

  function selectAll()  { onChange(new Set(readyDocs.map((d) => d.id))); }
  function clearAll()   { onChange(new Set()); }

  return (
    <div className="border-t border-white/10 bg-[#111]">
      {/* Section header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="w-3.5 h-3.5 text-neutral-500" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-neutral-600">
            Documents
            {selected.size > 0 && (
              <span className="ml-1.5 text-brand-400">{selected.size}</span>
            )}
          </span>
        </div>
        {collapsed
          ? <ChevronDown className="w-3 h-3 text-neutral-600" />
          : <ChevronUp   className="w-3 h-3 text-neutral-600" />
        }
      </button>

      {!collapsed && (
        <div className="px-2 pb-2">
          {/* Select all / clear */}
          <div className="flex gap-2 px-1 mb-1">
            <button onClick={selectAll} className="text-[10px] text-neutral-600 hover:text-neutral-400">All</button>
            <button onClick={clearAll}  className="text-[10px] text-neutral-600 hover:text-neutral-400">None</button>
          </div>

          {readyDocs.length === 0 ? (
            <p className="text-[11px] text-neutral-600 px-1 py-1">No documents</p>
          ) : (
            <div className="space-y-0.5 max-h-36 overflow-y-auto">
              {readyDocs.map((doc) => {
                const checked = selected.has(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => toggle(doc.id)}
                    title={doc.filename}
                    className="w-full flex items-center gap-2 px-1 py-1 rounded hover:bg-white/5 transition-colors text-left"
                  >
                    {checked
                      ? <CheckSquare className="w-3 h-3 text-brand-400 flex-shrink-0" />
                      : <Square      className="w-3 h-3 text-neutral-700 flex-shrink-0" />
                    }
                    <span className={`text-[11px] truncate ${checked ? "text-neutral-300" : "text-neutral-600"}`}>
                      {doc.filename}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Rebuild button */}
          <button
            onClick={onRebuild}
            disabled={rebuilding}
            title={selected.size > 0 ? "Rebuild graph with selected docs" : "Rebuild graph with all docs"}
            className="mt-2 w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg bg-brand-600/20 hover:bg-brand-600/30 text-brand-400 text-[11px] font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {rebuilding
              ? <Loader2 className="w-3 h-3 animate-spin" />
              : <RotateCcw className="w-3 h-3" />
            }
            {rebuilding ? "Rebuilding…" : selected.size > 0 ? `Rebuild (${selected.size})` : "Rebuild graph"}
          </button>
          <p className="text-[9px] text-neutral-700 text-center mt-1 leading-tight px-1">
            Clears & re-indexes the knowledge graph
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function GraphPage() {
  const [data, setData]         = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [status, setStatus]     = useState<"loading" | "disabled" | "empty" | "ready">("loading");
  const [message, setMessage]   = useState("");
  const [search, setSearch]     = useState("");
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
  const [tooltip, setTooltip]   = useState<TooltipState | null>(null);
  const [docs, setDocs]         = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [rebuilding, setRebuilding]     = useState(false);
  const [rebuildMsg, setRebuildMsg]     = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef     = useRef<any>(null);
  const mousePosRef  = useRef({ x: 0, y: 0 });
  const [dims, setDims] = useState({ w: 800, h: 600 });

  async function load() {
    setStatus("loading");
    try {
      const res = await graphApi.get();
      if (!res.enabled) { setStatus("disabled"); return; }
      if (res.nodes.length === 0) {
        setStatus("empty");
        setMessage(res.message ?? "No graph data yet.");
        return;
      }
      setData({ nodes: res.nodes, edges: res.edges });
      setStatus("ready");
    } catch {
      setStatus("empty");
      setMessage("Failed to load graph data.");
    }
  }

  useEffect(() => {
    load();
    docApi.list().then(setDocs).catch(() => {});
    // Restore polling if a rebuild was already running when the page loaded
    graphApi.rebuildStatus().then((s) => {
      if (s.running) {
        setRebuilding(true);
        setRebuildMsg("Graph rebuild is in progress…");
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDims({ w: width, h: height });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const filtered = useCallback(() => {
    if (!data) return { nodes: [], links: [] };
    const q = search.toLowerCase();
    const visibleNodes = data.nodes.filter(
      (n) =>
        !hiddenTypes.has(n.type.toLowerCase()) &&
        (q === "" || n.label.toLowerCase().includes(q) || n.description.toLowerCase().includes(q))
    );
    const visibleIds = new Set(visibleNodes.map((n) => n.id));
    const links = data.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => ({ ...e }));
    return { nodes: visibleNodes, links };
  }, [data, search, hiddenTypes]);

  function toggleType(t: string) {
    setHiddenTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t); else next.add(t);
      return next;
    });
  }

  // Poll rebuild/status while a rebuild is in progress
  useEffect(() => {
    if (!rebuilding) return;
    const timer = setInterval(async () => {
      try {
        const s = await graphApi.rebuildStatus();
        if (!s.running) {
          setRebuilding(false);
          setRebuildMsg("Graph rebuild complete — refreshing…");
          await load();
          setTimeout(() => setRebuildMsg(""), 4000);
        }
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(timer);
  }, [rebuilding]);

  async function handleRebuild() {
    if (rebuilding) return;
    setRebuilding(true);
    setRebuildMsg("");
    try {
      const docIds = selectedDocs.size > 0 ? Array.from(selectedDocs) : undefined;
      const res = await graphApi.rebuild(docIds);
      setRebuildMsg(res.message + " This may take several minutes.");
    } catch (err) {
      setRebuilding(false);
      setRebuildMsg(err instanceof Error ? err.message : "Rebuild failed.");
    }
  }

  function zoomIn()  { graphRef.current?.zoom(graphRef.current.zoom() * 1.4, 400); }
  function zoomOut() { graphRef.current?.zoom(graphRef.current.zoom() / 1.4, 400); }
  function fitAll()  { graphRef.current?.zoomToFit(400, 40); }

  const gd    = filtered();
  const types = data ? uniqueTypes(data.nodes) : [];

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, scale: number) => {
    const r     = Math.max(3, Math.min(8, (node.val ?? 1) * 3));
    const color = typeColor(node.type ?? "unknown");
    const isHighlighted = search && node.label.toLowerCase().includes(search.toLowerCase());
    if (isHighlighted) { ctx.shadowBlur = 16; ctx.shadowColor = color; }
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.shadowBlur = 0;
    if (scale > 2.5) {
      ctx.font         = `${Math.min(4, 12 / scale)}px Inter,sans-serif`;
      ctx.fillStyle    = "#e2e8f0";
      ctx.textAlign    = "center";
      ctx.textBaseline = "top";
      ctx.fillText(node.label, node.x, node.y + r + 1.5);
    }
  }, [search]);

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-full py-40">
        <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
      </div>
    );
  }

  if (status === "disabled") {
    return (
      <div className="flex flex-col items-center justify-center h-full py-40 gap-4">
        <div className="w-14 h-14 rounded-2xl bg-neutral-100 flex items-center justify-center">
          <Network className="w-7 h-7 text-neutral-400" />
        </div>
        <div className="text-center">
          <p className="font-semibold text-neutral-700">LightRAG is not enabled</p>
          <p className="text-sm text-neutral-400 mt-1 max-w-sm">
            Set <code className="text-xs bg-neutral-100 px-1 py-0.5 rounded">--rag-mode hybrid</code> in
            docker-compose.yml and rebuild the API container to enable the knowledge graph.
          </p>
        </div>
      </div>
    );
  }

  if (status === "empty") {
    return (
      <div className="flex flex-col items-center justify-center h-full py-40 gap-4">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 flex items-center justify-center">
          <AlertTriangle className="w-7 h-7 text-amber-400" />
        </div>
        <div className="text-center">
          <p className="font-semibold text-neutral-700">No graph data yet</p>
          <p className="text-sm text-neutral-400 mt-1 max-w-sm">{message}</p>
        </div>
        {docs.filter((d) => d.status === "ready").length > 0 && (
          <button
            onClick={handleRebuild}
            disabled={rebuilding}
            className="mt-2 flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm disabled:opacity-50"
          >
            {rebuilding ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
            Build knowledge graph
          </button>
        )}
        {rebuildMsg && <p className="text-xs text-neutral-500 max-w-xs text-center">{rebuildMsg}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#0a0a0a]">

      {/* Top bar */}
      <div className="flex items-center gap-4 px-5 py-3 border-b border-white/10 bg-[#111] flex-shrink-0">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold text-white">Knowledge Graph</span>
        </div>

        <div className="flex items-center gap-1.5 h-7 bg-white/5 border border-white/10 rounded-lg px-2.5 flex-1 max-w-64">
          <Search className="w-3.5 h-3.5 text-neutral-500 flex-shrink-0" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search entities…"
            className="bg-transparent text-xs text-neutral-200 placeholder:text-neutral-600 focus:outline-none w-full"
          />
        </div>

        <div className="ml-auto flex items-center gap-1">
          <span className="text-xs text-neutral-500 mr-2">
            {gd.nodes.length} nodes · {gd.links.length} edges
          </span>
          <button onClick={zoomIn}  className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"><ZoomIn   className="w-3.5 h-3.5" /></button>
          <button onClick={zoomOut} className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"><ZoomOut  className="w-3.5 h-3.5" /></button>
          <button onClick={fitAll}  className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"><Maximize2 className="w-3.5 h-3.5" /></button>
          <button onClick={load}    className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"><RefreshCw className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {rebuildMsg && (
        <div className="px-5 py-2 bg-brand-600/20 border-b border-brand-600/30 text-[11px] text-brand-300">
          {rebuildMsg}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">

        {/* Left panel */}
        <div className="w-44 flex-shrink-0 border-r border-white/10 bg-[#111] flex flex-col overflow-hidden">
          {/* Entity types */}
          <div className="px-3 py-4 overflow-y-auto flex-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-600 mb-3">Entity types</p>
            <div className="space-y-1">
              {types.map((t) => {
                const count  = data!.nodes.filter((n) => n.type.toLowerCase() === t).length;
                const hidden = hiddenTypes.has(t);
                return (
                  <button
                    key={t}
                    onClick={() => toggleType(t)}
                    className="flex items-center gap-2 w-full px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors"
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0 transition-opacity"
                      style={{ background: typeColor(t), opacity: hidden ? 0.25 : 1 }}
                    />
                    <span className={`text-xs capitalize flex-1 text-left ${hidden ? "text-neutral-600" : "text-neutral-300"}`}>
                      {t}
                    </span>
                    <span className="text-[10px] text-neutral-600">{count}</span>
                  </button>
                );
              })}
            </div>

            <div className="mt-6 pt-4 border-t border-white/10">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-600 mb-2">Tips</p>
              <div className="space-y-1.5 text-[11px] text-neutral-600 leading-relaxed">
                <p>Scroll to zoom</p>
                <p>Drag to pan</p>
                <p>Click node for details</p>
              </div>
            </div>
          </div>

          {/* Document selector + rebuild */}
          <DocPanel
            docs={docs}
            selected={selectedDocs}
            onChange={setSelectedDocs}
            onRebuild={handleRebuild}
            rebuilding={rebuilding}
          />
        </div>

        {/* Graph canvas */}
        <div
          className="flex-1 relative overflow-hidden"
          ref={containerRef}
          onMouseMove={(e) => {
            const rect = containerRef.current?.getBoundingClientRect();
            if (rect) mousePosRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          }}
        >
          {tooltip && (
            <div
              className="absolute z-10 pointer-events-none bg-[#1a1a1a] border border-white/15 rounded-xl px-3 py-2.5 max-w-xs shadow-2xl"
              style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: typeColor(tooltip.node.type) }} />
                <span className="text-xs font-semibold text-white truncate">{tooltip.node.label}</span>
              </div>
              <span className="text-[10px] text-neutral-400 capitalize">{tooltip.node.type}</span>
              {tooltip.node.description && (
                <p className="text-[11px] text-neutral-300 mt-1.5 leading-relaxed line-clamp-4">
                  {tooltip.node.description}
                </p>
              )}
            </div>
          )}

          <ForceGraph2D
            ref={graphRef}
            graphData={gd}
            width={dims.w}
            height={dims.h}
            backgroundColor="#0a0a0a"
            nodeCanvasObject={paintNode}
            nodeCanvasObjectMode={() => "replace"}
            nodeColor={(n: any) => typeColor(n.type ?? "unknown")}
            nodeRelSize={4}
            nodeVal={(_: any) => 1}
            linkColor={() => "rgba(255,255,255,0.12)"}
            linkWidth={(l: any) => Math.min(3, (l.weight ?? 1) * 0.8)}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.1}
            linkLabel={(l: any) => l.label || l.description || ""}
            onNodeHover={(node: any) => {
              if (!node) { setTooltip(null); return; }
              const { x, y } = mousePosRef.current;
              setTooltip({ x, y, node: node as GraphNode });
            }}
            onNodeClick={(node: any) => {
              graphRef.current?.centerAt(node.x, node.y, 600);
              graphRef.current?.zoom(6, 600);
            }}
            cooldownTicks={120}
            onEngineStop={fitAll}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
          />
        </div>
      </div>
    </div>
  );
}
