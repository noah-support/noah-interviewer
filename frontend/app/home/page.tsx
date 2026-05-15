"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { InterviewLiveKitSession } from "../../components/interview-livekit-session";
import { MicCheckModal } from "../../components/mic-check-modal";
import { me, startInterview, type MeResponse } from "../../lib/api";
import { btnPrimary } from "../../lib/ui-brand";

export default function HomePage() {
  const router = useRouter();
  const serverUrl = useMemo(() => process.env.NEXT_PUBLIC_LIVEKIT_URL || "", []);

  const [authLoading, setAuthLoading] = useState(true);
  const [interview, setInterview] = useState<MeResponse | null>(null);

  const [connected, setConnected] = useState(false);
  const [starting, setStarting] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [room, setRoom] = useState<string | null>(null);
  const [micModalOpen, setMicModalOpen] = useState(false);
  const [micCheckKey, setMicCheckKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setAuthLoading(true);
      try {
        const m = await me();
        if (cancelled) return;
        setInterview(m);
      } catch {
        if (cancelled) return;
        router.push("/");
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onConfirmMicAndStart() {
    if (!interview) return;
    setStarting(true);
    try {
      const { token, room } = await startInterview(interview.id);
      setToken(token);
      setRoom(room);
      setConnected(true);
      setMicModalOpen(false);
    } finally {
      setStarting(false);
    }
  }

  async function onEndInterview() {
    if (!interview) return;
    // Navigate immediately so the user sees the "Saving..." spinner right away.
    const qs = room ? `?room=${encodeURIComponent(room)}` : "";
    router.replace(`/saving${qs}`);
  }

  if (authLoading) return <div className="py-10">Loading...</div>;
  if (!interview) return <div className="py-10">Authentication required.</div>;
  if (!serverUrl) return <div className="py-10">Missing `NEXT_PUBLIC_LIVEKIT_URL`.</div>;

  if (!connected) {
    return (
      <>
        <MicCheckModal
          key={micCheckKey}
          open={micModalOpen}
          onClose={() => setMicModalOpen(false)}
          onConfirmStart={() => void onConfirmMicAndStart()}
          starting={starting}
        />
        <div className="min-h-screen flex items-center justify-center bg-(--bg) px-4">
          <div className="flex flex-col items-center gap-6">
            <div className="text-left max-w-xl">
              <h1 className="text-3xl font-medium">Interview</h1>
              <p className="mt-2 text-sm">
                User: <span className="font-medium">{interview.username}</span> · Status:{" "}
                <span className="font-medium">{interview.status}</span>
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setMicCheckKey((k) => k + 1);
                setMicModalOpen(true);
              }}
              disabled={starting}
              className={`px-8 py-4 text-lg ${btnPrimary}`}
            >
              Click to Start Conversation
            </button>
          </div>
        </div>
      </>
    );
  }

  if (!token) return <div className="py-10">Getting token...</div>;
  return (
    <InterviewLiveKitSession
      serverUrl={serverUrl}
      token={token}
      onEndCall={onEndInterview}
    />
  );
}

