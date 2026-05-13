"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, Building2, User, Check, ArrowRight } from "lucide-react";
import { authApi } from "@/lib/api";

type Step = "org" | "admin";

const fieldCls = "h-10 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors";
const labelCls = "block text-sm font-medium text-neutral-300 mb-1.5";

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("org");

  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  function handleOrgName(v: string) {
    setOrgName(v);
    setOrgSlug(v.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (step === "org") { setStep("admin"); return; }
    setError("");
    setLoading(true);
    try {
      const res = await authApi.register({
        org_name: orgName, org_slug: orgSlug,
        full_name: fullName, email, password,
      });
      localStorage.setItem("access_token",  res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      router.push("/admin");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  const isOrgDone = step === "admin";

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md animate-fade-in">

        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-white font-semibold text-sm">DocIntel</span>
        </div>

        <h1 className="text-2xl font-semibold text-white tracking-tight mb-1">
          Create your workspace
        </h1>
        <p className="text-neutral-400 text-sm mb-8">
          Set up DocIntel for your company in under 2 minutes.
        </p>

        {/* Stepper */}
        <div className="flex items-center gap-3 mb-8">
          {([
            { id: "org",   icon: Building2, label: "Company" },
            { id: "admin", icon: User,      label: "Your account" },
          ] as { id: Step; icon: typeof Building2; label: string }[]).map((s, i) => {
            const done    = s.id === "org" && isOrgDone;
            const current = s.id === step;
            return (
              <div key={s.id} className="flex items-center gap-2">
                {i > 0 && <div className={`h-px w-8 ${isOrgDone ? "bg-brand-600" : "bg-neutral-800"}`} />}
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 transition-colors ${
                  done    ? "bg-brand-600 text-white" :
                  current ? "bg-neutral-700 text-white ring-2 ring-brand-500 ring-offset-1 ring-offset-neutral-950" :
                            "bg-neutral-800 text-neutral-500"
                }`}>
                  {done ? <Check className="w-3.5 h-3.5" /> : i + 1}
                </div>
                <span className={`text-xs font-medium ${current ? "text-white" : "text-neutral-500"}`}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Form card */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {step === "org" ? (
              <>
                <div>
                  <label className={labelCls}>Company name</label>
                  <input
                    value={orgName}
                    onChange={(e) => handleOrgName(e.target.value)}
                    placeholder="Acme Corporation"
                    required
                    className={fieldCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>Workspace slug</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">docintel.co/</span>
                    <input
                      value={orgSlug}
                      onChange={(e) => setOrgSlug(e.target.value)}
                      placeholder="acme-corp"
                      required
                      pattern="[a-z0-9-]{2,40}"
                      className={`${fieldCls} pl-[6.5rem]`}
                    />
                  </div>
                  <p className="text-xs text-neutral-500 mt-1.5">Lowercase letters, digits, hyphens only (2–40 chars)</p>
                </div>
                <button type="submit" className="w-full h-10 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium flex items-center justify-center gap-2 transition-colors mt-2">
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                <div>
                  <label className={labelCls}>Your full name</label>
                  <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Smith" required className={fieldCls} />
                </div>
                <div>
                  <label className={labelCls}>Work email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jane@acme.com" required className={fieldCls} />
                </div>
                <div>
                  <label className={labelCls}>Password</label>
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min. 8 characters" required minLength={8} className={fieldCls} />
                </div>

                {error && (
                  <div className="text-sm text-red-400 bg-red-950 border border-red-900 rounded-lg px-3 py-2.5">
                    {error}
                  </div>
                )}

                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setStep("org")}
                    className="flex-1 h-10 rounded-lg border border-neutral-700 text-neutral-300 text-sm font-medium hover:bg-neutral-800 transition-colors">
                    Back
                  </button>
                  <button type="submit" disabled={loading}
                    className="flex-1 h-10 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50">
                    {loading
                      ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      : "Create workspace"
                    }
                  </button>
                </div>
              </>
            )}
          </form>
        </div>

        <p className="text-center text-sm text-neutral-500 mt-6">
          Already have a workspace?{" "}
          <Link href="/login" className="text-brand-400 hover:text-brand-300 font-medium transition-colors">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
