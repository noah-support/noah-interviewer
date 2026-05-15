"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getDiscoverySnapshot,
  getDiscoveryStateRooms,
  type DiscoverySnapshotResponse,
} from "../../../lib/api";
import { btnPrimary, btnSecondary } from "../../../lib/ui-brand";

export default function DiscoveryStatePage() {
  const [rooms, setRooms] = useState<string[]>([]);
  const [roomsError, setRoomsError] = useState<string | null>(null);
  const [manualRoom, setManualRoom] = useState("");
  const [selectedRoom, setSelectedRoom] = useState("");
  const [snapshot, setSnapshot] = useState<DiscoverySnapshotResponse | null>(null);
  const [snapError, setSnapError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const refreshRooms = useCallback(async () => {
    try {
      const { rooms: r } = await getDiscoveryStateRooms();
      setRooms(r);
      setRoomsError(null);
    } catch (e) {
      setRoomsError(e instanceof Error ? e.message : "Failed to list rooms");
    }
  }, []);

  useEffect(() => {
    void refreshRooms();
    const id = window.setInterval(() => void refreshRooms(), 4000);
    return () => window.clearInterval(id);
  }, [refreshRooms]);

  useEffect(() => {
    const room = selectedRoom.trim();
    const normalized = room.match(/^interview-(\d+)-([0-9a-f]{8})$/i);
    if (!normalized) {
      setSnapshot(null);
      setSnapError(null);
      return;
    }
    const roomKey = `interview-${normalized[1]}-${normalized[2].toLowerCase()}`;

    let cancelled = false;
    const tick = async () => {
      try {
        const s = await getDiscoverySnapshot(roomKey);
        if (!cancelled) {
          setSnapshot(s);
          setSnapError(null);
          setLastUpdated(new Date().toISOString());
        }
      } catch (e) {
        if (!cancelled) {
          setSnapError(e instanceof Error ? e.message : "Snapshot failed");
        }
      }
    };

    void tick();
    const id = window.setInterval(() => void tick(), 600);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [selectedRoom]);

  const jsonBlock = useMemo(() => {
    if (!snapshot) return "";
    if (!snapshot.exists) {
      return "No state key in Redis yet for this room (agent may not have joined, or key expired).";
    }
    return JSON.stringify(snapshot.state, null, 2);
  }, [snapshot]);

  const showLoading =
    Boolean(selectedRoom.trim().match(/^interview-\d+-[0-9a-f]{8}$/i)) &&
    snapshot === null &&
    !snapError;

  function followManual() {
    const raw = manualRoom.trim();
    const m = raw.match(/^interview-(\d+)-([0-9a-f]{8})$/i);
    if (m) {
      setSelectedRoom(`interview-${m[1]}-${m[2].toLowerCase()}`);
    }
  }

  return (
    <div className="min-h-screen bg-(--bg) text-(--text) px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6">
          <h1 className="text-2xl font-medium text-(--text-h)">Discovery state (Redis)</h1>
          <p className="mt-1 text-sm opacity-80">
            Pick a LiveKit room to poll the state manager JSON. Rooms appear after the agent has
            initialized Redis for that session.
          </p>
        </div>

        <div className="rounded border border-(--border) bg-(--bg) p-4 space-y-4 mb-6">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Room from Redis</span>
              <select
                className="min-w-[280px] rounded border border-(--border) bg-white px-3 py-2 font-mono text-sm"
                value={selectedRoom}
                onChange={(e) => setSelectedRoom(e.target.value)}
              >
                <option value="">— select —</option>
                {rooms.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void refreshRooms()}
              className={`px-3 py-2 text-sm ${btnSecondary}`}
            >
              Refresh list
            </button>
          </div>
          {roomsError ? (
            <p className="text-sm text-red-600">{roomsError}</p>
          ) : rooms.length === 0 ? (
            <p className="text-sm opacity-70">No rooms with state keys yet.</p>
          ) : null}

          <div className="flex flex-wrap items-end gap-2 border-t border-(--border) pt-4">
            <label className="flex flex-col gap-1 text-sm flex-1 min-w-[200px]">
              <span className="font-medium">Or enter room manually</span>
              <input
                type="text"
                placeholder="interview-1-a1b2c3d4"
                className="rounded border border-(--border) bg-white px-3 py-2 font-mono text-sm"
                value={manualRoom}
                onChange={(e) => setManualRoom(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && followManual()}
              />
            </label>
            <button
              type="button"
              onClick={followManual}
              className={`px-4 py-2 text-sm ${btnPrimary}`}
            >
              Follow
            </button>
          </div>
          <p className="text-xs opacity-60">
            Format: <code className="font-mono">interview-&lt;id&gt;-&lt;8 hex&gt;</code> (same as the
            livekit-token response).
          </p>
        </div>

        {selectedRoom ? (
          <div className="rounded border border-(--border) bg-(--bg) p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
              <span className="font-mono text-sm">{selectedRoom}</span>
              {snapshot ? (
                <span className="text-xs opacity-70">
                  buffer lines: {snapshot.buffer_line_count}
                  {lastUpdated ? ` · last poll ${lastUpdated}` : null}
                </span>
              ) : null}
            </div>
            {snapError ? <p className="text-sm text-red-600 mb-2">{snapError}</p> : null}
            <pre className="text-xs overflow-auto max-h-[70vh] rounded bg-black/4 dark:bg-white/6 p-4 font-mono whitespace-pre-wrap">
              {showLoading ? "Loading…" : jsonBlock}
            </pre>
          </div>
        ) : null}
      </div>
    </div>
  );
}
