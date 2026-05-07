"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createProject,
  deleteProject,
  getProjects,
  updateProject,
  type ProjectRow,
} from "../../../lib/api";

function Modal(props: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  actions?: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={props.onClose} />
      <div className="relative w-full max-w-lg rounded border border-(--border) bg-(--bg) p-6">
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

export default function ProjectsPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editId, setEditId] = useState<number | null>(null);
  const [title, setTitle] = useState("");

  const headerRight = useMemo(() => {
    return (
      <button
        type="button"
        onClick={() => router.push("/home")}
        className="px-3 py-2 rounded border border-(--border) hover:opacity-90"
      >
        home
      </button>
    );
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const rows = await getProjects();
        if (!cancelled) setProjects(rows);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refresh() {
    setLoading(true);
    try {
      const rows = await getProjects();
      setProjects(rows);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setModalMode("create");
    setEditId(null);
    setTitle("");
    setModalOpen(true);
  }

  function openEdit(project: ProjectRow) {
    setModalMode("edit");
    setEditId(project.id);
    setTitle(project.title);
    setModalOpen(true);
  }

  async function submitProject() {
    if (!title.trim()) return;
    setLoading(true);
    try {
      if (modalMode === "create") {
        await createProject(title.trim());
      } else if (editId != null) {
        await updateProject(editId, title.trim());
      }
      setModalOpen(false);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function deleteProjectById(id: number) {
    const ok = window.confirm("Delete this project? This will delete its interviews.");
    if (!ok) return;
    setLoading(true);
    try {
      await deleteProject(id);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full px-4 py-8">
      <div className="max-w-5xl mx-auto flex items-center justify-between mb-6">
        <h1 className="text-2xl font-medium">Projects</h1>
        <div className="flex items-center gap-3">
          {headerRight}
          <button
            type="button"
            onClick={openCreate}
            className="px-4 py-2 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
            disabled={loading}
          >
            New Project
          </button>
        </div>
      </div>

      {error ? <div className="text-red-600 mb-4 text-sm">{error}</div> : null}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left">
              <th className="border-b border-(--border) py-3 px-2">id</th>
              <th className="border-b border-(--border) py-3 px-2">title</th>
              <th className="border-b border-(--border) py-3 px-2">namespace</th>
              <th className="border-b border-(--border) py-3 px-2">created_at</th>
              <th className="border-b border-(--border) py-3 px-2">actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id} className="align-top">
                <td className="border-b border-(--border) py-3 px-2 text-sm">{p.id}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{p.title}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm font-mono">
                  {p.namespace}
                </td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">{p.created_at}</td>
                <td className="border-b border-(--border) py-3 px-2 text-sm">
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => router.push(`/system-manager/projects/${p.id}/interviews`)}
                      className="px-2 py-1 border rounded hover:opacity-90"
                    >
                      view
                    </button>
                    <button
                      onClick={() => openEdit(p)}
                      className="px-2 py-1 border rounded hover:opacity-90"
                      disabled={loading}
                    >
                      edit
                    </button>
                    <button
                      onClick={() => deleteProjectById(p.id)}
                      className="px-2 py-1 border rounded hover:opacity-90"
                      disabled={loading}
                    >
                      delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && projects.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-sm">
                  No projects yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {modalOpen ? (
        <Modal
          title={modalMode === "create" ? "Create project" : "Edit project"}
          onClose={() => setModalOpen(false)}
          actions={
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 border rounded"
                type="button"
              >
                Cancel
              </button>
              <button
                onClick={submitProject}
                className="px-4 py-2 rounded bg-blue-600 text-white hover:opacity-90 disabled:opacity-50"
                type="button"
                disabled={loading}
              >
                {loading ? "Saving..." : "Save"}
              </button>
            </div>
          }
        >
          <div className="flex flex-col gap-1 text-left">
            <label className="text-sm">title</label>
            <input
              className="border border-(--border) rounded px-3 py-2 bg-transparent"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Default Project"
            />
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

