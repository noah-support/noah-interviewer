## AI Interviewee Testing Harness

This folder contains the **interviewee side** of a BPMN reconstruction testing harness. It provides:

- **Personas** — one folder per interviewee (`personas/A/`, `B/`, …) with `process*.json` source data; batch prep writes `persona.json` ground truth per folder.
- A **persona prep tool** that generates structured `persona.json` from local process files (legacy mode can still emit YAML from Prosaview subjects).
- A **batch runner** that runs all personas against Noah (LiveKit) or ElevenLabs.

### Sentinel (end-of-interview)

The interviewer must end its final message with the exact sentinel string on a line by itself:

`[[INTERVIEW_COMPLETE]]`

The harness strips this sentinel from stored transcripts, generates one final closing reply, then disconnects.

### Setup

```bash
cd testing-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
cp config.example.env .env
```

### Prepare personas (ground-truth JSON)

Each subfolder under `personas/` (`A/`, `B/`, …) holds `process*.json` files. The batch command writes **`personas/{folder}/persona.json`** (one per folder, one `Process` per process file):

```bash
python tools/prepare_personas.py batch
```

Batch prep uses the literal contents of each folder’s `process*.json` files (no cross-folder merge, no dataset substitution).

Legacy Prosaview single-subject mode still works with `--input` / `--input-dir` and `--output-dir` (writes YAML).

Notes:

- Output is validated with Pydantic; invalid generations are retried (up to three attempts).
- It will not overwrite existing `persona.json` files unless `--force` is passed.

### Batch output test (all personas)

```bash
# Noah — DB project output-test-noah, LiveKit, combined JSON in --output-dir
python3 runner.py --interviewer noah --output-dir ./out

# ElevenLabs — ConvAI only; no DB or JSON export
python3 runner.py --interviewer elevenlabs --output-dir ./out
```

Shows a progress bar per persona folder (`A`, `B`, `C`, `D`). See [TESTING.md](TESTING.md) for prerequisites.

**Noah JSON export** (`{output-dir}/output-test-noah_{timestamp}.json`):

```json
{
  "A": {
    "content": { "items": [ { "role": "user", "content": "..." } ] },
    "discovery_state_json": { },
    "summary": "..."
  }
}
```

Fields match the Postgres `Interview` row: `content`, `discovery_state_json`, `summary`.

### Evaluate interview reconstructions

Stage artifacts into each persona folder, then run reconstruction + validation against `persona.json`:

```bash
python tools/evaluate_interviews.py stage --noah-export ./out/output-test-noah_*.json --transcripts-root ./transcripts/output-test
python tools/evaluate_interviews.py batch
```

See [TESTING.md](TESTING.md) for canonical filenames and outputs (`result_*.json`, `validation_*.json`, `validation.md`).

### Run a single interview (debugging)

```bash
python3 runner.py interview \
  --persona personas/A/persona.json \
  --interviewer noah \
  --mode full
```

Use `--interviewer elevenlabs` or `noah` (`noah` maps to the LiveKit client).

### Transcript format

Per-interview harness transcripts (optional, under `transcripts/`):

- `transcripts/<project>/<subject_label>__<interviewer>__<timestamp>.json`

Schema: `schema_version`, `persona_id`, `project`, `subject_label`, `interviewer`, `turns[]`, `ended_by`.

### Transport contracts

#### ElevenLabs (text-only ConvAI)

- `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`
- Chat/text mode; harness sends `user_message`, receives agent responses.

#### Noah / LiveKit (text streams)

- `NOAH_API_URL`, `LIVEKIT_URL`, and token or `LIVEKIT_API_KEY` + `LIVEKIT_API_SECRET`
- Topics: `lk.chat` (out), `lk.transcription` (in)
- Batch mode provisions token/room via the Noah API per interview.
