import type { AgentState } from "@livekit/components-react";

/** Short, literal status line shown under the audio visualizer. */
export function agentStateLabel(state: AgentState | undefined): string {
  switch (state) {
    case "connecting":
      return "Connecting…";
    case "pre-connect-buffering":
      return "Preparing connection…";
    case "initializing":
      return "Initializing…";
    case "listening":
      return "Listening…";
    case "thinking":
      return "Thinking…";
    case "speaking":
      return "Speaking…";
    case "idle":
      return "Ready";
    case "disconnected":
      return "Disconnected";
    case "failed":
      return "Connection failed";
    default:
      return "Connecting…";
  }
}
