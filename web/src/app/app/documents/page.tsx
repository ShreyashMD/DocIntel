"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Image, Trash2, RefreshCw, Upload, CloudUpload, X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { docApi } from "@/lib/api";
import { StatusBadge } from "@/components/ui/Badge";
import { useToast } from "@/contexts/toast-context";
import type { Document } from "@/types";

const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif"]);

function isImage(filename: string) {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  return IMAGE_EXTS.has(ext);
}

const ACCEPTED = [
  ".pdf", ".txt", ".md", ".rst", ".log", ".csv",
  ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".html", ".htm",
  ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif",
];

function fmtSize(bytes?: number) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface UploadItem {
  id: string;
  file: File;
  status: "queued" | "uploading" | "done" | "error";
  error?: string;
}

export default function DocumentsPage() {
  const [docs, setDocs]         = useState<Document[]>([]);
  const [loading, setLoading]   = useState(true);
  const [uploads, setUploads]   = useState<UploadItem[]>([]);
  const [collection, setCollection] = useState("default");
  const [dragging, setDragging] = useState(false);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);
  const prevDocsRef = useRef<Document[]>([]);
  const { toast } = useToast();

  async function load() {
    setLoading(true);
    const data = await docApi.list().catch(() => []);

    // Detect status transitions and notify
    const prev = prevDocsRef.current;
    if (prev.length > 0) {
      data.forEach((doc) => {
        const old = prev.find((d) => d.id === doc.id);
        if (!old) return;
        if (old.status === "ingesting" && doc.status === "ready") {
          toast(`"${doc.filename}" is ready`, "success");
        }
        if (old.status === "ingesting" && doc.status === "failed") {
          toast(`"${doc.filename}" failed to process`, "error");
        }
      });
    }

    prevDocsRef.current = data;
    setDocs(data);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  // Auto-refresh while any document is ingesting
  useEffect(() => {
    const ingesting = docs.some((d) => d.status === "ingesting" || d.status === "pending");
    if (!ingesting) return;
    const timer = setInterval(load, 4000);
    return () => clearInterval(timer);
  }, [docs]);

  function enqueue(files: FileList | File[]) {
    const items: UploadItem[] = Array.from(files).map((f) => ({
      id: `${f.name}-${Date.now()}-${Math.random()}`,
      file: f,
      status: "queued",
    }));
    setUploads((prev) => [...prev, ...items]);
    items.forEach((item) => processUpload(item));
  }

  async function processUpload(item: UploadItem) {
    setUploads((prev) => prev.map((u) => u.id === item.id ? { ...u, status: "uploading" } : u));
    toast(`Uploading "${item.file.name}"…`, "info");
    try {
      await docApi.upload(item.file, collection);
      setUploads((prev) => prev.map((u) => u.id === item.id ? { ...u, status: "done" } : u));
      toast(`"${item.file.name}" uploaded — processing in background`, "info");
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setUploads((prev) => prev.map((u) =>
        u.id === item.id ? { ...u, status: "error", error: msg } : u
      ));
      toast(`Upload failed: ${msg}`, "error");
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) enqueue(e.dataTransfer.files);
  }, [collection]);

  async function del(doc: Document) {
    if (!confirm(`Delete "${doc.filename}"?`)) return;
    setDeleting((prev) => new Set(prev).add(doc.id));
    try {
      await docApi.delete(doc.id, doc.collection_id);
      toast(`"${doc.filename}" deleted`, "success");
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      toast(`Delete failed: ${msg}`, "error");
    } finally {
      setDeleting((prev) => { const s = new Set(prev); s.delete(doc.id); return s; });
    }
  }

  const pendingUploads = uploads.filter((u) => u.status !== "done");
  const ingestingCount = docs.filter((d) => d.status === "ingesting" || d.status === "pending").length;

  return (
    <div className="flex flex-col min-h-full">

      {/* Page header */}
      <div className="page-header">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-6">
          <div>
            <h1 className="page-header-title">Documents</h1>
            <p className="page-header-desc">Upload and manage your knowledge base</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-500 font-medium">Collection</span>
              <input
                value={collection}
                onChange={(e) => setCollection(e.target.value)}
                className="h-8 text-xs border border-neutral-300 rounded-md px-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 w-28 text-neutral-700 shadow-xs"
              />
            </div>
            <button
              onClick={load}
              className="h-8 w-8 rounded-md border border-neutral-300 bg-white flex items-center justify-center text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50 transition-colors shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div className="px-8 py-7 max-w-4xl mx-auto w-full">

      {/* Processing status banner */}
      {ingestingCount > 0 && (
        <div className="flex items-center gap-3 mb-5 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
          <Loader2 className="w-4 h-4 text-brand-600 animate-spin flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-800">
              {ingestingCount} document{ingestingCount > 1 ? "s" : ""} processing
            </p>
            <p className="text-xs text-blue-600 mt-0.5">
              Extracting, embedding and indexing — this may take a few minutes
            </p>
          </div>
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        className={`
          relative rounded-xl border-2 border-dashed p-10 mb-6 text-center cursor-pointer transition-all duration-150
          ${dragging
            ? "border-brand-400 bg-brand-50"
            : "border-neutral-200 bg-white hover:border-brand-300 hover:bg-neutral-50"
          }
        `}
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          accept={ACCEPTED.join(",")}
          className="hidden"
          onChange={(e) => { if (e.target.files) { enqueue(e.target.files); e.target.value = ""; } }}
        />
        <div className={`w-12 h-12 rounded-xl mx-auto mb-4 flex items-center justify-center transition-colors ${
          dragging ? "bg-brand-600" : "bg-neutral-100"
        }`}>
          <CloudUpload className={`w-6 h-6 ${dragging ? "text-white" : "text-neutral-400"}`} />
        </div>
        <p className="text-sm font-semibold text-neutral-700 mb-1">
          {dragging ? "Drop files here" : "Drag & drop files, or click to browse"}
        </p>
        <p className="text-xs text-neutral-400">
          Documents: PDF, Word, Excel, PowerPoint, CSV, Markdown, HTML, TXT
        </p>
        <p className="text-xs text-neutral-300 mt-1">
          Images (OCR): PNG, JPG, TIFF, BMP, WebP
        </p>
      </div>

      {/* Upload queue */}
      {pendingUploads.length > 0 && (
        <div className="mb-6 space-y-2">
          <p className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">Uploading</p>
          {pendingUploads.map((u) => (
            <div key={u.id} className="flex items-center gap-3 bg-white border border-neutral-200 rounded-lg px-4 py-3">
              {isImage(u.file.name)
                ? <Image className="w-4 h-4 text-purple-400 flex-shrink-0" />
                : <FileText className="w-4 h-4 text-neutral-400 flex-shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <p className="text-sm text-neutral-700 truncate">{u.file.name}</p>
                {u.error && <p className="text-xs text-red-500 mt-0.5">{u.error}</p>}
              </div>
              {u.status === "uploading" && (
                <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              )}
              {u.status === "done" && <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
              {u.status === "error" && <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />}
              <button onClick={() => setUploads((p) => p.filter((x) => x.id !== u.id))}
                className="text-neutral-300 hover:text-neutral-500 flex-shrink-0">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Documents list */}
      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-5 py-3 border-b border-neutral-100 bg-neutral-50">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Name</span>
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Collection</span>
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Chunks</span>
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</span>
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider"></span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-16">
            <Upload className="w-8 h-8 text-neutral-200 mx-auto mb-3" />
            <p className="text-sm font-medium text-neutral-400">No documents yet</p>
            <p className="text-xs text-neutral-300 mt-1">Upload files using the drop zone above</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-100">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className={`grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 items-center px-5 py-3.5 transition-colors ${
                  deleting.has(doc.id) ? "opacity-50 bg-red-50" : "hover:bg-neutral-50"
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${
                    isImage(doc.filename) ? "bg-purple-50" : "bg-neutral-100"
                  }`}>
                    {isImage(doc.filename)
                      ? <Image className="w-3.5 h-3.5 text-purple-400" />
                      : <FileText className="w-3.5 h-3.5 text-neutral-400" />
                    }
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-neutral-800 truncate">{doc.filename}</p>
                      {isImage(doc.filename) && (
                        <span className="text-[10px] font-semibold text-purple-600 bg-purple-50 border border-purple-200 px-1.5 py-0.5 rounded flex-shrink-0">
                          OCR
                        </span>
                      )}
                    </div>
                    {doc.file_size ? (
                      <p className="text-xs text-neutral-400">{fmtSize(doc.file_size)}</p>
                    ) : null}
                  </div>
                </div>
                <span className="text-xs text-neutral-400 bg-neutral-100 px-2 py-0.5 rounded-md flex-shrink-0">
                  {doc.collection_id}
                </span>
                <span className="text-sm text-neutral-600 flex-shrink-0 text-right">
                  {doc.chunk_count ?? "—"}
                </span>
                <div className="flex-shrink-0">
                  <StatusBadge status={doc.status} />
                </div>
                <button
                  onClick={() => del(doc)}
                  disabled={deleting.has(doc.id)}
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-neutral-300 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0 disabled:cursor-not-allowed"
                >
                  {deleting.has(doc.id)
                    ? <div className="w-3.5 h-3.5 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                    : <Trash2 className="w-3.5 h-3.5" />
                  }
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
