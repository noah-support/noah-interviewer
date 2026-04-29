import { useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  ControlBar,
} from "@livekit/components-react";
import "@livekit/components-styles";

export default function App() {
  const [token] = useState<string>(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MDc5MDA5MDAsImlkZW50aXR5IjoidGVzdC11c2VyIiwiaXNzIjoiZGV2a2V5IiwibmFtZSI6InRlc3QtdXNlciIsIm5iZiI6MTc3NjM2NDkwMCwic3ViIjoidGVzdC11c2VyIiwidmlkZW8iOnsicm9vbSI6Im15LXJvb20iLCJyb29tSm9pbiI6dHJ1ZX19.PDKAli4YKwJ6Vqw2nF7puc0IA6IEHA_oWujgDgbuPMA",
  );
  // Add a new state to track if the user has clicked start
  const [connected, setConnected] = useState(false);

  const serverUrl = import.meta.env.VITE_LIVEKIT_URL;

  if (!token) return <div>Getting token...</div>;

  // Render a start screen FIRST to satisfy browser autoplay policies
  if (!connected) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#F6F3EC",
        }}
      >
        <button
          onClick={() => setConnected(true)}
          style={{
            padding: "16px 32px",
            fontSize: "18px",
            cursor: "pointer",
            borderRadius: "8px",
            border: "none",
            backgroundColor: "#3b82f6",
            color: "white",
          }}
        >
          Click to Start Conversation
        </button>
      </div>
    );
  }

  // Once clicked, render the room
  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#FFFFFF",
        color: "white",
      }}
    >
      <h1>Noah Voice Assistant</h1>

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
            controls={{ microphone: true, camera: false, screenShare: false }}
          />
        </div>
      </LiveKitRoom>
    </div>
  );
}
