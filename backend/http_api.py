import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from livekit.api import AccessToken, VideoGrants

from database import db
from models import Interview, Project, ProjectDocument

from rag.ingest import ingest_document
import os

from pinecone import Pinecone  # type: ignore[import-not-found]


SESSION_COOKIE_NAME = "session"

_DISCOVERY_ROOM_NAME_RE = re.compile(r"^interview-\d+-[0-9a-f]{8}$")
_INTERVIEW_CODE_RE = re.compile(r"^[A-Za-z0-9]{6}$")


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

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _INTERVIEW_CODE_RE.match(v):
            raise ValueError("code must be exactly 6 alphanumeric characters")
        return v


class UpdateInterviewRequest(BaseModel):
    username: Optional[str] = None
    code: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None

    @field_validator("code")
    @classmethod
    def validate_code_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not _INTERVIEW_CODE_RE.match(v):
            raise ValueError("code must be exactly 6 alphanumeric characters")
        return v


class EndInterviewRequest(BaseModel):
    room: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    title: str
    namespace: str
    created_at: str


class InterviewResponse(BaseModel):
    id: int
    username: str
    code: str
    status: str
    created_at: str


class ProjectDocumentResponse(BaseModel):
    id: int
    project_id: int
    title: str
    source_filename: str
    source_mime: str
    status: str
    chunk_count: int
    error: Optional[str] = None
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


@app.on_event("startup")
def _ensure_project_namespaces_on_startup() -> None:
    """
    Ensure that starting the backend service results in Pinecone namespaces existing.
    """
    from seeder import ensure_seeded_if_empty

    ensure_seeded_if_empty()

    with db_session():
        projects = list(Project.select().order_by(Project.id))
        for p in projects:
            ns = (p.namespace or "").strip()
            if not ns:
                ns = f"project-{p.id}"
                p.namespace = ns
                p.save()
            try:
                api_key = os.getenv("PINECONE_API_KEY")
                if api_key:
                    index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
                    pc = Pinecone(api_key=api_key)
                    index = pc.Index(index_name)
                    index.upsert(
                        namespace=ns,
                        vectors=[
                            {
                                "id": "__namespace_init__",
                                "values": [0.0] * 1024,
                                "metadata": {
                                    "doc_id": 0,
                                    "chunk_id": 0,
                                    "source_filename": "__namespace__",
                                    "text": "",
                                },
                            }
                        ],
                    )
            except Exception as e:
                print(f"[SYSTEM] failed to touch pinecone namespace {ns!r}: {e}")


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


