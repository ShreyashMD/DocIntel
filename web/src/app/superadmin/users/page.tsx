"use client";
import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { superApi } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { RoleBadge, StatusBadge } from "@/components/ui/Badge";
import type { User } from "@/types";

export default function AllUsersPage() {
  const [users, setUsers]     = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState("");

  useEffect(() => {
    superApi.users().then(setUsers).catch(() => setUsers([])).finally(() => setLoading(false));
  }, []);

  const filtered = filter
    ? users.filter((u) =>
        u.email.includes(filter) ||
        u.full_name.toLowerCase().includes(filter.toLowerCase())
      )
    : users;

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All users</h1>
          <p className="text-gray-500 mt-1">{users.length} users across all organisations</p>
        </div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by name or email…"
          className="w-64 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filtered.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p>No users found</p>
              </div>
            ) : filtered.map((u) => (
              <div key={u.id} className="flex items-center gap-4 px-6 py-4">
                <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-semibold text-brand-700">
                    {u.full_name?.[0]?.toUpperCase() ?? u.email[0].toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{u.full_name || "—"}</p>
                  <p className="text-xs text-gray-500">{u.email}</p>
                </div>
                <div className="text-xs text-gray-400">
                  {u.org_id ? `org: ${u.org_id.slice(0, 8)}…` : "platform"}
                </div>
                <RoleBadge role={u.role} />
                <StatusBadge status={u.active ? "active" : "suspended"} />
                <p className="text-xs text-gray-400 w-24 text-right">
                  {new Date(u.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
