const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      // ignore
    }
    throw new Error(
      `API ${res.status} ${res.statusText}${detail ? `: ${JSON.stringify(detail)}` : ""}`,
    );
  }

  return (await res.json()) as T;
}

export type MeResponse = {
  id: number;
  username: string;
  code: string;
  status: string;
  project: { id: number; title: string; created_at: string };
};

export type ProjectRow = {
  id: number;
  title: string;
  namespace: string;
  created_at: string;
};

export type InterviewRow = {
  id: number;
  username: string;
  code: string;
  status: string;
  created_at: string;
};

export type InterviewDetail = InterviewRow & {
  content: string;
  summary: string;
  discovery_state_json?: string;
  project: { id: number; title: string };
};

export type ProjectDocumentRow = {
  id: number;
  project_id: number;
  title: string;
  source_filename: string;
  source_mime: string;
  status: string;
  chunk_count: number;
  error?: string | null;
  created_at: string;
};

export async function login(username: string, code: string) {
  return apiFetch<{ ok: boolean }>("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, code }),
  });
}

export async function me(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/me", { method: "GET" });
}

export async function getProjects(): Promise<ProjectRow[]> {
  return apiFetch<ProjectRow[]>("/api/projects", { method: "GET" });
}

export async function createProject(title: string): Promise<ProjectRow> {
  return apiFetch<ProjectRow>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function updateProject(
  projectId: number,
  title: string,
): Promise<ProjectRow> {
  return apiFetch<ProjectRow>(`/api/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify({ title }),
  });
}

export async function deleteProject(projectId: number): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/projects/${projectId}`, { method: "DELETE" });
}

export async function getInterviews(projectId: number): Promise<InterviewRow[]> {
  return apiFetch<InterviewRow[]>(
    `/api/projects/${projectId}/interviews`,
    { method: "GET" },
  );
}

export async function createInterview(
  projectId: number,
  payload: { username: string; code: string; status?: string },
): Promise<InterviewRow> {
  return apiFetch<InterviewRow>(`/api/projects/${projectId}/interviews`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateInterview(
  interviewId: number,
  payload: {
    username?: string;
    code?: string;
    status?: string;
    content?: string;
    summary?: string;
  },
): Promise<InterviewRow> {
  return apiFetch<InterviewRow>(`/api/interviews/${interviewId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteInterview(
  interviewId: number,
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/interviews/${interviewId}`, {
    method: "DELETE",
  });
}

export async function getInterviewDetail(
  interviewId: number,
): Promise<InterviewDetail> {
  return apiFetch<InterviewDetail>(`/api/interviews/${interviewId}`, { method: "GET" });
}

export async function startInterview(interviewId: number): Promise<{
  token: string;
  room: string;
}> {
  return apiFetch<{ token: string; room: string }>(
    `/api/interviews/${interviewId}/livekit-token`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export async function endInterview(
  interviewId: number,
  payload: { room?: string },
): Promise<{ ok: boolean; summary_error?: string | null }> {
  return apiFetch<{ ok: boolean; summary_error?: string | null }>(
    `/api/interviews/${interviewId}/end`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export type DiscoveryRoomsResponse = {
  rooms: string[];
};

export type DiscoverySnapshotResponse = {
  room: string;
  exists: boolean;
  state: unknown | null;
  buffer_line_count: number;
};

export async function getDiscoveryStateRooms(): Promise<DiscoveryRoomsResponse> {
  return apiFetch<DiscoveryRoomsResponse>("/api/discovery-state/rooms", {
    method: "GET",
  });
}

export async function getDiscoverySnapshot(
  room: string,
): Promise<DiscoverySnapshotResponse> {
  const q = new URLSearchParams({ room: room.trim() });
  return apiFetch<DiscoverySnapshotResponse>(
    `/api/discovery-state/snapshot?${q.toString()}`,
    { method: "GET" },
  );
}

export async function logout(): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/logout`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getProjectDocuments(
  projectId: number,
): Promise<ProjectDocumentRow[]> {
  return apiFetch<ProjectDocumentRow[]>(`/api/projects/${projectId}/documents`, {
    method: "GET",
  });
}

export async function uploadProjectDocument(
  projectId: number,
  payload: { file: File; title?: string },
): Promise<ProjectDocumentRow> {
  const fd = new FormData();
  fd.append("file", payload.file);
  if (payload.title != null && payload.title.trim()) {
    fd.append("title", payload.title.trim());
  }

  const res = await fetch(`${API_BASE}/api/projects/${projectId}/documents`, {
    method: "POST",
    credentials: "include",
    body: fd,
  });

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      // ignore
    }
    throw new Error(
      `API ${res.status} ${res.statusText}${detail ? `: ${JSON.stringify(detail)}` : ""}`,
    );
  }

  return (await res.json()) as ProjectDocumentRow;
}

export async function deleteProjectDocument(
  documentId: number,
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/documents/${documentId}`, {
    method: "DELETE",
  });
}

