"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  FileText, MessageSquare, Search, History,
  Users, Settings, LayoutDashboard, Building2,
  LogOut, Network, ChevronRight,
} from "lucide-react";
import { useAuth } from "@/lib/auth";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
}

const userNav: NavItem[] = [
  { href: "/app",           label: "Home",      icon: LayoutDashboard, exact: true },
  { href: "/app/documents", label: "Documents", icon: FileText },
  { href: "/app/ask",       label: "Ask AI",    icon: MessageSquare },
  { href: "/app/search",    label: "Search",    icon: Search },
  { href: "/app/graph",     label: "Graph",     icon: Network },
  { href: "/app/history",   label: "History",   icon: History },
];

const adminNav: NavItem[] = [
  { href: "/admin",          label: "Overview",  icon: LayoutDashboard, exact: true },
  { href: "/admin/users",    label: "Team",      icon: Users },
  { href: "/admin/settings", label: "Settings",  icon: Settings },
];

const superNav: NavItem[] = [
  { href: "/superadmin",       label: "Overview",      icon: LayoutDashboard, exact: true },
  { href: "/superadmin/orgs",  label: "Organizations", icon: Building2 },
  { href: "/superadmin/users", label: "All Users",     icon: Users },
];

function NavLink({ item }: { item: NavItem }) {
  const pathname = usePathname();
  const active = item.exact
    ? pathname === item.href
    : pathname === item.href || pathname.startsWith(item.href + "/");
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={clsx(
        "relative flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-all duration-100",
        active
          ? "bg-brand-50 text-brand-700"
          : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-brand-600" />
      )}
      <Icon className={clsx(
        "w-4 h-4 flex-shrink-0 transition-colors",
        active ? "text-brand-600" : "text-neutral-400"
      )} />
      <span className="leading-none">{item.label}</span>
    </Link>
  );
}

function NavSection({ label, items }: { label?: string; items: NavItem[] }) {
  return (
    <div className="space-y-0.5">
      {label && (
        <p className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-[0.09em] text-neutral-400 select-none">
          {label}
        </p>
      )}
      {items.map((item) => <NavLink key={item.href} item={item} />)}
    </div>
  );
}

export function Sidebar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  const isAdmin = user.role === "org_admin";
  const isSuper = user.role === "superadmin";

  const initials = user.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : user.email[0].toUpperCase();

  return (
    <aside className="w-[220px] min-h-screen flex flex-col flex-shrink-0 bg-white border-r border-neutral-200">

      {/* ── Logo ───────────────────────────────────────────────────── */}
      <div className="h-14 flex items-center px-4 flex-shrink-0 border-b border-neutral-200">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 bg-brand-600">
            <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="none">
              <path d="M3 4h10M3 8h10M3 12h6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
            </svg>
          </div>
          <span className="font-semibold text-[13.5px] text-neutral-900 tracking-tight">DocIntel</span>
        </Link>
      </div>

      {/* ── Navigation ─────────────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {isSuper ? (
          <NavSection label="Platform" items={superNav} />
        ) : isAdmin ? (
          <>
            <NavSection label="Admin" items={adminNav} />
            <div className="pt-4 border-t border-neutral-100">
              <NavSection label="Workspace" items={userNav} />
            </div>
          </>
        ) : (
          <NavSection items={userNav} />
        )}

        {(isAdmin || isSuper) && (
          <div className="pt-2 border-t border-neutral-100">
            <Link
              href={isSuper ? "/admin" : "/app"}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs text-neutral-400 hover:text-neutral-600 hover:bg-neutral-50 transition-colors"
            >
              <ChevronRight className="w-3 h-3" />
              {isSuper ? "Org admin view" : "User workspace"}
            </Link>
          </div>
        )}
      </nav>

      {/* ── User footer ────────────────────────────────────────────── */}
      <div className="px-3 py-3 flex-shrink-0 border-t border-neutral-200">
        <div className="flex items-center gap-2.5 px-2 py-2 rounded-md hover:bg-neutral-50 transition-colors group cursor-default">
          <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 bg-brand-600 ring-2 ring-white">
            <span className="text-[10px] font-bold text-white">{initials}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-semibold text-neutral-800 truncate leading-tight">
              {user.full_name || user.email}
            </p>
            <p className="text-[10px] text-neutral-400 capitalize truncate leading-tight mt-0.5">
              {user.role.replace(/_/g, " ")}
            </p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-1 rounded text-neutral-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
