"use client";

import { btnPrimary, btnSecondary } from "@/lib/ui-brand";
import type { InterviewAgentError } from "@/lib/interview-agent-error";

type InterviewAgentErrorScreenProps = {
  error: InterviewAgentError;
  onTryAgain?: () => void;
  onLeave: () => void;
  tryingAgain?: boolean;
};

export function InterviewAgentErrorScreen({
  error,
  onTryAgain,
  onLeave,
  tryingAgain = false,
}: InterviewAgentErrorScreenProps) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center bg-(--bg) px-4 py-10 text-neutral-900"
      role="alert"
    >
      <div className="w-full max-w-md rounded border border-(--border) bg-white p-8 text-center shadow-sm">
        <div
          className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600"
          aria-hidden
        >
          <span className="text-xl font-semibold">!</span>
        </div>

        <h1 className="text-xl font-medium text-neutral-900">{error.title}</h1>
        <p className="mt-3 text-sm leading-relaxed text-neutral-600">{error.message}</p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
          {onTryAgain ? (
            <button
              type="button"
              className={`px-5 py-2.5 text-sm ${btnPrimary}`}
              disabled={tryingAgain}
              onClick={onTryAgain}
            >
              {tryingAgain ? "Reconnecting…" : "Try again"}
            </button>
          ) : null}
          <button
            type="button"
            className={`px-5 py-2.5 text-sm ${btnSecondary}`}
            disabled={tryingAgain}
            onClick={onLeave}
          >
            Leave interview
          </button>
        </div>
      </div>
    </div>
  );
}
