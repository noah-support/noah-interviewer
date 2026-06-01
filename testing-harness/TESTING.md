# Testing harness guide

This document covers setup and commands for the **interviewee testing harness** in `testing-harness/`. All shell examples assume:

```bash
cd testing-harness
source .venv/bin/activate   # after creating the venv once
```

The harness drives an AI **interviewee** against a real **interviewer** (Noah over LiveKit, or a hosted ElevenLabs ConvAI agent). Personas live under `personas/A/`, `personas/B/`, etc., with one prepared prompt file per folder.

---

## Prerequisites

### Install the harness

```bash
cd testing-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
cp config.example.env .env
```

Fill in `testing-harness/.env` (see [Environment variables](#environment-variables)).

### Persona layout on disk

```
personas/
├── A/
│   ├── process1.json
│   ├── process2.json
│   └── prompt.yaml          ← created by prep (required before batch runs)
├── B/
│   ├── process3.json
│   └── prompt.yaml
├── C/
│   └── ...
├── D/
│   └── ...
└── devide.txt               ← maps processN → dataset folder names
```

Each `process*.json` is either Prosaview **fragments** JSON or a stub that prep resolves from `datasets/ProsaviewDataSets-main/`.

### Interviewer: end-of-interview sentinel

The interviewer must end its final message with this exact string (on its own or embedded in text):

`[[INTERVIEW_COMPLETE]]`

The harness strips it from stored turns, sends one closing reply, then disconnects.

### What you need by interviewer

| Interviewer | CLI value | What must be running |
|-------------|-----------|----------------------|
| **Noah** (local LiveKit + Noah agent) | `noah` | Full Noah stack (below) + prepared `personas/*/prompt.yaml` |
| **ElevenLabs** (hosted ConvAI) | `elevenlabs` | ElevenLabs agent in **text/chat** mode + prepared `prompt.yaml` files only |

#### Noah stack (for `--interviewer noah`)

From the **repo root**:

```bash
# 1) Postgres + Redis
docker compose up -d

# 2) API
cd backend && source .venv/bin/activate && python main.py

# 3) Celery (transcript + summary after each interview)
cd backend && celery -A celery_app.celery_app worker -l info

# 4) LiveKit interviewer agent (text streams for harness; voice optional for UI)
cd backend && python interviewer.py dev
```

For harness-only runs (no microphone), set in `backend/.env.local`:

```env
NOAH_INTERVIEWER_TEXT_ONLY=1
```

This disables STT/TTS and uses `lk.chat` / `lk.transcription` only. The state manager runs on every harness text turn (see below).

Checklist:

- [ ] Postgres reachable (default `localhost:5434`)
- [ ] Redis reachable (`localhost:6379`)
- [ ] `NOAH_API_URL` in harness `.env` (default `http://localhost:8000`)
- [ ] `LIVEKIT_URL` matches backend LiveKit config
- [ ] Celery worker running (otherwise DB `content` / `summary` stay empty after `/end`)
- [ ] Interviewer agent restarted after code changes (state manager hooks `lk.chat` text input)
- [ ] For harness: `NOAH_INTERVIEWER_TEXT_ONLY=1` in `backend/.env.local` (recommended) or voice agent with custom text callback
- [ ] RAG is **off** automatically for project `output-test-noah` (and any `output-test*` title); optional `NOAH_DISABLE_RAG=1` in `backend/.env.local` for other rooms
- [ ] Interviewer emits `[[INTERVIEW_COMPLETE]]` when closing

You do **not** need the Next.js frontend for harness runs. Batch Noah mode provisions LiveKit token and room via the API (no manual `LIVEKIT_ROOM`).

#### ElevenLabs (for `--interviewer elevenlabs`)

- [ ] Agent configured for **text/chat** (not voice-only). Harness forces `text_only` and sends an opening user message if the agent is silent for 8s (avoids the 60s timeout).
- [ ] `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID` in `.env`
- [ ] Hosted agent dynamic vars: harness sends `name` (and `role`, `company`, `department`) from each persona’s `identity` block; add more via `ELEVENLABS_DYNAMIC_VARIABLES_JSON` if your agent requires other keys
- [ ] `OPENAI_API_KEY` for the **interviewee** LLM (separate from ElevenLabs’ model)
- [ ] Sentinel on the hosted agent’s closing message

No Noah API, Postgres, LiveKit, or Celery required for ElevenLabs batch runs.

### Environment variables

| Variable | Noah | ElevenLabs | Persona prep |
|----------|:----:|:----------:|:------------:|
| `OPENAI_API_KEY` | Interviewee LLM | Interviewee LLM | Required |
| `NOAH_API_URL` | Yes | — | — |
| `LIVEKIT_URL` | Yes | — | — |
| `LIVEKIT_API_KEY` + `LIVEKIT_API_SECRET` | Yes (batch auto-token) | — | — |
| `ELEVENLABS_API_KEY` | — | Yes | — |
| `ELEVENLABS_AGENT_ID` | — | Yes | — |

Example `testing-harness/.env`:

```env
NOAH_API_URL=http://localhost:8000
OPENAI_API_KEY=sk-...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
```

Align `LIVEKIT_*` with `backend/.env.local`.

---

## How to run the persona prep script

Prep merges every `process*.json` in each folder under `personas/` and writes **one** `prompt.yaml` per folder. The batch test runner loads that file automatically.

```bash
python tools/prepare_personas.py batch
```

Defaults:

- `--personas-root` → `testing-harness/personas/`
- `--datasets-root` → `datasets/ProsaviewDataSets-main/` (used when a `process*.json` is not already fragments JSON)

Options:

| Flag | Purpose |
|------|---------|
| `--force` | Overwrite existing `prompt.yaml` files |
| `--openai-model` | Model for knowledge generation (default `gpt-4o`) |
| `--personas-root PATH` | Alternate personas root |
| `--datasets-root PATH` | Alternate Prosaview datasets tree |

After a successful run you should have:

- `personas/A/prompt.yaml`
- `personas/B/prompt.yaml`
- `personas/C/prompt.yaml`
- `personas/D/prompt.yaml`

The tool rejects persona text containing modeling jargon (`BPMN`, `gateway`, `node`, etc.) and retries once. Process-to-dataset names follow `personas/devide.txt` (e.g. `process1` → `caseHandling_1`).

**Legacy mode** (single Prosaview subject file, not used for output-test batch):

```bash
python tools/prepare_personas.py \
  --input datasets/ProsaviewDataSets-main/ComputerRepair_1/S0_ComputerRepair_1.json \
  --output-dir personas/legacy/
```

---

## How to run testing scripts

Unit tests validate persona loading, sentinel handling, folder discovery, and fragment resolution **without** external services.

```bash
pytest -q
```

Run a single file or test:

```bash
pytest tests/test_discover_personas.py -v
pytest tests/test_end_signal.py -v
```

Expected: all tests pass with only the venv and package installed (no API keys required for unit tests).

---

## How to run the testing harness for one persona

Use the `interview` subcommand with a prepared `prompt.yaml` and either interviewer.

**Noah (full turn cap 80):**

```bash
python3 runner.py interview \
  --persona personas/A/prompt.yaml \
  --interviewer noah \
  --mode full
```

**ElevenLabs:**

```bash
python3 runner.py interview \
  --persona personas/A/prompt.yaml \
  --interviewer elevenlabs \
  --mode full
```

**Smoke run** (10-turn cap, transcripts under `transcripts/_smoke/`):

```bash
python3 runner.py interview \
  --persona personas/A/prompt.yaml \
  --interviewer noah \
  --mode smoke
```

Useful options:

| Flag | Description |
|------|-------------|
| `--verbose` | Print each turn on stderr |
| `--transcript-dir PATH` | Override harness transcript output directory |
| `--openai-model` | Interviewee model (default `gpt-4o`) |

On success, stdout prints the path to a harness transcript JSON, e.g. `transcripts/output-test/A__livekit__20260531T120000Z.json`.

For **Noah** single runs, if `LIVEKIT_ROOM` is **not** set in `.env`, the harness provisions token and room via the Noah API (same as batch mode: project `output-test-noah`, interview username from `subject_label`). Ensure `python main.py` and the LiveKit agent are running. Optional: set `LIVEKIT_ROOM` manually to skip API provisioning.

---

## How to run the testing harness for a complete batch (by interviewer)

Batch mode runs **every persona folder** under `personas/` in order (`A` → `B` → `C` → `D`), loading each folder’s `prompt.yaml`. A progress bar shows the current persona.

Both commands require `--interviewer` and `--output-dir`.

### Noah (local interviewer + DB + JSON export)

```bash
python3 runner.py --interviewer noah --output-dir ./out
```

What it does:

1. Finds or creates Postgres project **`output-test-noah`**
2. For each persona folder: creates an interview, provisions LiveKit token/room, runs the interviewee
3. Calls `POST /api/interviews/{id}/end` and waits for Celery to fill `content`, `summary`, `discovery_state_json`
4. Writes **`./out/output-test-noah_{timestamp}.json`**

Export shape (one key per persona folder):

```json
{
  "A": {
    "content": { "items": [ { "role": "user", "content": "..." } ] },
    "discovery_state_json": { },
    "summary": "..."
  },
  "B": { }
}
```

Field names match the database: `content` (transcript), `discovery_state_json` (state manager), `summary`.

Extra options:

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `full` | `smoke` = 10 turns per interview |
| `--api-url` | `NOAH_API_URL` from `.env` | Noah API base URL |
| `--persist-wait-timeout` | `60` | Seconds to wait for DB after `/end` |
| `--personas-root` | `personas/` | Alternate personas tree |
| `--verbose` | off | Log turns |

Completion message example: `Ran 4 interviews (noah). Wrote ./out/output-test-noah_20260531T120000Z.json`

### ElevenLabs (hosted interviewer, no DB)

```bash
python3 runner.py --interviewer elevenlabs --output-dir ./out
```

What it does:

1. Runs each persona against your ElevenLabs ConvAI agent (fresh session per persona)
2. Writes harness transcripts under `transcripts/` (unless `--transcript-dir` is set)
3. Does **not** use Postgres or write the combined JSON file (`--output-dir` is required for CLI symmetry only)

Completion message example: `Ran 4 interviews (elevenlabs). No DB or JSON export.`

Same optional flags as Noah (`--mode`, `--verbose`, `--personas-root`, etc.) except Noah-only flags (`--api-url`, `--persist-wait-timeout`) apply only to `noah`.

### Typical evaluation workflow

```bash
# 1) Generate prompt files (once, or after changing process JSON)
python tools/prepare_personas.py batch

# 2a) Full Noah output test
python3 runner.py --interviewer noah --output-dir ./results/noah

# 2b) ElevenLabs comparison run
python3 runner.py --interviewer elevenlabs --output-dir ./results/el
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `Missing prompt.yaml in A/` | Run `python tools/prepare_personas.py batch` |
| `No persona folders under personas/` | Add subfolders `A/`, `B/`, … with `process*.json` |
| Noah: empty `content` / `summary` in export | Celery worker not running or `/end` not reached |
| Noah: no interviewer messages | Agent not in text mode or wrong LiveKit topics |
| `NOAH_API_URL` connection refused | Start `python main.py` in `backend/` |
| ElevenLabs: no replies | Agent not in chat mode; check `ELEVENLABS_*` |
| ElevenLabs: 60s “No user message” | Agent waits for user first; harness now sends a kick message after 8s — update harness if you still see this |
| Interview never ends | Interviewer missing `[[INTERVIEW_COMPLETE]]` |
| Turn cap exit (`ended_by: turn_cap`) | Interview ran past 80 turns (`full`) or 10 (`smoke`) without sentinel |

---

## Transport reference

**ElevenLabs:** harness uses `text_only` ConvAI, sends interviewee text as `user_message`, and collects interviewer text from `agent_response` and streaming `agent_chat_response_part` events.

**Noah / LiveKit:**

- Interviewee → interviewer: topic `lk.chat`
- Interviewer → interviewee: topic `lk.transcription` (attributes `lk.segment_id`, `lk.transcription_final`)

Harness transcript JSON (per run): `schema_version`, `persona_id`, `project`, `subject_label`, `interviewer`, `turns[]`, `ended_by` (`sentinel` | `turn_cap` | `error` | `manual`).
