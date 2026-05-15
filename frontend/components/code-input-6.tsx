"use client";

import { useCallback, useId, useRef } from "react";

const CELL_COUNT = 6;
const ALLOWED = /^[A-Za-z0-9]$/;

function normalizePasted(raw: string): string {
  const alnum = raw.replace(/[^A-Za-z0-9]/g, "").slice(0, CELL_COUNT);
  return alnum.toUpperCase();
}

export type CodeInput6Props = {
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
  autoComplete?: string;
  "aria-label"?: string;
};

export function CodeInput6(props: CodeInput6Props) {
  const baseId = useId();
  const refs = useRef<(HTMLInputElement | null)[]>([]);

  const cells = Array.from({ length: CELL_COUNT }, (_, i) => props.value[i] ?? "");

  const focusCell = useCallback((index: number) => {
    const el = refs.current[Math.max(0, Math.min(CELL_COUNT - 1, index))];
    el?.focus();
    el?.select();
  }, []);

  const setFromString = useCallback(
    (raw: string) => {
      const next = normalizePasted(raw);
      props.onChange(next);
    },
    [props],
  );

  return (
    <div
      className="flex gap-2"
      role="group"
      aria-label={props["aria-label"] ?? "Access code"}
    >
      {cells.map((ch, i) => (
        <input
          key={i}
          id={`${baseId}-${i}`}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="text"
          inputMode="text"
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
          maxLength={1}
          disabled={props.disabled}
          autoComplete={i === 0 ? props.autoComplete : "off"}
          className="h-11 w-10 rounded border border-(--border) bg-white text-center text-lg font-mono uppercase outline-none focus-visible:ring-2 focus-visible:ring-[#3540A8] disabled:opacity-50"
          value={ch}
          aria-label={`Character ${i + 1} of ${CELL_COUNT}`}
          onChange={(e) => {
            const v = e.target.value;
            if (v === "") {
              const next =
                props.value.slice(0, i) + props.value.slice(i + 1);
              props.onChange(next);
              return;
            }
            const last = v.slice(-1);
            if (!ALLOWED.test(last)) return;
            const combined = (
              props.value.slice(0, i) +
              last.toUpperCase() +
              props.value.slice(i + 1)
            ).slice(0, CELL_COUNT);
            props.onChange(combined);
            if (combined.length < CELL_COUNT) focusCell(i + 1);
          }}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !ch && i > 0) {
              e.preventDefault();
              focusCell(i - 1);
            }
            if (e.key === "ArrowLeft" && i > 0) {
              e.preventDefault();
              focusCell(i - 1);
            }
            if (e.key === "ArrowRight" && i < CELL_COUNT - 1) {
              e.preventDefault();
              focusCell(i + 1);
            }
          }}
          onPaste={(e) => {
            e.preventDefault();
            const text = e.clipboardData.getData("text") || "";
            setFromString(text);
            const len = normalizePasted(text).length;
            focusCell(Math.min(len, CELL_COUNT - 1));
          }}
        />
      ))}
    </div>
  );
}
