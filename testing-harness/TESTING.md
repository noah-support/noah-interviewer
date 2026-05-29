## Testing guide (interviewee harness)

This document explains how to run tests for **both interviewer transports**:

| Transport | Interviewer runs on | Harness connects via |
|-----------|---------------------|----------------------|
| **ElevenLabs** | ElevenLabs (hosted ConvAI, text/chat mode) | WebSocket ConvAI API |
| **LiveKit** | Noah agent worker (local, text streams) | `lk.chat` / `lk.transcription` |

All commands assume your working directory is `testing-harness/`.

### Runner commands (two modes)

The CLI has two subcommands (plus backward-compatible flags):

| Mode | Command | Use when |
|------|---------|----------|
| **Single interview** | `python runner.py interview …` or `python runner.py --persona … --interviewer …` | One persona, one session; writes a per-interview transcript under `transcripts/` |
| **Project test** | `python runner.py project --project … --interviewer …` | All personas in `personas/<project>/` run **sequentially**; **one aggregate JSON** under `results/` (LiveKit includes DB data; ElevenLabs harness transcripts only) |

**LiveKit project mode** (`--interviewer livekit`) mirrors a human using the web app:

1. Creates a **Project** in Postgres  
2. For each persona: creates an **Interview**, logs in, gets **token + room** from the API (no manual `LIVEKIT_ROOM` / `LIVEKIT_TOKEN`)  
3. Runs the AI interviewee over LiveKit  
4. Calls **`POST /api/interviews/{id}/end`** (state manager → DB, Celery summarizer)  
5. Collects **transcript**, **summary**, and **discovery state** from the DB into the aggregate file  

The database is **not** wiped after a LiveKit project test. Stopping `interviewer.py` also does **not** wipe Postgres unless you set `NOAH_CLEAN_DB_ON_AGENT_EXIT=1` in `backend/.env.local`.

**ElevenLabs project mode** (`--interviewer elevenlabs`) runs the same persona loop against your hosted ConvAI agent. No Noah API, LiveKit, or DB setup. Each persona gets a fresh ConvAI session; results land in one aggregate JSON with harness transcripts only.

```bash
python runner.py project \
  --project ComputerRepair_1 \
  --interviewer elevenlabs \
  --mode full \
  --verbose
```

Requires `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, and `ELEVENLABS_AGENT_ID` in `.env`. Persona YAMLs under `personas/ComputerRepair_1/`.

---

### Prerequisites

Use this checklist before each test type. **(local)** = process on your machine. **(hosted)** = external API credentials only.

#### Always (before any test)

- [ ] Python 3.11+ installed  
- [ ] Virtualenv: `testing-harness/.venv` activated  
- [ ] Package installed: `pip install -e ".[dev]"`  
- [ ] `testing-harness/.env` (copy from `config.example.env`)  

#### By test type

| Test | Command | What must be up |
|------|---------|-----------------|
| **Unit tests** (§1) | `pytest -q` | Venv only. No API keys. |
| **Persona prep** (§2) | `tools/prepare_personas.py` | `OPENAI_API_KEY`. Dataset JSON under `datasets/`. |
| **ElevenLabs E2E** (§3.1, §4.1) | `runner.py interview --interviewer elevenlabs` | `OPENAI_API_KEY`, ElevenLabs agent (chat mode), `ELEVENLABS_*`. Persona YAML. Sentinel on interviewer. |
| **LiveKit single E2E** (§3.2, §4.2) | `runner.py interview --interviewer livekit` | LiveKit server, text-mode agent worker, `LIVEKIT_URL` + auth. **Manual** `LIVEKIT_ROOM` (and optional token) **or** wire API yourself. |
| **LiveKit project test** (§5) | `runner.py project --project … --interviewer livekit` | Full Noah stack (below): API, Postgres, Redis, Celery, text-mode agent. **Auto** token/room. |
| **ElevenLabs project test** (§5) | `runner.py project --project … --interviewer elevenlabs` | `OPENAI_API_KEY`, ElevenLabs agent (chat mode), `ELEVENLABS_*`. Persona YAMLs for all subjects. No local stack. |

#### Full Noah stack (for LiveKit project mode)

Start from the **repo root** unless noted:

```bash
# 1) Data stores
docker compose up -d

