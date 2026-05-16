"use client";

import { useEffect, useMemo, useRef } from "react";
import { TokenSource } from "livekit-client";
import { useAgent, useSession } from "@livekit/components-react";
import "@livekit/components-styles";

import { AgentSessionProvider } from "@/components/agents-ui/agent-session-provider";
import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura";
import { AgentControlBar } from "@/components/agents-ui/agent-control-bar";
import { InterviewAgentErrorScreen } from "@/components/interview-agent-error-screen";
import { useInterviewAgentError } from "@/hooks/use-interview-agent-error";
import { agentStateLabel } from "@/lib/agent-state-label";
import { errorFromUnknown } from "@/lib/interview-agent-error";

type InterviewLiveKitSessionProps = {
  serverUrl: string;
  token: string;
  onEndCall: () => void;
  /** Called when the user leaves after a fatal agent error (return to start screen). */
  onLeaveAfterError?: () => void;
};

export function InterviewLiveKitSession({
  serverUrl,
  token,
  onEndCall,
  onLeaveAfterError,
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

  const {
    fatalError,
    tryingAgain,
    markUserLeave,
    reportError,
    handleStartFailure,
    retrySession,
  } = useInterviewAgentError({ session, agent });

  useEffect(() => {
    const s = sessionRef.current;
    void s
      .start({
        tracks: {
          microphone: { enabled: true },
        },
      })
      .catch(handleStartFailure);

    return () => {
      void s.end().catch(() => undefined);
    };
  }, [serverUrl, token, handleStartFailure]);

  function handleDisconnect() {
    markUserLeave();
    onEndCall();
  }

  function handleLeaveAfterError() {
    markUserLeave();
    void session.end().catch(() => undefined);
    if (onLeaveAfterError) {
      onLeaveAfterError();
    } else {
      onEndCall();
    }
  }

  if (fatalError) {
    return (
      <InterviewAgentErrorScreen
        error={fatalError}
        tryingAgain={tryingAgain}
        onTryAgain={() => void retrySession()}
        onLeave={handleLeaveAfterError}
      />
    );
  }

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
          onDisconnect={handleDisconnect}
          onDeviceError={({ error }) => {
            reportError(
              errorFromUnknown(
                error,
                "Could not access your microphone. Check browser permissions and try again.",
              ),
            );
          }}
          className="w-full max-w-md border-neutral-200 bg-white shadow-sm"
        />
      </div>
    </AgentSessionProvider>
  );
}