@app.get("/api/discovery-state/rooms")
def discovery_state_rooms():
    """List LiveKit room names that currently have discovery state in Redis (dev / ops)."""
    try:
        from bpmn_redis import list_discovery_state_room_names

        return {"rooms": list_discovery_state_room_names()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Redis unavailable: {e}")


@app.get("/api/discovery-state/snapshot")
def discovery_state_snapshot(room: str):
    """Latest parsed discovery JSON + buffer size for one room."""
    rn = room.strip()
    if not _DISCOVERY_ROOM_NAME_RE.match(rn):
        raise HTTPException(
            status_code=400,
            detail="Invalid room format (expected interview-<id>-<8 hex chars>)",
        )
    try:
        from bpmn_redis import buffer_length, get_state_raw
        from hobby_schema import parse_state_json
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        raw = get_state_raw(rn)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Redis unavailable: {e}")

    exists = bool(raw and raw.strip())
    buf_n = buffer_length(rn)
    if not exists:
        return {
            "room": rn,
            "exists": False,
            "state": None,
            "buffer_line_count": buf_n,
        }
    return {
        "room": rn,
        "exists": True,
        "state": parse_state_json(raw),
        "buffer_line_count": buf_n,
    }


@app.get("/api/projects", response_model=List[ProjectResponse])
def list_projects():
    with db_session():
        projects = list(Project.select().order_by(Project.id))
        return [
            ProjectResponse(
                id=p.id,
                title=p.title,
                namespace=(p.namespace or "").strip() or f"project-{p.id}",
                created_at=str(p.created_at),
            )
            for p in projects
        ]


@app.post("/api/projects", response_model=ProjectResponse)
def create_project(body: CreateProjectRequest):
    with db_session():
        project = Project.create(
            title=body.title,
            graph="",
            namespace="",
        )
        project.namespace = f"project-{project.id}"
        project.save()
        namespace = project.namespace

    # Ensure namespace exists immediately (best-effort).
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if api_key:
            index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
            pc = Pinecone(api_key=api_key)
            index = pc.Index(index_name)
            index.upsert(
                namespace=namespace,
                vectors=[
                    {
                        "id": "__namespace_init__",
                        "values": [0.0] * 1024,
                        "metadata": {
                            "doc_id": 0,
                            "chunk_id": 0,
                            "source_filename": "__namespace__",
                            "text": "",
                        },
                    }
                ],
            )
    except Exception as e:
        print(f"[SYSTEM] failed to touch pinecone namespace: {e}")

    with db_session():
        return ProjectResponse(
            id=project.id,
            title=project.title,
            namespace=project.namespace,
            created_at=str(project.created_at),
        )


@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: UpdateProjectRequest):
    with db_session():
        project = Project.get_or_none(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project.title = body.title
        project.save()
        return ProjectResponse(
            id=project.id,
            title=project.title,
            namespace=(project.namespace or "").strip() or f"project-{project.id}",
            created_at=str(project.created_at),
        )


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    with db_session():
        project = Project.get_or_none(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        namespace = (project.namespace or "").strip() or f"project-{project.id}"

    # Purge vectors best-effort; if it fails, don't delete the DB row.
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if api_key:
            index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
            pc = Pinecone(api_key=api_key)
            index = pc.Index(index_name)
            index.delete(namespace=namespace, delete_all=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to delete namespace vectors: {e}")

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
            discovery_state_json="",
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
            "discovery_state_json": interview.discovery_state_json or "",
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


@app.get(
    "/api/projects/{project_id}/documents",
    response_model=List[ProjectDocumentResponse],
)
def list_project_documents(project_id: int):
    with db_session():
        project = Project.get_or_none(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        docs = list(ProjectDocument.select().where(ProjectDocument.project == project).order_by(ProjectDocument.id))
        return [
            ProjectDocumentResponse(
                id=d.id,
                project_id=project.id,
                title=d.title,
                source_filename=d.source_filename,
                source_mime=d.source_mime,
                status=d.status,
                chunk_count=int(d.chunk_count or 0),
                error=d.error,
                created_at=str(d.created_at),
            )
            for d in docs
        ]


@app.post(
    "/api/projects/{project_id}/documents",
    response_model=ProjectDocumentResponse,
)
async def upload_project_document(
    project_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    with db_session():
        project = Project.get_or_none(Project.id == project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not (project.namespace or "").strip():
            project.namespace = f"project-{project.id}"
            project.save()

        doc = ProjectDocument.create(
            project=project,
            title=(title or file.filename or "Untitled").strip() or "Untitled",
            source_filename=(file.filename or "upload").strip() or "upload",
            source_mime=(file.content_type or "").strip(),
            status=ProjectDocument.STATUS_UPLOADED,
            chunk_count=0,
            error=None,
        )

    # Ingest outside db_session (embedding + pinecone are network calls).
    try:
        result = await asyncio.to_thread(
            ingest_document,
            namespace=project.namespace,
            doc_id=doc.id,
            filename=doc.source_filename,
            content_type=doc.source_mime,
            data=data,
        )
        with db_session():
            doc2 = ProjectDocument.get_by_id(doc.id)
            doc2.status = ProjectDocument.STATUS_INDEXED
            doc2.chunk_count = int(result.chunk_count)
            doc2.error = None
            doc2.save()
    except Exception as e:
        with db_session():
            doc2 = ProjectDocument.get_by_id(doc.id)
            doc2.status = ProjectDocument.STATUS_FAILED
            doc2.error = str(e)
            doc2.save()

    with db_session():
        final = ProjectDocument.get_by_id(doc.id)
        return ProjectDocumentResponse(
            id=final.id,
            project_id=final.project.id,
            title=final.title,
            source_filename=final.source_filename,
            source_mime=final.source_mime,
            status=final.status,
            chunk_count=int(final.chunk_count or 0),
            error=final.error,
            created_at=str(final.created_at),
        )


@app.delete("/api/documents/{document_id}")
def delete_project_document(document_id: int):
    with db_session():
        doc = ProjectDocument.get_or_none(ProjectDocument.id == document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        project = doc.project
        namespace = (project.namespace or "").strip()
        if not namespace:
            namespace = f"project-{project.id}"

    # Purge vectors best-effort; if it fails, don't delete the DB row.
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if api_key:
            index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
            pc = Pinecone(api_key=api_key)
            index = pc.Index(index_name)
            index.delete(namespace=namespace, filter={"doc_id": {"$eq": document_id}})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to delete vectors: {e}")

    with db_session():
        deleted = ProjectDocument.delete().where(ProjectDocument.id == document_id).execute()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Document not found")
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

    # Mark interview done immediately, then wait for the summarizer/save job to
    # persist content/summary. Frontend uses 200 OK as "saved" signal.
    deadline_s = time.monotonic() + float(os.getenv("END_INTERVIEW_WAIT_S", "30"))
    last_summary_error: str | None = None

    while True:
        with db_session():
            interview = Interview.get_or_none(Interview.id == interview_id)
            if not interview:
                raise HTTPException(status_code=404, detail="Interview not found")

            if interview.status != Interview.STATUS_DONE:
                interview.status = Interview.STATUS_DONE
                interview.save()

            content_ready = bool((interview.content or "").strip())
            summary_ready = bool((interview.summary or "").strip())

        if content_ready or summary_ready:
            break

        if time.monotonic() >= deadline_s:
            last_summary_error = "Timed out waiting for summarizer to persist content/summary"
            break

        time.sleep(0.5)

    if body.room:
        from bpmn_redis import delete_room_discovery_keys
        from discovery_persist import persist_discovery_state_to_db
        from state_tracker import flush_tracker_final

        room = body.room.strip()
        if not re.match(rf"^interview-{interview_id}-[0-9a-f]{{8}}$", room):
            raise HTTPException(status_code=400, detail="Invalid room for this interview")
        try:
            # Do not call ensure_default_state: if the agent already persisted and removed Redis
            # keys, we must not recreate empty state and overwrite the DB.
            flush_tracker_final(room_name=room)
            persist_discovery_state_to_db(interview_id=interview_id, room_name=room)
            delete_room_discovery_keys(room)
        except Exception as e:
            print(f"[SYSTEM] end_interview discovery persist failed: {e}")

    return {"ok": True, "summary_error": last_summary_error}

