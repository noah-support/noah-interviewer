"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { endInterview, me } from "../../lib/api";

function Spinner() {
  return (
    <div
      className="h-10 w-10 rounded-full border-4 border-(--border) border-t-blue-600 animate-spin"
      aria-label="Loading"
    />
  );
}

export default function SavingPage() {
  const router = useRouter();

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const room =
          typeof window !== "undefined"
            ? new URLSearchParams(window.location.search).get("room") || undefined
            : undefined;
        const m = await me();
        await endInterview(m.id, { room });
        if (!cancelled) router.replace("/thank-you");
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to save");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-(--bg) px-4">
      <div className="w-full max-w-md rounded border border-(--border) bg-(--bg) p-8">
        <div className="flex items-center gap-4">
          <Spinner />
          <div>
            <div className="text-lg font-medium">Saving</div>
            <div className="text-sm text-(--text) opacity-80">
              Please keep this tab open while we save your interview.
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-6 text-sm text-red-600">
            {error}
            <div className="mt-2">
              <button
                type="button"
                className="px-4 py-2 rounded border border-(--border) hover:opacity-90"
                onClick={() => router.replace("/thank-you")}
              >
                Continue
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

