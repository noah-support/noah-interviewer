"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { CodeInput6 } from "../../../../../components/code-input-6";
import {
  createInterview,
  deleteInterview,
  getInterviews,
  getInterviewDetail,
  updateInterview,
  type InterviewDetail,
  type InterviewRow,
} from "../../../../../lib/api";
import { btnPrimary, btnSecondary } from "../../../../../lib/ui-brand";

function Modal(props: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  actions?: React.ReactNode;
  maxWidthClassName?: string;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={props.onClose} />
      <div
        className={`relative w-full ${props.maxWidthClassName || "max-w-2xl"} rounded border border-(--border) bg-(--bg) p-6`}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-medium">{props.title}</h2>
          <button type="button" onClick={props.onClose} className={`px-2 py-1 text-sm ${btnSecondary}`}>
            Close
          </button>
        </div>
        <div className="flex flex-col gap-4">{props.children}</div>
        {props.actions ? <div className="mt-6">{props.actions}</div> : null}
      </div>
    </div>
  );
}

const STATUS_OPTIONS = ["Ready", "paused", "failed", "done"];

function DiscoveryStateSection(props: { rawJson?: string }) {
  const formatted = useMemo(() => {
    const raw = (props.rawJson || "").trim();
    if (!raw) return "(No discovery state saved yet — run an interview and end the session to persist.)";
    try {
      return JSON.stringify(JSON.parse(raw), null, 2);
    } catch {
      return raw;
    }
  }, [props.rawJson]);

  return (
    <div className="text-left border-t border-(--border) pt-4 mt-2">
      <div className="text-sm mb-1 font-medium">Discovery state (saved from Redis)</div>
      <p className="text-xs opacity-70 mb-2">
        Last persisted JSON snapshot from the live session. Editable only via a new interview run.
      </p>
      <pre className="w-full max-h-72 overflow-auto border border-(--border) rounded px-3 py-2 bg-black/4 dark:bg-white/6 text-xs font-mono whitespace-pre-wrap">
        {formatted}
      </pre>
    </div>
  );
}

