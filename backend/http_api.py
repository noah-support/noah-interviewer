import base64
import hashlib
import hmac
import json
import os
import secrets
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from livekit.api import AccessToken, VideoGrants

from database import db
from models import Interview, Project


SESSION_COOKIE_NAME = "session"


@contextmanager
def db_session():
    db.connect(reuse_if_open=True)
    try:
        yield
    finally:
        db.close()


def _cookie_secret() -> str:
    # For prototype simplicity we reuse LIVEKIT_API_SECRET if a dedicated cookie secret isn't provided.
    return os.getenv("SESSION_SECRET") or os.getenv("LIVEKIT_API_SECRET") or "dev-session-secret"


def sign_cookie(payload: Dict[str, Any]) -> str:
    secret = _cookie_secret().encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
    sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_cookie(cookie_value: str) -> Optional[Dict[str, Any]]:
    try:
        payload_b64, sig = cookie_value.split(".", 1)
    except ValueError:
        return None

    secret = _cookie_secret().encode("utf-8")
    expected_sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        return None

    # Add required '=' padding back for urlsafe_b64decode
    padding = "=" * (-len(payload_b64) % 4)
    payload_json = base64.urlsafe_b64decode(payload_b64 + padding)
    return json.loads(payload_json.decode("utf-8"))


def interview_to_me_shape(interview: Interview) -> Dict[str, Any]:
    project = interview.project
    return {
        "id": interview.id,
        "username": interview.username,
        "code": interview.code,
        "status": interview.status,
        "project": {
            "id": project.id,
            "title": project.title,
            "created_at": str(project.created_at),
        },
    }


class LoginRequest(BaseModel):
    username: str
    code: str


class CreateProjectRequest(BaseModel):
    title: str


class UpdateProjectRequest(BaseModel):
    title: str


class CreateInterviewRequest(BaseModel):
    username: str
    code: str
    status: Optional[str] = "Ready"


class UpdateInterviewRequest(BaseModel):
    username: Optional[str] = None
    code: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class EndInterviewRequest(BaseModel):
    room: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    title: str
    created_at: str


class InterviewResponse(BaseModel):
    id: int
    username: str
    code: str
    status: str
    created_at: str


def require_auth(request: Request) -> Interview:
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_cookie(cookie)
    if not payload or "interview_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid session")

    interview_id = payload["interview_id"]
    with db_session():
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            raise HTTPException(status_code=401, detail="Session expired")
        # Eagerly access `project` for /api/me and token endpoint room naming.
        _ = interview.project
        return interview


app = FastAPI()

# Dev defaults: allow both Vite and Next dev servers.
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/login")
def login(body: LoginRequest, response: Response):
    with db_session():
        interview = Interview.get_or_none((Interview.username == body.username) & (Interview.code == body.code))
        if not interview:
            raise HTTPException(status_code=401, detail="Wrong credentials")
        _ = interview.project

    session_value = sign_cookie({"interview_id": interview.id})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_value,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(interview: Interview = Depends(require_auth)):
    return interview_to_me_shape(interview)


@app.get("/api/projects", response_model=List[ProjectResponse])
def list_projects():
    with db_session():
        projects = list(Project.select().order_by(Project.id))
        return [
            ProjectResponse(id=p.id, title=p.title, created_at=str(p.created_at)) for p in projects
        ]


@app.post("/api/projects", response_model=ProjectResponse)
def create_project(body: CreateProjectRequest):
    with db_session():
        project = Project.create(
            title=body.title,
            graph="",
            namespace="",
        )
        return ProjectResponse(id=project.id, title=project.title, created_at=str(project.created_at))


@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: UpdateProjectRequest):
    with db_session():
        project = Project.get_or_none(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project.title = body.title
        project.save()
        return ProjectResponse(id=project.id, title=project.title, created_at=str(project.created_at))


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    with db_session():
        deleted = Project.delete().where(Project.id == project_id).execute()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"ok": True}


