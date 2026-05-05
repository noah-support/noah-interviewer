"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../lib/api";

export default function Page() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username.trim(), code.trim());
      router.push("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full min-h-screen flex flex-col items-center gap-6 px-4 py-10">
      <div className="w-full flex items-center justify-between max-w-xl">
        <h1 className="text-3xl font-medium">Noah Hub</h1>
        {username.length === 0 && code.length === 0 ? (
          <button
            type="button"
            onClick={() => router.push("/system-manager/projects")}
            className="px-3 py-2 rounded border border-(--border) hover:opacity-90"
          >
            system manager
          </button>
        ) : null}
      </div>

      <form onSubmit={onSubmit} className="w-full max-w-xl flex flex-col gap-4">
        <div className="flex flex-col gap-1 text-left">
          <label className="text-sm">Username</label>
          <input
            className="border border-(--border) rounded px-3 py-2 bg-transparent"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="default_user"
            autoComplete="username"
          />
        </div>

        <div className="flex flex-col gap-1 text-left">
          <label className="text-sm">Access code</label>
          <input
            className="border border-(--border) rounded px-3 py-2 bg-transparent"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="ABC123"
            autoComplete="one-time-code"
          />
        </div>

        {error ? <div className="text-left text-red-600 text-sm">{error}</div> : null}

        <button
          type="submit"
          disabled={loading}
          className="mt-2 px-6 py-3 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
