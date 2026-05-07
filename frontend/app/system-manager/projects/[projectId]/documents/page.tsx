"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  deleteProjectDocument,
  getProjectDocuments,
  uploadProjectDocument,
  type ProjectDocumentRow,
} from "../../../../../lib/api";

export default function ProjectDocumentsPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.projectId);

  const [docs, setDocs] = useState<ProjectDocumentRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");

  const headerRight = useMemo(() => {
    return (
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => router.push(`/system-manager/projects/${projectId}/interviews`)}
          className="px-3 py-2 rounded border border-(--border) hover:opacity-90"
        >
          interviews
        </button>
        <button
          type="button"
          onClick={() => router.push("/system-manager/projects")}
          className="px-3 py-2 rounded border border-(--border) hover:opacity-90"
        >
          projects
        </button>
      </div>
    );
  }, [router, projectId]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const rows = await getProjectDocuments(projectId);
      setDocs(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!Number.isFinite(projectId)) return;
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function onUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      await uploadProjectDocument(projectId, { file, title });
      setFile(null);
      setTitle("");
      const input = document.getElementById("doc-file-input") as HTMLInputElement | null;
      if (input) input.value = "";
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(doc: ProjectDocumentRow) {
    const ok = window.confirm(
      `Delete “${doc.title}”? This will also delete its chunks from the vector database.`,
    );
    if (!ok) return;

    setLoading(true);
    setError(null);
    try {
      await deleteProjectDocument(doc.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full px-4 py-8">
      <div className="max-w-5xl mx-auto flex items-center justify-between mb-6">
        <h1 className="text-2xl font-medium">Documents</h1>
        {headerRight}
      </div>

      {error ? <div className="text-red-600 mb-4 text-sm">{error}</div> : null}

      <div className="max-w-5xl mx-auto rounded border border-(--border) bg-(--bg) p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <label className="text-sm">file (pdf/docx/txt/md)</label>
            <input
              id="doc-file-input"
              type="file"
              accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
              className="text-sm"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={loading}
            />
          </div>

          <div className="flex flex-col gap-1 flex-1 md:max-w-md">
            <label className="text-sm">title (optional)</label>
            <input
              className="border border-(--border) rounded px-3 py-2 bg-transparent"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={file?.name || "Untitled"}
              disabled={loading}
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onUpload}
              disabled={loading || !file}
              className="px-4 py-2 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Working..." : "Upload"}
            </button>
            <button
              type="button"
              onClick={refresh}
              disabled={loading}
              className="px-4 py-2 rounded border border-(--border) hover:opacity-90 disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto mt-6 overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left">
              <th className="border-b border-(--border) py-3 px-2">id</th>
              <th className="border-b border-(--border) py-3 px-2">title</th>
              <th className="border-b border-(--border) py-3 px-2">file</th>
              <th className="border-b border-(--border) py-3 px-2">status</th>
              <th className="border-b border-(--border) py-3 px-2">chunks</th>
              <th className="border-b border-(--border) py-3 px-2">created_at</th>
              <th className="border-b border-(--border) py-3 px-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className="align-top">
                <td className="border-b border-(--border) py-3 px-2 text-sm">{d.id}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{d.title}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{d.source_filename}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">
                  <div className="font-medium">{d.status}</div>
                  {d.error ? (
                    <div className="text-xs text-red-600 mt-1 max-w-xs wrap-break-word">
                      {d.error}
                    </div>
                  ) : null}
                </td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{d.chunk_count}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{d.created_at}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">
                  <button
                    type="button"
                    onClick={() => onDelete(d)}
                    disabled={loading}
                    className="px-2 py-1 border rounded hover:opacity-90 disabled:opacity-50"
                  >
                    delete
                  </button>
                </td>
              </tr>
            ))}
            {!loading && docs.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-sm">
                  No documents yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

