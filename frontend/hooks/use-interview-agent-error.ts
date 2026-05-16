"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { SessionEvent, type UseAgentReturn, type UseSessionReturn } from "@livekit/components-react";
import { ConnectionState, RoomEvent } from "livekit-client";

import {
  errorFromAgent,
  errorFromUnexpectedDisconnect,
  errorFromUnknown,
  type InterviewAgentError,
} from "@/lib/interview-agent-error";

type UseInterviewAgentErrorOptions = {
  session: UseSessionReturn;
  agent: UseAgentReturn;
};

export function useInterviewAgentError({ session, agent }: UseInterviewAgentErrorOptions) {
  const [fatalError, setFatalError] = useState<InterviewAgentError | null>(null);
  const [tryingAgain, setTryingAgain] = useState(false);
  const userInitiatedLeaveRef = useRef(false);
  const wasConnectedRef = useRef(false);

  const reportError = useCallback((error: InterviewAgentError) => {
    setFatalError((prev) => prev ?? error);
  }, []);

  const clearError = useCallback(() => {
    setFatalError(null);
  }, []);

  const markUserLeave = useCallback(() => {
    userInitiatedLeaveRef.current = true;
  }, []);

  // Agent failed to connect or disconnected unexpectedly.
  useEffect(() => {
    const agentError = errorFromAgent(agent);
    if (agentError) {
      reportError(agentError);
    }
  }, [agent, reportError]);

  // Track whether the room had connected successfully.
  useEffect(() => {
    if (session.isConnected) {
      wasConnectedRef.current = true;
    }
  }, [session.isConnected]);

  // Room-level disconnect (network / server).
  useEffect(() => {
    const room = session.room;
    const onDisconnected = () => {
      if (userInitiatedLeaveRef.current || !wasConnectedRef.current) {
        return;
      }
      reportError(errorFromUnexpectedDisconnect());
    };

    room.on(RoomEvent.Disconnected, onDisconnected);
    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
    };
  }, [session.room, reportError]);

  // Session connection state after a successful connect.
  useEffect(() => {
    if (userInitiatedLeaveRef.current) {
      return;
    }
    if (
      wasConnectedRef.current &&
      session.connectionState === ConnectionState.Disconnected &&
      !session.isConnected
    ) {
      reportError(errorFromUnexpectedDisconnect());
    }
  }, [session.connectionState, session.isConnected, reportError]);

  // Microphone / media device errors from the session.
  useEffect(() => {
    const emitter = session.internal.emitter;
    const onMediaDevicesError = (error: Error) => {
      reportError(
        errorFromUnknown(
          error,
          "Could not access your microphone. Check browser permissions and try again.",
        ),
      );
    };

    emitter.on(SessionEvent.MediaDevicesError, onMediaDevicesError);
    return () => {
      emitter.off(SessionEvent.MediaDevicesError, onMediaDevicesError);
    };
  }, [session, reportError]);

  const handleStartFailure = useCallback(
    (err: unknown) => {
      reportError(
        errorFromUnknown(
          err,
          "Could not start the interview session. Please try again.",
        ),
      );
    },
    [reportError],
  );

  const retrySession = useCallback(async () => {
    setTryingAgain(true);
    clearError();
    userInitiatedLeaveRef.current = false;
    try {
      await session.end().catch(() => undefined);
      await session.start({
        tracks: {
          microphone: { enabled: true },
        },
      });
    } catch (err) {
      handleStartFailure(err);
    } finally {
      setTryingAgain(false);
    }
  }, [session, clearError, handleStartFailure]);

  return {
    fatalError,
    tryingAgain,
    reportError,
    clearError,
    markUserLeave,
    handleStartFailure,
    retrySession,
  };
}
