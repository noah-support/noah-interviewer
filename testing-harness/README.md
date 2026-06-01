## AI Interviewee Testing Harness

This folder contains the **interviewee side** of a BPMN reconstruction testing harness. It provides:

- **Personas** — one folder per interviewee (`personas/A/`, `B/`, …) with `process*.json` BPMN fragments; prepared YAML at `personas/{name}.yaml`.
- A **persona prep tool** that merges process files per folder into one persona YAML.
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

### Prepare personas (output-test layout)

Each subfolder under `personas/` (`A/`, `B/`, …) holds `process*.json` files. The batch command merges them and writes **`personas/{folder}/prompt.yaml`** (one per folder):

```bash
python tools/prepare_personas.py batch
```

If a `process*.json` is not already Prosaview **fragments** JSON, the tool loads `S0_*.json` from `datasets/ProsaviewDataSets-main/` using the mapping in `personas/devide.txt`.

Legacy Prosaview single-subject mode still works with `--input` / `--input-dir` and `--output-dir`.

Notes:

- The generator rejects outputs containing process-modeling terms (`BPMN`, `gateway`, `node`, `flowchart`, `branch`, `task`) and retries once.
- It will not overwrite existing persona YAMLs unless `--force` is passed.

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

### Run a single interview (debugging)

```bash
python3 runner.py interview \
  --persona personas/A/prompt.yaml \
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
