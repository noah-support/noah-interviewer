"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  createInterview,
  deleteInterview,
  getInterviews,
  getInterviewDetail,
  updateInterview,
  type InterviewDetail,
  type InterviewRow,
} from "../../../../../lib/api";

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
          <button onClick={props.onClose} className="px-2 py-1 border rounded">
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

export default function InterviewsPage() {
  const router = useRouter();
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

  const headerRight = useMemo(() => {
    return (
      <button
        type="button"
        onClick={() => router.push("/system-manager/projects")}
        className="px-3 py-2 rounded border border-(--border) hover:opacity-90"
      >
        projects
      </button>
    );
  }, [router]);

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
    setModalOpen(true);
    setModalLoading(true);
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
    if (!username.trim() || !code.trim()) return;
    setLoading(true);
    try {
      if (modalMode === "create") {
        await createInterview(projectId, {
          username: username.trim(),
          code: code.trim(),
          status,
        });
      } else if (modalMode === "edit" && modalInterviewId != null) {
        await updateInterview(modalInterviewId, {
          username: username.trim(),
          code: code.trim(),
          status,
          content,
          summary,
        });
      }
      setModalOpen(false);
      await refresh();
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
          {headerRight}
          <button
            type="button"
            onClick={openCreate}
            className="px-4 py-2 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
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
                      onClick={() => openEdit(i)}
                      className="px-2 py-1 border rounded hover:opacity-90"
                      disabled={loading}
                    >
                      edit
                    </button>
                    <button
                      onClick={() => deleteInterviewById(i.id)}
                      className="px-2 py-1 border rounded hover:opacity-90"
                      disabled={loading}
                    >
                      delete
                    </button>
                    <button
                      onClick={() => openView(i)}
                      className="px-2 py-1 border rounded hover:opacity-90"
                      disabled={loading}
                    >
                      view content/summary
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
                : "Interview content/summary"
          }
          onClose={() => setModalOpen(false)}
          actions={
            modalMode === "view" ? (
              <div className="flex justify-end">
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 border rounded"
                  type="button"
                >
                  Close
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 border rounded"
                  type="button"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={submitEditOrCreate}
                  className="px-4 py-2 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
                  type="button"
                  disabled={loading}
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
                    className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-transparent"
                    value={detail.content}
                    readOnly
                  />
                </div>

                <div className="text-left">
                  <div className="text-sm mb-1">summary</div>
                  <textarea
                    className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-transparent"
                    value={detail.summary}
                    readOnly
                  />
                </div>
              </>
            ) : (
              <div>Loading details...</div>
            )
          ) : modalLoading ? (
            <div>Loading interview...</div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 text-left">
                <div className="flex flex-col gap-1">
                  <label className="text-sm">username</label>
                  <input
                    className="border border-(--border) rounded px-3 py-2 bg-transparent"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm">code</label>
                  <input
                    className="border border-(--border) rounded px-3 py-2 bg-transparent"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-sm">status</label>
                <select
                  className="border border-(--border) rounded px-3 py-2 bg-transparent"
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
                  className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-transparent"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-sm">summary</label>
                <textarea
                  className="w-full min-h-32 border border-(--border) rounded px-3 py-2 bg-transparent"
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