@app.get("/api/projects/{project_id}/interviews", response_model=List[InterviewResponse])
def list_interviews(project_id: int):
    with db_session():
        interviews = list(Interview.select().where(Interview.project == project_id).order_by(Interview.id))
        return [
            InterviewResponse(
                id=i.id,
                username=i.username,
                code=i.code,
                status=i.status,
                created_at=str(i.created_at),
            )
            for i in interviews
        ]


def validate_status(status: str) -> str:
    if status not in Interview.STATUS_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {list(Interview.STATUS_VALUES)}",
        )
    return status


@app.post("/api/projects/{project_id}/interviews", response_model=InterviewResponse)
def create_interview(project_id: int, body: CreateInterviewRequest):
    with db_session():
        project = Project.get_or_none(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        status = validate_status(body.status or "Ready")
        interview = Interview.create(
            project=project,
            username=body.username,
            code=body.code,
            status=status,
            content="",
            summary="",
        )
        return InterviewResponse(
            id=interview.id,
            username=interview.username,
            code=interview.code,
            status=interview.status,
            created_at=str(interview.created_at),
        )


@app.get("/api/interviews/{interview_id}")
def get_interview_detail(interview_id: int):
    with db_session():
        interview = (
            Interview.select()
            .where(Interview.id == interview_id)
            .join(Project)
            .switch(Interview)
            .first()
        )
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        _ = interview.project
        return {
            "id": interview.id,
            "username": interview.username,
            "code": interview.code,
            "status": interview.status,
            "content": interview.content,
            "summary": interview.summary,
            "created_at": str(interview.created_at),
            "project": {"id": interview.project.id, "title": interview.project.title},
        }


@app.put("/api/interviews/{interview_id}", response_model=InterviewResponse)
def update_interview(interview_id: int, body: UpdateInterviewRequest):
    with db_session():
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        if body.username is not None:
            interview.username = body.username
        if body.code is not None:
            interview.code = body.code
        if body.status is not None:
            interview.status = validate_status(body.status)
        if body.content is not None:
            interview.content = body.content
        if body.summary is not None:
            interview.summary = body.summary

        interview.save()
        return InterviewResponse(
            id=interview.id,
            username=interview.username,
            code=interview.code,
            status=interview.status,
            created_at=str(interview.created_at),
        )


@app.delete("/api/interviews/{interview_id}")
def delete_interview(interview_id: int):
    with db_session():
        deleted = Interview.delete().where(Interview.id == interview_id).execute()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Interview not found")
        return {"ok": True}


@app.post("/api/interviews/{interview_id}/livekit-token")
def livekit_token(interview_id: int, response: Response, authed: Interview = Depends(require_auth)):
    if authed.id != interview_id:
        raise HTTPException(status_code=403, detail="Cannot access other interview")

    with db_session():
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        # Room naming contract: include interview id + per-session suffix so
        # multiple concurrent sessions cannot overlap.
        room_name = f"interview-{interview.id}-{secrets.token_hex(4)}"
        identity = interview.username

        token_ttl = timedelta(minutes=60)
        token = (
            AccessToken()
            .with_identity(identity)
            .with_grants(VideoGrants(room=room_name, room_join=True))
            .with_ttl(token_ttl)
        )
        jwt = token.to_jwt()

        # Best-effort: if the interview is not ready yet, still allow join in prototype.
        return {"token": jwt, "room": room_name}


@app.post("/api/interviews/{interview_id}/end")
def end_interview(interview_id: int, body: EndInterviewRequest, authed: Interview = Depends(require_auth)):
    if authed.id != interview_id:
        raise HTTPException(status_code=403, detail="Cannot end other interview")

    with db_session():
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        interview.status = Interview.STATUS_DONE
        interview.save()

    # `body.room` is accepted for compatibility with older clients but unused.
    _ = body.room

    return {"ok": True}

