"use client";
import { useRequireAuth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { ToastProvider } from "@/contexts/toast-context";
import { Toaster } from "@/components/ui/Toaster";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { loading } = useRequireAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="flex flex-col items-center gap-3">
        <div className="w-7 h-7 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-neutral-400 font-medium">Loading workspace…</p>
      </div>
    </div>
  );
  return (
    <ToastProvider>
      <div className="flex min-h-screen bg-neutral-50">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
      <Toaster />
    </ToastProvider>
  );
}
