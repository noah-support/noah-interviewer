"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ControlBar,
  LiveKitRoom,
  RoomAudioRenderer,
} from "@livekit/components-react";
import "@livekit/components-styles";

import { endInterview, me, startInterview, type MeResponse } from "../../lib/api";

export default function HomePage() {
  const router = useRouter();
  const serverUrl = useMemo(() => process.env.NEXT_PUBLIC_LIVEKIT_URL || "", []);

  const [authLoading, setAuthLoading] = useState(true);
  const [interview, setInterview] = useState<MeResponse | null>(null);

  const [connected, setConnected] = useState(false);
  const [starting, setStarting] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [room, setRoom] = useState<string | null>(null);
  const [ending, setEnding] = useState(false);

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

  async function onStartConversation() {
    if (!interview) return;
    setStarting(true);
    try {
      const { token, room } = await startInterview(interview.id);
      setToken(token);
      setRoom(room);
      setConnected(true);
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
            onClick={onStartConversation}
            disabled={starting}
            className="px-8 py-4 text-lg rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
          >
            {starting ? "Starting..." : "Click to Start Conversation"}
          </button>
        </div>
      </div>
    );
  }

  if (!token) return <div className="py-10">Getting token...</div>;
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white">
      <h1 className="text-2xl font-medium text-(--text-h)">Noah Voice Assistant</h1>

      <LiveKitRoom
        video={false}
        audio={true}
        token={token}
        serverUrl={serverUrl}
        connect={true}
        data-lk-theme="default"
      >
        <RoomAudioRenderer />
        <div style={{ marginTop: "20px" }}>
          <ControlBar
            variation="minimal"
            // Keep mic toggle, hide the built-in leave/exit button.
            controls={{
              microphone: true,
              camera: false,
              screenShare: false,
              leave: false,
            }}
          />
        </div>
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={onEndInterview}
            disabled={ending}
            className="px-6 py-3 rounded border border-(--border) hover:opacity-90 disabled:opacity-50"
          >
            {ending ? "Ending..." : "End interview"}
          </button>
        </div>
      </LiveKitRoom>
    </div>
  );
}

