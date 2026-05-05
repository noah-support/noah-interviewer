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

### 2) Backend (API + LiveKit agent)

In one terminal:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py dev
```

Required env (loaded from `backend/.env.local`): at minimum `OPENAI_API_KEY` and your LiveKit credentials/URL.

### 3) Celery worker (summarization jobs)

In a second terminal:

```bash
cd backend
source .venv/bin/activate
export REDIS_URL="redis://localhost:6379/0"
celery -A celery_app.celery_app worker -l info
```

### 4) Frontend (Next.js)

In a third terminal:

```bash
cd frontend
npm install
npm run dev
```

Env:
- `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
- `NEXT_PUBLIC_LIVEKIT_URL` must be set (used by `/home`)

