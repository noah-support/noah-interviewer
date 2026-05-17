import os
import json
from typing import TypedDict
from env_loader import load_app_env
from openai import OpenAI
from celery_app import celery_app
from database import db
from models import Interview
from prompts import DEFAULT_TRANSCRIPT_SUMMARY_PROMPT

load_app_env()

class Turn(TypedDict):
    party: str
    message: str


def _summary_prompt() -> str:
    return os.getenv("SUMMARY_PROMPT", DEFAULT_TRANSCRIPT_SUMMARY_PROMPT)


def _summary_model() -> str:
    return os.getenv("SUMMARY_MODEL", "gpt-4o")


def summarize_transcript_text(transcript_json: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY (Celery worker must load backend/.env.local or have env var set)")

    client = OpenAI(api_key=api_key)

    prompt = _summary_prompt()
    model = _summary_model()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": transcript_json},
        ],
        temperature=0.2,
    )

    return (completion.choices[0].message.content or "").strip()


def _messages_only_transcript_json(transcript_json: str) -> str:
    """
    Ensure we only persist user/assistant chat messages into Interview.content.
    LiveKit ChatContext can contain non-message items (config updates, tool calls, etc.).
    """
    try:
        data = json.loads(transcript_json)
    except Exception:
        # If it's not JSON, fall back to whatever we got (better than dropping content).
        return transcript_json

    items = data.get("items")
    if not isinstance(items, list):
        return transcript_json

    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue
        # Persist only what we need: role + content.
        filtered.append({"role": role, "content": item.get("content")})

    return json.dumps({"items": filtered}, ensure_ascii=False)


@celery_app.task(name="tasks.summarize_interview_turns")
def summarize_interview_turns(*, interview_id: int, transcript_json: str) -> dict:
    minimal_json = _messages_only_transcript_json(transcript_json)
    summary = summarize_transcript_text(minimal_json)
    content_json = minimal_json

    db.connect(reuse_if_open=True)
    try:
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            return {"ok": False, "error": "Interview not found"}
        interview.content = content_json
        interview.summary = summary
        interview.save()
        return {"ok": True}
    finally:
        db.close()