# 2) API (terminal A)
cd backend && source .venv/bin/activate
python main.py

# 3) Celery — content + summary after each interview (terminal B)
cd backend && source .venv/bin/activate
celery -A celery_app.celery_app worker -l info

# 4) LiveKit interviewer agent — text mode required (terminal C)
cd backend && source .venv/bin/activate
python interviewer.py dev
```

Checklist:

- [ ] **Postgres** — `localhost:5434`  
- [ ] **Redis** — `localhost:6379`  
- [ ] **LiveKit server** — reachable at `LIVEKIT_URL` (e.g. `ws://localhost:7880`)  
- [ ] **`python main.py`** — `NOAH_API_URL` in harness `.env` (default `http://localhost:8000`)  
- [ ] **Celery worker** — without it, `db.content` / `db.summary` stay empty after `/end`  
- [ ] **`python interviewer.py dev`** in **text mode** (`RoomOptions`: `text_input=True`, `text_output=True`, `audio_input=False`, `audio_output=False`)  
- [ ] Interviewer emits `[[INTERVIEW_COMPLETE]]` on its own line when closing  
- [ ] **`NOAH_CLEAN_DB_ON_AGENT_EXIT`** unset or `0` in `backend/.env.local` (default: DB kept when agent stops)  

**Not required**

- Next.js frontend — human UI only  
- Manual `LIVEKIT_ROOM` / `LIVEKIT_TOKEN` in harness `.env` — **project mode sets these via API**  

#### ElevenLabs (hosted interviewer)

- [ ] Agent in **text/chat mode**  
- [ ] `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` in `.env`  
- [ ] `OPENAI_API_KEY` (interviewee LLM, separate from ElevenLabs’ internal model)  
- [ ] Sentinel `[[INTERVIEW_COMPLETE]]` in interviewer closing message  

#### LiveKit transport contract

- Interviewee → interviewer: topic **`lk.chat`**  
- Interviewer → interviewee: topic **`lk.transcription`** (attributes: `lk.segment_id`, `lk.transcription_final`)  
- Not a custom data-channel JSON protocol  

#### `.env` quick reference

| Variable | Unit | Persona prep | ElevenLabs | LiveKit single | LiveKit **project** |
|----------|:----:|:------------:|:----------:|:--------------:|:-------------------:|
| `OPENAI_API_KEY` | | ✓ | ✓ | ✓ | ✓ |
| `ELEVENLABS_API_KEY` | | | ✓ | | |
| `ELEVENLABS_AGENT_ID` | | | ✓ | | |
| `NOAH_API_URL` | | | | | ✓ |
| `LIVEKIT_URL` | | | | ✓ | ✓ |
| `LIVEKIT_API_KEY` + `LIVEKIT_API_SECRET` | | | | ✓* | ✓ |
| `LIVEKIT_ROOM` | | | | ✓* | — (auto) |
| `LIVEKIT_TOKEN` | | | | optional | — (auto) |
| `LIVEKIT_IDENTITY` | | | | optional | — (uses interview `username`, e.g. `S0`) |

\*Single LiveKit mode: room required unless you integrate the API yourself. Project mode mints token/room per interview via `NOAH_API_URL`.

Example `testing-harness/.env` for **project mode**:

```env
NOAH_API_URL=http://localhost:8000
OPENAI_API_KEY=...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
# LIVEKIT_ROOM and LIVEKIT_TOKEN intentionally empty
```

Align `LIVEKIT_*` with `backend/.env.local`.

---

### Sentinel (end-of-interview)

The interviewer must append this exact string on its **own line** at the end of its final message:

```text
[[INTERVIEW_COMPLETE]]
```

The harness strips it from stored transcripts, sends one brief closing reply, then disconnects.

---

### 0) One-time environment setup

```bash
cd testing-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
cp config.example.env .env
# Edit .env with your keys
```

---

### 1) Unit tests (fast)

```bash
pytest -q
```

Expected: `6 passed` (persona assembly + sentinel handling). No external services.

---

### 2) Persona preparation (dataset → YAML)

