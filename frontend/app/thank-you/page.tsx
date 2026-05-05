"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getInterviewDetail, logout, me, type InterviewDetail } from "../../lib/api";

export default function ThankYouPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const m = await me();
        const d = await getInterviewDetail(m.id);
        if (!cancelled) setDetail(d);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load interview");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onBackToHome() {
    setLoading(true);
    try {
      await logout();
      router.push("/");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-(--bg) px-4">
      <div className="w-full max-w-3xl rounded border border-(--border) bg-(--bg) p-8">
        <h1 className="text-2xl font-medium">Thank you</h1>
        <p className="mt-2 text-sm text-(--text)">Your session has ended.</p>

        {error ? <div className="mt-4 text-sm text-red-600">{error}</div> : null}

        <div className="mt-6 grid grid-cols-1 gap-6">
          <div>
            <div className="text-sm font-medium mb-2">summary</div>
            <textarea
              className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-transparent"
              value={detail?.summary || ""}
              readOnly
            />
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end">
          <button
            type="button"
            onClick={onBackToHome}
            disabled={loading}
            className="px-6 py-3 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Returning..." : "Back to home"}
          </button>
        </div>
      </div>
    </div>
  );
}
