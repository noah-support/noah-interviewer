"use client";

import { useEffect, useMemo, useRef } from "react";
import { TokenSource } from "livekit-client";
import { useAgent, useSession } from "@livekit/components-react";
import "@livekit/components-styles";

import { AgentSessionProvider } from "@/components/agents-ui/agent-session-provider";
import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura";
import { AgentControlBar } from "@/components/agents-ui/agent-control-bar";
import { agentStateLabel } from "@/lib/agent-state-label";

type InterviewLiveKitSessionProps = {
  serverUrl: string;
  token: string;
  onEndCall: () => void;
};

export function InterviewLiveKitSession({
  serverUrl,
  token,
  onEndCall,
}: InterviewLiveKitSessionProps) {
  const tokenSource = useMemo(
    () =>
      TokenSource.literal({
        serverUrl,
        participantToken: token,
      }),
    [serverUrl, token],
  );

  const session = useSession(tokenSource, {});
  const agent = useAgent(session);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  useEffect(() => {
    const s = sessionRef.current;
    void s
      .start({
        tracks: {
          microphone: { enabled: true },
        },
      })
      .catch((err) => {
        console.warn("[LiveKit] session.start failed:", err);
      });

    return () => {
      void s.end().catch(() => undefined);
    };
  }, [serverUrl, token]);

  return (
    <AgentSessionProvider session={session}>
      <div
        className="flex min-h-screen flex-col items-center justify-center gap-8 bg-white px-4 py-10 text-neutral-900"
        data-lk-theme="light"
      >
        <h1 className="text-2xl font-medium text-neutral-900">Noah Voice Assistant</h1>

        <AgentAudioVisualizerAura
          size="xl"
          themeMode="light"
          state={agent.state}
          audioTrack={agent.microphoneTrack}
          className="text-[#3540A8]"
        />

        <p
          className="min-h-5 text-sm text-neutral-500"
          aria-live="polite"
          aria-atomic="true"
        >
          {agentStateLabel(agent.state)}
        </p>

        <AgentControlBar
          variant="livekit"
          isConnected={session.isConnected}
          controls={{
            microphone: true,
            leave: true,
            camera: false,
            screenShare: false,
            chat: false,
          }}
          onDisconnect={onEndCall}
          className="w-full max-w-md border-neutral-200 bg-white shadow-sm"
        />
      </div>
    </AgentSessionProvider>
  );
}