Requires `OPENAI_API_KEY` and Prosaview JSON, e.g. `datasets/ComputerRepair_1/S0_ComputerRepair_1.json`.

**Single file:**

```bash
python tools/prepare_personas.py \
  --input datasets/ComputerRepair_1/S0_ComputerRepair_1.json \
  --output-dir personas/ComputerRepair_1/ \
  --openai-model gpt-4o
```

**Batch:**

```bash
python tools/prepare_personas.py \
  --input-dir datasets/ComputerRepair_1/ \
  --output-dir personas/ComputerRepair_1/ \
  --openai-model gpt-4o
```

- Output: `personas/<project>/<subject>.yaml` (e.g. `S0.yaml`)  
- Skips existing files unless `--force`  
- Rejects knowledge text containing: `BPMN`, `gateway`, `node`, `flowchart`, `branch`, `task`  

---

### 3) Smoke tests (wiring)

| Setting | Value |
|---------|--------|
| Turn cap | **10** per interview |
| Per-interview transcripts | `transcripts/_smoke/` |
| Exit code | **0** if sentinel or turn cap; non-zero only on errors |

Flags: `--verbose` (log each turn on stderr), `--openai-model` (interviewee model).

#### 3.1 ElevenLabs smoke

```bash
python runner.py interview \
  --persona personas/ComputerRepair_1/S0.yaml \
  --interviewer elevenlabs \
  --mode smoke \
  --verbose
```

#### 3.2 LiveKit smoke (single interview, manual room)

Set `LIVEKIT_ROOM` (and token or key/secret) in `.env`, or use **project smoke** (§5) for automatic setup.

```bash
python runner.py interview \
  --persona personas/ComputerRepair_1/S0.yaml \
  --interviewer livekit \
  --mode smoke \
  --verbose
```

---

### 4) Full single-interview runs

| Setting | Value |
|---------|--------|
| Turn cap | **80** |
| Transcripts | `transcripts/<project>/` |

#### 4.1 ElevenLabs full

```bash
python runner.py interview \
  --persona personas/ComputerRepair_1/S0.yaml \
  --interviewer elevenlabs \
  --mode full
```

#### 4.2 LiveKit full (one persona, manual room)

For evaluating **all** interviewees with DB persistence, use **§5 project mode** instead.

```bash
python runner.py interview \
  --persona personas/ComputerRepair_1/S0.yaml \
  --interviewer livekit \
  --mode full
```

If `LIVEKIT_ROOM` / token were provisioned via API and you call `/end` from another tool, a single run can also persist to the DB when the livekit client is given a `LiveKitSession` (project mode does this automatically).

---

### 5) Project test — all interviewees sequentially (recommended for evaluation)

Runs every `personas/<project>/*.yaml` **in order** and writes **one combined results file** under `results/<project>__<interviewer>__<mode>__<timestamp>.json`.

Choose the interviewer with `--interviewer livekit` or `--interviewer elevenlabs`.

#### 5a) ElevenLabs project test

No DB or LiveKit required. Only the project name (and personas on disk) are needed.

```bash
python runner.py project \
  --project ComputerRepair_1 \
  --interviewer elevenlabs \
  --mode full \
  --verbose
```

Smoke:

```bash
python runner.py project \
  --project ComputerRepair_1 \
  --interviewer elevenlabs \
  --mode smoke \
  --verbose
```

Each `interviews[]` entry contains `harness_transcript` and `harness_transcript_path` (no `db` block).

#### 5b) LiveKit project test

Runs every `personas/<project>/*.yaml` **in order**, with full Noah DB lifecycle.

**Flow per persona**

1. `POST /api/projects` — create harness project (once)  
2. `POST /api/projects/{id}/interviews` — create interview (`username` = subject label, e.g. `S0`)  
3. `POST /api/login` — session cookie  
4. `POST /api/interviews/{id}/livekit-token` — **token + room** (`interview-{id}-{8 hex}`)  
5. Harness joins room as that user, runs interviewee over `lk.chat` / `lk.transcription`  
6. `POST /api/interviews/{id}/end` with `room` — flush state tracker, persist discovery JSON, enqueue summary  
7. Poll DB until `content` or `summary` is present (Celery)  
8. Append to aggregate JSON  

**Run**

