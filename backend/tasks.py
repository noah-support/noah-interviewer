import os
from typing import TypedDict
from dotenv import load_dotenv
from openai import OpenAI
from celery_app import celery_app
from database import db
from models import Interview

load_dotenv(".env.local", override=True)

class Turn(TypedDict):
    party: str
    message: str


def _summary_prompt() -> str:
    return os.getenv(
        "SUMMARY_PROMPT",
        "Summarize the interview conversation so far in a concise, factual way. "
        "Focus on key goals, constraints, decisions, and any open questions. "
        "Write in plain text, no bullet symbols.",
    )


def _summary_model() -> str:
    return os.getenv("SUMMARY_MODEL", "gpt-4o-mini")


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


@celery_app.task(name="tasks.summarize_interview_turns")
def summarize_interview_turns(*, interview_id: int, transcript_json: str) -> dict:
    summary = summarize_transcript_text(transcript_json)

    db.connect(reuse_if_open=True)
    try:
        interview = Interview.get_or_none(Interview.id == interview_id)
        if not interview:
            return {"ok": False, "error": "Interview not found"}
        # Persist the full transcript JSON so the UI / later jobs can re-use it.
        interview.content = transcript_json
        interview.summary = summary
        interview.save()
        return {"ok": True}
    finally:
        db.close()
