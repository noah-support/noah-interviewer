# Deploying noah-interviewer on Northflank

This guide covers running the four application services (frontend, API, LiveKit agent, Celery) plus Postgres, Redis, and LiveKit in a production-like setup on [Northflank](https://northflank.com).

## Architecture

| Component | Image / source | Role |
|-----------|----------------|------|
| **frontend** | `frontend/Dockerfile` | Next.js UI (`:3000`) |
| **api** | `backend/Dockerfile` | FastAPI HTTP API (`:8000`) |
| **agent** | `backend/Dockerfile` | LiveKit voice worker (`python interviewer.py start`) |
| **celery** | `backend/Dockerfile` | Background summarization jobs |
| **postgres** | Northflank addon or `pgvector/pgvector:pg17` | App database |
| **redis** | Northflank addon or `redis:7-alpine` | Celery broker + discovery state |
| **livekit** | LiveKit Cloud (recommended) or `docker/livekit/Dockerfile` | WebRTC signaling + media |

All three Python services share one Docker image; only the **start command** differs.

```
                    ┌─────────────┐
   Browser ────────►│  frontend   │
                    └──────┬──────┘
                           │ NEXT_PUBLIC_API_URL
                           ▼
                    ┌─────────────┐     ┌──────────┐
                    │     api     │────►│ postgres │
                    └──────┬──────┘     └──────────┘
                           │
         LiveKit token     │                    ┌──────────┐
                           ▼                    │  redis   │
                    ┌─────────────┐◄───────────►└──────────┘
                    │   agent     │            ▲
                    └──────┬──────┘            │
                           │                   │
                    ┌──────┴──────┐     ┌──────┴──────┐
                    │  LiveKit    │     │   celery    │
                    │  (Cloud)    │     └─────────────┘
                    └─────────────┘
```

## Prerequisites

- Northflank project linked to this Git repository
- [Pinecone](https://www.pinecone.io/) index: **cosine**, **dimension 1024** (`text-embedding-3-large` with `dimensions=1024`), name e.g. `interviewer-docs`
- API keys: OpenAI, ElevenLabs, Groq (optional), Pinecone
- **LiveKit Cloud** project (recommended for production WebRTC) — or willingness to operate self-hosted LiveKit with UDP/TURN

Copy env templates locally:

```bash
cp backend/.env.example backend/.env.local
cp frontend/.env.example frontend/.env.local
```

## 1. Create Northflank addons

### Postgres

1. **Addons → Create addon → PostgreSQL**
2. Note the injected credentials (`HOST`, `PORT`, `USERNAME`, `PASSWORD`, `DATABASE`).
3. Map them to the app (secret group or per-service env):

| Addon key | App env var |
|-----------|-------------|
| `HOST` | `POSTGRES_HOST` |
| `PORT` | `POSTGRES_PORT` |
| `USERNAME` | `POSTGRES_USER` |
| `PASSWORD` | `POSTGRES_PASSWORD` |
| `DATABASE` | `POSTGRES_DB` |

Local `docker-compose.yml` uses pgvector; the app uses Peewee + Pinecone for vectors today, so standard Postgres on Northflank is fine.

### Redis

1. **Addons → Create addon → Redis**
2. Map `REDIS_MASTER_URL` (or TLS URL) → `REDIS_URL` on **api**, **agent**, and **celery**.

Example (non-TLS internal URL):

```text
REDIS_URL=redis://:password@redis-addon:6379/0
```

## 2. LiveKit

### Option A — LiveKit Cloud (recommended)

1. Create a project at [cloud.livekit.io](https://cloud.livekit.io).
2. Copy **URL**, **API key**, and **API secret** into a Northflank secret group:
   - `LIVEKIT_URL` — e.g. `wss://your-project.livekit.cloud`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
3. Set the frontend build/runtime variable:
   - `NEXT_PUBLIC_LIVEKIT_URL` — same WebSocket URL (`wss://...`)

No LiveKit container is required on Northflank.

### Option B — Self-hosted container

Build from `docker/livekit/Dockerfile`. Production requires a real config (keys, domains, TURN, UDP `7882`). The default `CMD ["--dev"]` is only suitable for local/staging. See [LiveKit server deployment](https://docs.livekit.io/home/self-hosting/deployment/).

WebRTC through a generic HTTP load balancer is often problematic; prefer LiveKit Cloud unless you have ops experience with TURN and UDP.

## 3. Build services

Create **four services** in the same Northflank project. Use **Build → Dockerfile** for each.

### Service: `api`

| Setting | Value |
|---------|--------|
| Build context | `/backend` |
| Dockerfile | `/backend/Dockerfile` |
| Port (public HTTP) | `8000` |
| Health check | `GET /health` on port `8000` |
| Start command | *(default)* `uvicorn main:app --host 0.0.0.0 --port 8000` |

### Service: `agent`

| Setting | Value |
|---------|--------|
| Build context | `/backend` |
| Dockerfile | `/backend/Dockerfile` |
| Public port | none (worker) |
| Start command | `python interviewer.py start` |
| Instances | `1` minimum; scale when load increases |

### Service: `celery`

| Setting | Value |
|---------|--------|
| Build context | `/backend` |
| Dockerfile | `/backend/Dockerfile` |
| Start command | `celery -A celery_app.celery_app worker -l info` |

### Service: `frontend`

| Setting | Value |
|---------|--------|
| Build context | `/frontend` |
| Dockerfile | `/frontend/Dockerfile` |
| Port | `3000` |
| Build arguments | see below |

**Frontend build arguments** (set at build time — they are baked into the client bundle):

| Build arg | Example |
|-----------|---------|
| `NEXT_PUBLIC_API_URL` | `https://api.your-domain.com` |
| `NEXT_PUBLIC_LIVEKIT_URL` | `wss://your-project.livekit.cloud` |
| `NEXT_PUBLIC_SHOW_SYSTEM_MANAGER` | `false` |

Assign a public Northflank domain to **frontend** and **api**.

## 4. Environment variables

Use one **secret group** linked to `api`, `agent`, and `celery`. Link Postgres/Redis addons as described above.

### Shared backend (api + agent + celery)

```text
# Postgres — from addon mapping
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=

REDIS_URL=

LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

OPENAI_API_KEY=
ELEVEN_API_KEY=
GROQ_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=interviewer-docs

SESSION_SECRET=<long-random-string>
CORS_ORIGINS=https://app.your-domain.com
CLEAN_DATABASE_ON_EXIT=false
```

**Important:** `CLEAN_DATABASE_ON_EXIT=false` prevents the agent from wiping the database when the worker restarts (local dev defaults to `true`).

Optional:

```text
API_LOG_LEVEL=info
CELERY_QUEUE=default
SUMMARY_AMOUNT=5
BPMN_REDIS_TTL_S=172800
```

### API only

```text
API_HOST=0.0.0.0
API_PORT=8000
```

### Do not mount `.env.local` in production

Containers load optional `ENV_FILE` (default `backend/.env.local`) only if the file exists. Northflank-injected variables take precedence. Never bake secrets into images.

## 5. CORS and cookies

Set `CORS_ORIGINS` to your frontend origin (comma-separated if multiple):

```text
CORS_ORIGINS=https://app.your-domain.com
```

Set `SESSION_SECRET` to a strong random value (do not rely on `LIVEKIT_API_SECRET` in production).

## 6. First deploy checklist

1. Addons running (Postgres, Redis).
2. All four services built and deployed.
3. `GET https://api.your-domain.com/health` returns `{"status":"ok"}`.
4. Agent logs show `STARTING WITH URL: wss://...` (correct LiveKit URL).
5. Celery worker logs show `ready`.
6. Open frontend → hub login (`user` / `ABC123` seeded when DB is empty).
7. Start an interview — room name `interview-<id>-<hex>` — agent joins the room.

### Seeding

On API startup, `ensure_seeded_if_empty()` creates a demo project and interview when the database has no rows. For a clean production DB, remove or change this in `http_api.py` / `seeder.py` before go-live.

To reset locally:

```bash
cd backend && python main.py   # runs reset_and_seed()
```

In production, use **System manager** or direct DB access instead.

## 7. Smoke test with Docker Compose (optional)

On a machine with Docker:

```bash
# Infra only (same as local dev)
docker compose up -d

# Full stack (requires backend/.env.local with keys)
docker compose -f docker-compose.prod.yml up --build
```

## 8. Scaling and ops notes

| Topic | Guidance |
|-------|----------|
| **Agent** | CPU-heavy (STT/LLM/TTS). Start with 1 instance; add replicas if LiveKit dispatch queues jobs. |
| **Celery** | Scale workers independently of the agent. |
| **API** | Stateless; scale horizontally behind Northflank load balancing. |
| **Redis TTL** | Discovery keys expire after `BPMN_REDIS_TTL_S` (default 48h). |
| **Pinecone** | One namespace per project: `project-<id>`. |
| **Logs** | Use Northflank log drains; agent prints `[SYSTEM]` lines for debugging. |

## 9. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Hub login fails | API unreachable, wrong `NEXT_PUBLIC_API_URL`, or CORS |
| No agent in room | Agent down, wrong `LIVEKIT_*` on agent vs Cloud project, or token mismatch |
| Summaries never update | Celery not running or `REDIS_URL` mismatch |
| DB empty after agent restart | `CLEAN_DATABASE_ON_EXIT` still `true` |
| CORS error in browser | `CORS_ORIGINS` missing frontend URL |
| `Missing OPENAI_API_KEY` in Celery | Secret group not attached to **celery** service |

## File reference

| Path | Purpose |
|------|---------|
| `backend/Dockerfile` | Python image (API, agent, Celery) |
| `frontend/Dockerfile` | Next.js standalone production image |
| `docker/livekit/Dockerfile` | Self-hosted LiveKit (dev/staging) |
| `docker-compose.yml` | Local Postgres + Redis |
| `docker-compose.prod.yml` | Optional all-in-one compose stack |
| `backend/.env.example` | Backend env template |
| `frontend/.env.example` | Frontend env template |

## Related docs

- Local development: [README.md](../README.md)
- LiveKit agents: [Agent deployment](https://docs.livekit.io/agents/deployment/)
- Northflank Dockerfile builds: [Build with a Dockerfile](https://northflank.com/docs/v1/application/build/build-with-a-dockerfile)
