# noah-interviewer
A custom conversational voice agent that is optimized for process discovery using spoken interviews

## Local development

### 1) Start Postgres + Redis

```bash
docker compose up -d
```

This starts:
- Postgres on `localhost:5434` (matches `backend/database.py`)
- Redis on `localhost:6379` (Celery broker/result backend)

### 2) Backend API (`main.py`)

[`backend/main.py`](backend/main.py) only runs the **FastAPI** app (tokens, interviews, RAG admin, discovery-state endpoints). Running `python main.py` also calls **`reset_and_seed()`** (full drop + demo data). On every API process startup (including **`uvicorn main:app`**), **`ensure_seeded_if_empty()`** runs so if the database has **no interviews**—for example after the LiveKit agent exits and runs **`clean_database()`**—the demo project and interview (`user` / `ABC123`) are created again without needing `python main.py`.

In one terminal:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The API listens on `API_HOST` / `API_PORT` (defaults `0.0.0.0:8000`).

Hub sign-in (seeded interview): username **`user`**, access code **`ABC123`** (six characters; avoids mixing up the letter O with the digit 0). If you still have an older database row with code `DEMO01`, either sign in with **D-E-M-*O*-0-1** (capital **O**) or change the code in System manager → Interviews.

### 3) LiveKit agent (`interviewer.py`)

[`backend/interviewer.py`](backend/interviewer.py) runs the **LiveKit voice worker** (Noah). Start it after the API is up and Redis/Postgres are running.

In another terminal:

```bash
cd backend
source .venv/bin/activate
python interviewer.py dev
```

Stopping the agent runs `clean_database()` (dev helper that clears rows—same behavior as before when the combined process exited).

Required env (loaded from `backend/.env.local` for both processes):
- `OPENAI_API_KEY` (LLM + embeddings)
- LiveKit credentials/URL (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`)
- **Pinecone (RAG)**:
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX_NAME=interviewer-docs` (defaults to `interviewer-docs`)

Notes:
- The Pinecone index must be configured for **cosine** with **dimension 1024** (matches `text-embedding-3-large` with `dimensions=1024`).
- Each project uses its own Pinecone **namespace**: `project-<project_id>` (created automatically when you create a project).

### 4) Celery worker (summarization jobs)

In another terminal:

```bash
cd backend
source .venv/bin/activate
export REDIS_URL="redis://localhost:6379/0"
celery -A celery_app.celery_app worker -l info
```

### Optional) Watch the discovery state manager (Redis)

While an interview is active, you can open **another terminal** and stream the latest JSON the state manager keeps in Redis (`lk:bpmn:state:<room>`). Use the exact **`room`** string returned when you start the session (for example from `POST /api/interviews/{id}/livekit-token`; it looks like `interview-<id>-<8 hex chars>`).

**Or** use the app: open **`/system-manager/discovery-state`** (from **Projects**, use **discovery state** in the header). Pick a room from the dropdown (active sessions with keys in Redis) or type the room name and click **Follow**; the JSON refreshes automatically. When an interview ends, Redis keys for that room are removed so the list only shows **live** sessions. The last discovery JSON is stored on the interview row and is visible under **view content/summary** in the system manager (discovery state section).

CLI alternative:

```bash
cd backend
source .venv/bin/activate
python watch_discovery_state.py --room interview-1-a1b2c3d4
```

- Poll interval: `--interval 0.5` (seconds; default `0.5`).
- Append-only log when the JSON changes: `--no-clear`.
- Also show transcript buffer size: `--show-buffer`.

Uses `REDIS_URL` from `backend/.env.local` (same as the agent and Celery). **Ctrl+C** to stop.

### 5) Frontend (Next.js)

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Env:
- `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
- `NEXT_PUBLIC_LIVEKIT_URL` must be set (used by `/home`)
