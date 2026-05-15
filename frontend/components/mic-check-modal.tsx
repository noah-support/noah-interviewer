"use client";

import { useEffect, useRef, useState } from "react";

import { btnPrimary, btnSecondary } from "@/lib/ui-brand";

type MicCheckModalProps = {
  open: boolean;
  onClose: () => void;
  onConfirmStart: () => void;
  starting: boolean;
};

export function MicCheckModal(props: MicCheckModalProps) {
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [level, setLevel] = useState(0);
  const streamRef = useRef<MediaStream | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!props.open) return;

    let cancelled = false;

    (async () => {
      setError(null);
      setReady(false);
      setLevel(0);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const ctx = new AudioContext();
        ctxRef.current = ctx;
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        const data = new Uint8Array(analyser.frequencyBinCount);
        setReady(true);

        const tick = () => {
          if (cancelled) return;
          analyser.getByteFrequencyData(data);
          let sum = 0;
          for (let i = 0; i < data.length; i++) sum += data[i];
          const avg = sum / data.length / 255;
          setLevel(avg);
          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Microphone access was denied or no microphone was found.",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      void ctxRef.current?.close();
      ctxRef.current = null;
    };
  }, [props.open]);

  if (!props.open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" aria-hidden onClick={() => props.onClose()} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="mic-check-title"
        className="relative w-full max-w-md rounded-lg border border-(--border) bg-(--bg) p-6 shadow-lg"
      >
        <h2 id="mic-check-title" className="text-lg font-medium text-(--text-h)">
          Microphone check
        </h2>
        <p className="mt-2 text-sm text-(--text) opacity-90">
          We need to use your microphone for the interview. Allow access when your browser asks, then
          confirm you see activity below.
        </p>

        {error ? (
          <p className="mt-4 text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}

        {ready && !error ? (
          <div className="mt-4 space-y-2">
            <p className="text-sm font-medium text-green-700 dark:text-green-400">
              Microphone connected — speak to test the level.
            </p>
            <div
              className="h-2 w-full overflow-hidden rounded-full bg-black/10 dark:bg-white/10"
              aria-hidden
            >
              <div
                className="h-full rounded-full bg-[#3540A8] transition-[width] duration-75"
                style={{ width: `${Math.min(100, Math.round(level * 400))}%` }}
              />
            </div>
          </div>
        ) : null}

        {!ready && !error ? (
          <p className="mt-4 text-sm text-(--text) opacity-80">Waiting for microphone…</p>
        ) : null}

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            className={`px-4 py-2 text-sm ${btnSecondary}`}
            onClick={() => props.onClose()}
            disabled={props.starting}
          >
            Cancel
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm ${btnPrimary}`}
            onClick={() => props.onConfirmStart()}
            disabled={!ready || Boolean(error) || props.starting}
          >
            {props.starting ? "Starting…" : "Start interview"}
          </button>
        </div>
      </div>
    </div>
  );
}
