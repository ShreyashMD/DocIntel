"use client";
import { CheckCircle2, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { useToast } from "@/contexts/toast-context";

const ICONS = {
  success: <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />,
  error:   <AlertCircle  className="w-4 h-4 text-red-500 flex-shrink-0" />,
  warning: <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />,
  info:    <Info         className="w-4 h-4 text-brand-500 flex-shrink-0" />,
};

const STYLES = {
  success: "bg-emerald-50 border-emerald-200 text-emerald-800",
  error:   "bg-red-50 border-red-200 text-red-800",
  warning: "bg-amber-50 border-amber-200 text-amber-800",
  info:    "bg-white border-neutral-200 text-neutral-800",
};

export function Toaster() {
  const { toasts } = useToast();
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start gap-3 px-4 py-3 rounded-lg shadow-elevated border
            min-w-56 max-w-sm animate-in fade-in slide-in-from-bottom-2 duration-200
            ${STYLES[t.type]}`}
        >
          {ICONS[t.type]}
          <p className="text-sm leading-snug">{t.message}</p>
        </div>
      ))}
    </div>
  );
}