export default function InterviewsPage() {
  const params = useParams();
  const projectId = Number(params.projectId);

  const [interviews, setInterviews] = useState<InterviewRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit" | "view">("create");
  const [modalInterviewId, setModalInterviewId] = useState<number | null>(null);

  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<string>("Ready");
  const [content, setContent] = useState("");
  const [summary, setSummary] = useState("");

  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);

  const codeValid = /^[A-Za-z0-9]{6}$/.test(code);
  const canSaveInterview =
    Boolean(username.trim()) && codeValid && (modalMode === "create" || modalMode === "edit");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const rows = await getInterviews(projectId);
        if (!cancelled) setInterviews(rows);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function refresh() {
    setLoading(true);
    try {
      const rows = await getInterviews(projectId);
      setInterviews(rows);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setModalMode("create");
    setModalInterviewId(null);
    setUsername("");
    setCode("");
    setCodeError(null);
    setStatus("Ready");
    setContent("");
    setSummary("");
    setDetail(null);
    setModalLoading(false);
    setModalOpen(true);
  }

  async function openEdit(row: InterviewRow) {
    setModalMode("edit");
    setModalInterviewId(row.id);
    setDetail(null);
    setCodeError(null);
    setModalOpen(true);
    setModalLoading(true);
    try {
      const d = await getInterviewDetail(row.id);
      setDetail(d);
      setUsername(d.username);
      setCode(d.code.replace(/[^A-Za-z0-9]/g, "").slice(0, 6).toUpperCase());
      setStatus(d.status);
      setContent(d.content);
      setSummary(d.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load details");
    } finally {
      setModalLoading(false);
    }
  }

  async function openView(row: InterviewRow) {
    setModalMode("view");
    setModalInterviewId(row.id);
    setDetail(null);
    setModalLoading(false);
    setModalOpen(true);
    try {
      const d = await getInterviewDetail(row.id);
      setDetail(d);
      setUsername(d.username);
      setCode(d.code);
      setStatus(d.status);
      setContent(d.content);
      setSummary(d.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load details");
    }
  }

  async function submitEditOrCreate() {
    if (!username.trim()) return;
    if (!codeValid) {
      setCodeError("Access code must be exactly 6 letters or numbers.");
      return;
    }
    setCodeError(null);
    setLoading(true);
    try {
      if (modalMode === "create") {
        await createInterview(projectId, {
          username: username.trim(),
          code: code.trim().toUpperCase(),
          status,
        });
      } else if (modalMode === "edit" && modalInterviewId != null) {
        await updateInterview(modalInterviewId, {
          username: username.trim(),
          code: code.trim().toUpperCase(),
          status,
          content,
          summary,
        });
      }
      setModalOpen(false);
      await refresh();
    } catch (err) {
      setCodeError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  async function deleteInterviewById(id: number) {
    const ok = window.confirm("Delete this interview?");
    if (!ok) return;
    setLoading(true);
    try {
      await deleteInterview(id);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full px-4 py-8">
      <div className="max-w-5xl mx-auto flex items-center justify-between mb-6">
        <h1 className="text-2xl font-medium">Interviews</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={openCreate}
            className={`px-4 py-2 text-sm ${btnPrimary}`}
            disabled={loading}
          >
            New Interview
          </button>
        </div>
      </div>

      {error ? <div className="text-red-600 mb-4 text-sm">{error}</div> : null}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left">
              <th className="border-b border-(--border) py-3 px-2">id</th>
              <th className="border-b border-(--border) py-3 px-2">username</th>
              <th className="border-b border-(--border) py-3 px-2">code</th>
              <th className="border-b border-(--border) py-3 px-2">status</th>
              <th className="border-b border-(--border) py-3 px-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {interviews.map((i) => (
              <tr key={i.id} className="align-top">
                <td className="border-b border-(--border) py-3 px-2 text-sm">{i.id}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{i.username}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{i.code}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{i.status}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">
                  <div className="flex gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => openEdit(i)}
                      className={`px-2 py-1 text-sm ${btnSecondary}`}
                      disabled={loading}
                    >
                      edit
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteInterviewById(i.id)}
                      className={`px-2 py-1 text-sm ${btnSecondary}`}
                      disabled={loading}
                    >
                      delete
                    </button>
                    <button
                      type="button"
                      onClick={() => openView(i)}
                      className={`px-2 py-1 text-sm ${btnSecondary}`}
                      disabled={loading}
                    >
                      view content / discovery
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && interviews.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-sm">
                  No interviews yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {modalOpen ? (
        <Modal
          title={
            modalMode === "create"
              ? "Create interview"
              : modalMode === "edit"
                ? "Edit interview"
                : "Interview content / summary / discovery state"
          }
          maxWidthClassName={modalMode === "view" ? "max-w-5xl" : undefined}
          onClose={() => setModalOpen(false)}
          actions={
            modalMode === "view" ? (
              <div className="flex justify-end">
                <button
                  onClick={() => setModalOpen(false)}
                  className={`px-4 py-2 text-sm ${btnSecondary}`}
                  type="button"
                >
                  Close
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setModalOpen(false)}
                  className={`px-4 py-2 text-sm ${btnSecondary}`}
                  type="button"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={submitEditOrCreate}
                  className={`px-4 py-2 text-sm ${btnPrimary}`}
                  type="button"
                  disabled={loading || !canSaveInterview}
                >
                  {loading ? "Saving..." : "Save"}
                </button>
              </div>
            )
          }
        >
          {modalMode === "view" ? (
            detail ? (
              <>
                <div className="grid grid-cols-2 gap-4 text-left">
                  <div>
                    <div className="text-sm text-[--text]">username</div>
                    <div className="font-medium">{detail.username}</div>
                  </div>
                  <div>
                    <div className="text-sm text-[--text]">code</div>
                    <div className="font-medium">{detail.code}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-sm text-[--text]">status</div>
                    <div className="font-medium">{detail.status}</div>
                  </div>
                </div>

                <div className="text-left">
                  <div className="text-sm mb-1">content</div>
                  <textarea
                    className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-white"
                    value={detail.content}
                    readOnly
                  />
                </div>

                <div className="text-left">
                  <div className="text-sm mb-1">summary</div>
                  <textarea
                    className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-white"
                    value={detail.summary}
                    readOnly
                  />
                </div>

                <DiscoveryStateSection rawJson={detail.discovery_state_json} />
              </>
            ) : (
              <div>Loading details...</div>
            )
          ) : modalLoading ? (
            <div>Loading interview...</div>
          ) : (
            <>
              <div className="flex flex-col gap-4 text-left">
                <div className="flex flex-col gap-1">
                  <label className="text-sm">username</label>
                  <input
                    className="border border-(--border) rounded px-3 py-2 bg-white max-w-md"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <span className="text-sm">Access code (6 characters)</span>
                  <CodeInput6
                    value={code}
                    onChange={(next) => {
                      setCode(next);
                      setCodeError(null);
                    }}
                    disabled={loading}
                    aria-label="Interview access code"
                  />
                  {codeError ? (
                    <p className="text-sm text-red-600">{codeError}</p>
                  ) : null}
                </div>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-sm">status</label>
                <select
                  className="border border-(--border) rounded px-3 py-2 bg-white"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-sm">content</label>
                <textarea
                  className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-white"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-sm">summary</label>
                <textarea
                  className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-white"
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                />
              </div>
            </>
          )}
        </Modal>
      ) : null}
    </div>
  );
}

