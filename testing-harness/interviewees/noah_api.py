"""HTTP client for the Noah backend API (project / interview / LiveKit lifecycle)."""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any
import httpx

from interviewees.env import load_harness_env


@dataclass(frozen=True)
class LiveKitSession:
    interview_id: int
    token: str
    room: str
    username: str
    code: str


@dataclass(frozen=True)
class InterviewRecord:
    interview_id: int
    username: str
    code: str
    status: str
    content: str
    summary: str
    discovery_state: dict[str, Any] | None
    raw: dict[str, Any]


class NoahApiClient:
    """Cookie-authenticated client; create one instance per interview session."""

    def __init__(self, base_url: str | None = None) -> None:
        load_harness_env()
        url = (base_url or os.environ.get("NOAH_API_URL") or "http://localhost:8000").rstrip(
            "/"
        )
        self.base_url = url
        self._client = httpx.Client(base_url=url, timeout=120.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NoahApiClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def list_projects(self) -> list[dict[str, Any]]:
        r = self._client.get("/api/projects")
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise RuntimeError("Expected list from GET /api/projects")
        return data

    def find_or_create_project_by_title(self, title: str) -> int:
        """Return project id for an exact title match, creating the project if missing."""
        for project in self.list_projects():
            if str(project.get("title") or "") == title:
                return int(project["id"])
        created = self.create_project(title)
        return int(created["id"])

    def create_project(self, title: str) -> dict[str, Any]:
        r = self._client.post("/api/projects", json={"title": title})
        r.raise_for_status()
        return r.json()

    def create_interview(
        self,
        project_id: int,
        *,
        username: str,
        code: str | None = None,
    ) -> dict[str, Any]:
        access_code = code or secrets.token_hex(3).upper()
        r = self._client.post(
            f"/api/projects/{project_id}/interviews",
            json={"username": username, "code": access_code, "status": "Ready"},
        )
        r.raise_for_status()
        return r.json()

    def login(self, username: str, code: str) -> None:
        r = self._client.post("/api/login", json={"username": username, "code": code})
        r.raise_for_status()

    def start_livekit(self, interview_id: int, *, simulator: bool = True) -> LiveKitSession:
        params = {"simulator": "true"} if simulator else {}
        r = self._client.post(
            f"/api/interviews/{interview_id}/livekit-token",
            params=params,
        )
        r.raise_for_status()
        data = r.json()
        # Username/code from prior create; caller should track them.
        return LiveKitSession(
            interview_id=interview_id,
            token=data["token"],
            room=data["room"],
            username="",
            code="",
        )

    def end_interview(self, interview_id: int, room: str) -> dict[str, Any]:
        r = self._client.post(
            f"/api/interviews/{interview_id}/end",
            json={"room": room},
        )
        r.raise_for_status()
        return r.json()

    def get_interview(self, interview_id: int) -> InterviewRecord:
        r = self._client.get(f"/api/interviews/{interview_id}")
        r.raise_for_status()
        data = r.json()
        raw_state = data.get("discovery_state_json") or ""
        state: dict[str, Any] | None = None
        if raw_state.strip():
            try:
                state = json.loads(raw_state)
            except json.JSONDecodeError:
                state = {"_parse_error": True, "_raw": raw_state}
        return InterviewRecord(
            interview_id=int(data["id"]),
            username=str(data.get("username") or ""),
            code=str(data.get("code") or ""),
            status=str(data.get("status") or ""),
            content=str(data.get("content") or ""),
            summary=str(data.get("summary") or ""),
            discovery_state=state,
            raw=data,
        )

    def wait_for_persisted(
        self,
        interview_id: int,
        *,
        timeout_s: float = 60.0,
        poll_interval_s: float = 0.5,
    ) -> InterviewRecord:
        """Poll until content or summary is written (Celery summarizer), or timeout."""
        deadline = time.monotonic() + timeout_s
        last = self.get_interview(interview_id)
        while time.monotonic() < deadline:
            if (last.content or "").strip() or (last.summary or "").strip():
                return last
            time.sleep(poll_interval_s)
            last = self.get_interview(interview_id)
        return last

    def provision_livekit_session(
        self,
        project_id: int,
        *,
        username: str,
        code: str | None = None,
    ) -> LiveKitSession:
        """Create interview, login, and fetch LiveKit token + room (human-like flow)."""
        created = self.create_interview(project_id, username=username, code=code)
        interview_id = int(created["id"])
        uname = str(created["username"])
        access = str(created["code"])
        self.login(uname, access)
        lk = self.start_livekit(interview_id)
        return LiveKitSession(
            interview_id=interview_id,
            token=lk.token,
            room=lk.room,
            username=uname,
            code=access,
        )
