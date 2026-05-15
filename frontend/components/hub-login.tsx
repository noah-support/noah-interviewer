"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { CodeInput6 } from "./code-input-6";
import { login } from "../lib/api";
import { btnPrimary, btnSecondary } from "../lib/ui-brand";

type HubLoginProps = {
  showSystemManager: boolean;
};

export function HubLogin({ showSystemManager }: HubLoginProps) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const access = code.trim().toUpperCase();
    if (access.length !== 6) {
      setError("Enter the full 6-character access code.");
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), access);
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
        {showSystemManager && username.length === 0 && code.length === 0 ? (
          <button
            type="button"
            onClick={() => router.push("/system-manager/projects")}
            className={`px-3 py-2 text-sm ${btnSecondary}`}
          >
            system manager
          </button>
        ) : null}
      </div>

      <form onSubmit={onSubmit} className="w-full max-w-xl flex flex-col gap-4">
        <div className="flex flex-col gap-1 text-left">
          <label className="text-sm">Username</label>
          <input
            className="border border-(--border) rounded px-3 py-2 bg-white"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="default_user"
            autoComplete="username"
          />
        </div>

        <div className="flex flex-col gap-2 text-left">
          <span className="text-sm">Access code (6 characters)</span>
          <CodeInput6
            value={code}
            onChange={setCode}
            autoComplete="one-time-code"
            aria-label="Access code"
          />
        </div>

        {error ? <div className="text-left text-red-600 text-sm">{error}</div> : null}

        <button
          type="submit"
          disabled={loading}
          className={`mt-2 px-6 py-3 text-base ${btnPrimary}`}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
