"use client";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { FileText } from "lucide-react";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function AcceptInvitePage() {
  const { token } = useParams<{ token: string }>();
  const router    = useRouter();

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.acceptInvite(token, fullName, password);
      localStorage.setItem("access_token",  res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      router.push("/app");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not accept invitation.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-brand-600 rounded-xl flex items-center justify-center mb-3 shadow-sm">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Accept invitation</h1>
          <p className="text-sm text-gray-500 mt-1">Set up your DocIntel account</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Your name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Smith"
              required
            />
            <Input
              label="Choose a password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 8 characters"
              required
              minLength={8}
            />
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <Button type="submit" size="lg" className="w-full" loading={loading}>
              Create account
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
