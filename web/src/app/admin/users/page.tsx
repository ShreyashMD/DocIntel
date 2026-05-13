"use client";
import { useEffect, useState } from "react";
import { UserPlus, Mail, MoreVertical } from "lucide-react";
import { adminApi, authApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { RoleBadge } from "@/components/ui/Badge";
import type { Invitation, User } from "@/types";

const ROLES = ["user", "viewer", "manager", "org_admin"];

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers]     = useState<User[]>([]);
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);

  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole]   = useState("user");
  const [inviting, setInviting]       = useState(false);
  const [inviteResult, setInviteResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    const data = await adminApi.users().catch(() => ({ users: [], pending_invites: [] }));
    setUsers(data.users);
    setInvites(data.pending_invites);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setInviting(true);
    try {
      const res = await authApi.invite(inviteEmail, inviteRole);
      const inviteUrl = `${window.location.origin}/invite/${res.invite_token}`;
      setInviteResult(inviteUrl);
      setInviteEmail("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send invite.");
    } finally {
      setInviting(false);
    }
  }

  async function toggleActive(user: User) {
    await adminApi.updateUser(user.id, { active: !user.active }).catch(() => {});
    await load();
  }

  async function changeRole(user: User, role: string) {
    await adminApi.updateUser(user.id, { role }).catch(() => {});
    await load();
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Team members</h1>
          <p className="text-gray-500 mt-1">Manage users and invitations</p>
        </div>
        <Button onClick={() => { setShowInvite(!showInvite); setInviteResult(null); }}>
          <UserPlus className="w-4 h-4" /> Invite member
        </Button>
      </div>

      {/* Invite panel */}
      {showInvite && (
        <Card className="p-6 mb-8">
          <h2 className="font-semibold text-gray-900 mb-4">Send invitation</h2>
          {inviteResult ? (
            <div className="space-y-3">
              <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                Invitation created! Share this link with your teammate:
              </p>
              <code className="block text-xs bg-gray-100 rounded-lg px-3 py-2 break-all">{inviteResult}</code>
              <Button variant="secondary" size="sm" onClick={() => { setInviteResult(null); setShowInvite(false); }}>
                Done
              </Button>
            </div>
          ) : (
            <form onSubmit={sendInvite} className="flex gap-3 items-end">
              <div className="flex-1"><Input label="Email address" type="email" value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)} placeholder="colleague@company.com" required /></div>
              <div>
                <label className="text-sm font-medium text-gray-700">Role</label>
                <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                  {ROLES.map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
                </select>
              </div>
              <Button type="submit" loading={inviting}><Mail className="w-4 h-4" />Send</Button>
            </form>
          )}
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </Card>
      )}

      {/* Users table */}
      <Card className="mb-6">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Active members ({users.length})</h2>
        </div>
        {loading ? (
          <div className="flex justify-center py-10">
            <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {users.map((u) => (
              <div key={u.id} className="flex items-center gap-4 px-6 py-4">
                <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-semibold text-brand-700">
                    {u.full_name?.[0]?.toUpperCase() ?? u.email[0].toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{u.full_name || u.email}</p>
                  <p className="text-xs text-gray-500">{u.email}</p>
                </div>
                <RoleBadge role={u.role} />
                {u.id !== me?.id && (
                  <div className="flex items-center gap-2">
                    <select
                      value={u.role}
                      onChange={(e) => changeRole(u, e.target.value)}
                      className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
                    </select>
                    <button
                      onClick={() => toggleActive(u)}
                      className={`text-xs px-2 py-1 rounded border ${
                        u.active
                          ? "border-red-200 text-red-600 hover:bg-red-50"
                          : "border-green-200 text-green-600 hover:bg-green-50"
                      }`}
                    >
                      {u.active ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Pending invites */}
      {invites.length > 0 && (
        <Card>
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Pending invitations ({invites.length})</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {invites.map((inv) => (
              <div key={inv.id} className="flex items-center gap-4 px-6 py-4">
                <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm text-gray-900">{inv.email}</p>
                  <p className="text-xs text-gray-500">
                    Expires {new Date(inv.expires_at).toLocaleDateString()}
                  </p>
                </div>
                <RoleBadge role={inv.role} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