```bash
python runner.py project \
  --project ComputerRepair_1 \
  --interviewer livekit \
  --mode full \
  --verbose
```

**Smoke (10 turns per interviewee)**

```bash
python runner.py project \
  --project ComputerRepair_1 \
  --interviewer livekit \
  --mode smoke \
  --verbose
```

**Extra flags**

| Flag | Default | Purpose |
|------|---------|---------|
| `--personas-dir` | `personas/<project>/` | Override persona YAML directory |
| `--api-url` | `NOAH_API_URL` from `.env` | Noah API base URL |
| `--persist-wait-timeout` | `60` | Seconds to wait for Celery after `/end` |
| `--project-title` | `Harness <project> <timestamp>` | Custom DB project title |
| `--transcript-dir` | (default layout) | Override per-interview transcript folder |
| `--openai-model` | `gpt-4o` | Interviewee LLM |

**Output**

- Printed path, e.g. `results/ComputerRepair_1__elevenlabs__full__20260528T120000Z.json` or `results/ComputerRepair_1__livekit__full__....json`  
- Per-interview harness transcripts still written under `transcripts/` (or `--transcript-dir`)  

**Aggregate file shape (abbreviated)**

```json
{
  "schema_version": "1.0",
  "project_name": "ComputerRepair_1",
  "project_id": 42,
  "project_title": "Harness ComputerRepair_1 2026-05-28T10:00:00Z",
  "mode": "full",
  "interviewer": "livekit",
  "started_at": "...",
  "ended_at": "...",
  "interview_count": 3,
  "interviews": [
    {
      "persona_id": "ComputerRepair_1__S0",
      "subject_label": "S0",
      "interview_id": 101,
      "username": "S0",
      "code": "A1B2C3",
      "room": "interview-101-deadbeef",
      "harness_transcript_path": "transcripts/ComputerRepair_1/S0__livekit__....json",
      "harness_transcript": { "turns": [], "ended_by": "sentinel" },
      "ended_by": "sentinel",
      "db": {
        "status": "done",
        "content": { "items": [ { "role": "user", "content": "..." } ] },
        "summary": "...",
        "discovery_state": { "meta": {}, "discovery": {}, "process_details": {} }
      }
    }
  ]
}
```

**Backward-compatible single run**

```bash
python runner.py --persona personas/ComputerRepair_1/S0.yaml --interviewer livekit --mode full
```

---

### 6) What success looks like

#### Single interview (`runner.py interview`)

- stdout: path to `transcripts/.../__<interviewer>__<timestamp>.json`  
- No `[[INTERVIEW_COMPLETE]]` in stored interviewer turns  
- `ended_by`: `sentinel` or `turn_cap`  
- Schema: `schema_version`, `persona_id`, `project`, `subject_label`, `interviewer`, timestamps, `turns[]`  

#### Project test (`runner.py project`)

- stdout: path to `results/<project>__<interviewer>__<mode>__<timestamp>.json`  
- One `interviews[]` entry per persona YAML (all subjects run sequentially)  
- **ElevenLabs:** each entry has `harness_transcript` (+ path under `transcripts/`)  
- **LiveKit:** each entry also has `db.content`, `db.summary`, `db.discovery_state` when Celery and agent completed successfully; Postgres rows remain  

#### Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `LIVEKIT_ROOM is not set` (single mode) | Set room in `.env` or use `runner.py project` |
| No interviewer messages in room | Agent not in text mode or not publishing to `lk.transcription` |
| `db.content` / `db.summary` null in aggregate | Celery worker not running or `/end` not reached |
| Empty discovery state | State tracker not flushed; check Redis and `/end` with correct `room` |
| Postgres empty after stopping agent | `NOAH_CLEAN_DB_ON_AGENT_EXIT=1` — remove or set to `0` |
| `NOAH_API_URL` connection refused | Start `python main.py` |

---

### 7) Transport reference (short)

**ElevenLabs:** Harness sends interviewee text as ConvAI `user_message`; receives interviewer via `callback_agent_response`. Chat/text-only mode required.

**LiveKit:** Harness uses the same token API as the frontend (`livekit-token` → join → converse → `end`). Identity matches interview `username` so the agent loads the correct DB row.
