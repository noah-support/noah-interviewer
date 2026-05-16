import type { UseAgentReturn, UseSessionReturn } from "@livekit/components-react";
import { ConnectionState, RoomEvent } from "livekit-client";

export type InterviewAgentError = {
  title: string;
  message: string;
};

const DEFAULT_TITLE = "Interview unavailable";

export function formatAgentFailureReasons(reasons: string[] | null | undefined): string {
  if (!reasons?.length) {
    return "The voice assistant could not connect. Please try again in a moment.";
  }
  return reasons.join(" ");
}

export function errorFromAgent(agent: UseAgentReturn): InterviewAgentError | null {
  if (agent.state !== "failed") {
    return null;
  }
  const reasons =
    "failureReasons" in agent && Array.isArray(agent.failureReasons)
      ? agent.failureReasons
      : [];
  return {
    title: DEFAULT_TITLE,
    message: formatAgentFailureReasons(reasons),
  };
}

export function errorFromUnknown(err: unknown, fallback = "Something went wrong."): InterviewAgentError {
  return {
    title: DEFAULT_TITLE,
    message: err instanceof Error ? err.message : fallback,
  };
}

/** Unexpected room drop after the interview had connected. */
export function errorFromUnexpectedDisconnect(): InterviewAgentError {
  return {
    title: DEFAULT_TITLE,
    message:
      "The connection to the interview was lost. Check your network and try starting again.",
  };
}

export function shouldTreatDisconnectAsFatal(
  session: UseSessionReturn,
  wasConnected: boolean,
  userInitiatedLeave: boolean,
): boolean {
  if (userInitiatedLeave) {
    return false;
  }
  if (!wasConnected) {
    return false;
  }
  return session.connectionState === ConnectionState.Disconnected;
}

export { ConnectionState, RoomEvent };
