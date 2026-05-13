"use client";
import { useEffect, useState } from "react";
import { Building2, Plus, Power, Trash2, UserPlus, Copy, Check, Mail } from "lucide-react";
import { superApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import type { Org } from "@/types";

const ROLES = ["user", "viewer", "manager", "org_admin"];

interface InviteState {
  orgId: string;
  email: string;
  role: string;
  loading: boolean;
  result: string | null;
  error: string;
  copied: boolean;
}

export default function OrgsPage() {
  const [orgs, setOrgs]       = useState<Org[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating]     = useState(false);
  const [error, setError]           = useState("");
  const [invite, setInvite]         = useState<InviteState | null>(null);

  const [form, setForm] = useState({
    name: "", slug: "", admin_email: "", admin_name: "", admin_password: "",
  });

  async function load() {
    setLoading(true);
    const data = await superApi.orgs().catch(() => []);
    setOrgs(data);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  function handleName(v: string) {
    setForm((f) => ({
      ...f,
      name: v,
      slug: v.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
    }));
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setCreating(true);
    try {
      await superApi.createOrg(form);
      setShowCreate(false);
      setForm({ name: "", slug: "", admin_email: "", admin_name: "", admin_password: "" });
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create organisation.");
    } finally {
      setCreating(false);
    }
  }

  function openInvite(org: Org) {
    setInvite({ orgId: org.id, email: "", role: "org_admin", loading: false, result: null, error: "", copied: false });
  }

  async function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!invite) return;
    setInvite({ ...invite, loading: true, error: "" });
    try {
      const res = await superApi.inviteToOrg(invite.orgId, invite.email, invite.role);
      const url = `${window.location.origin}/invite/${res.invite_token}`;
      setInvite({ ...invite, loading: false, result: url, error: "" });
    } catch (err: unknown) {
      setInvite({ ...invite, loading: false, error: err instanceof Error ? err.message : "Failed." });
    }
  }

  async function copyLink() {
    if (!invite?.result) return;
    await navigator.clipboard.writeText(invite.result);
    setInvite({ ...invite, copied: true });
    setTimeout(() => setInvite((p) => p ? { ...p, copied: false } : p), 2000);
  }

  async function toggleActive(org: Org) {
    await superApi.updateOrg(org.id, { active: !org.active }).catch(() => {});
    await load();
  }

  async function del(org: Org) {
    if (!confirm(`Delete "${org.name}" and ALL its data? This cannot be undone.`)) return;
    await superApi.deleteOrg(org.id).catch(() => {});
    await load();
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Organisations</h1>
          <p className="text-gray-500 mt-1">Manage all company workspaces on this platform</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="w-4 h-4" /> New organisation
        </Button>
      </div>

      {/* Invite modal */}
      {invite && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setInvite(null)}>
          <div className="bg-white rounded-xl border border-neutral-200 shadow-card p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-semibold text-gray-900 mb-1">Invite member</h2>
            <p className="text-xs text-gray-500 mb-4">Send an invitation to join this organisation.</p>
            {invite.result ? (
              <div className="space-y-3">
                <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                  Invitation created! Share this link:
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs bg-gray-100 rounded-lg px-3 py-2 break-all">{invite.result}</code>
                  <button onClick={copyLink}
                    className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 flex-shrink-0">
                    {invite.copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setInvite({ ...invite, result: null, email: "" })}>
                    Invite another
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setInvite(null)}>Done</Button>
                </div>
              </div>
            ) : (
              <form onSubmit={sendInvite} className="space-y-4">
                <Input label="Email address" type="email" value={invite.email}
                  onChange={(e) => setInvite({ ...invite, email: e.target.value })}
                  placeholder="colleague@company.com" required />
                <div>
                  <label className="text-sm font-medium text-gray-700">Role</label>
                  <select value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                    {ROLES.map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
                  </select>
                </div>
                {invite.error && <p className="text-sm text-red-600">{invite.error}</p>}
                <div className="flex gap-2">
                  <Button type="submit" loading={invite.loading}><Mail className="w-4 h-4" />Send invite</Button>
                  <Button type="button" variant="secondary" onClick={() => setInvite(null)}>Cancel</Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <Card className="p-6 mb-8">
          <h2 className="font-semibold text-gray-900 mb-5">Create new organisation</h2>
          <form onSubmit={create} className="grid grid-cols-2 gap-4">
            <Input label="Organisation name" value={form.name}
              onChange={(e) => handleName(e.target.value)} placeholder="Acme Corp" required />
            <Input label="Slug" value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })} placeholder="acme-corp" required />
            <Input label="Admin full name" value={form.admin_name}
              onChange={(e) => setForm({ ...form, admin_name: e.target.value })} placeholder="Jane Smith" required />
            <Input label="Admin email" type="email" value={form.admin_email}
              onChange={(e) => setForm({ ...form, admin_email: e.target.value })} placeholder="admin@acme.com" required />
            <div className="col-span-2">
              <Input label="Admin password" type="password" value={form.admin_password}
                onChange={(e) => setForm({ ...form, admin_password: e.target.value })}
                placeholder="Min. 8 characters" required minLength={8} />
            </div>
            {error && <p className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
            <div className="col-span-2 flex gap-3">
              <Button type="submit" loading={creating}><Building2 className="w-4 h-4" /> Create</Button>
              <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Orgs table */}
      <Card>
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : orgs.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Building2 className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p>No organisations yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {orgs.map((org) => (
              <div key={org.id} className="flex items-center gap-4 px-6 py-4">
                <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-brand-700">{org.name[0].toUpperCase()}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-900">{org.name}</p>
                    <span className="text-xs text-gray-400">/{org.slug}</span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {org.plan} · Created {new Date(org.created_at).toLocaleDateString()}
                  </p>
                </div>
                <StatusBadge status={org.active ? "active" : "suspended"} />
                <div className="flex items-center gap-2">
                  <button onClick={() => openInvite(org)}
                    className="p-1.5 rounded-lg text-brand-500 hover:bg-brand-50" title="Invite member">
                    <UserPlus className="w-4 h-4" />
                  </button>
                  <button onClick={() => toggleActive(org)}
                    className={`p-1.5 rounded-lg ${org.active ? "text-amber-500 hover:bg-amber-50" : "text-green-500 hover:bg-green-50"}`}
                    title={org.active ? "Suspend" : "Activate"}>
                    <Power className="w-4 h-4" />
                  </button>
                  <button onClick={() => del(org)}
                    className="p-1.5 rounded-lg text-red-500 hover:bg-red-50" title="Delete">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
