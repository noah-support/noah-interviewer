import asyncio
import json
import re
import threading
import os
import time
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    AgentServer,
    AgentSession,
    Agent,
    ChatContext,
    ConversationItemAddedEvent,
    TurnHandlingOptions,
    llm,
)
from livekit.agents.llm import ChatMessage
from livekit.plugins import silero, openai, elevenlabs
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from database import db
from models import Interview
from seeder import reset_and_seed, clean_database
from http_api import app as fastapi_app
from tasks import summarize_interview_turns

load_dotenv(".env.local", override=True)

print("--- STARTING WITH URL:", os.getenv("LIVEKIT_URL"), "---")

_ROOM_INTERVIEW_ID_RE = re.compile(r"^interview-(?P<id>\d+)-")


class Interviewer(Agent):
    def __init__(self, *, interview_id: str) -> None:
        self.interview_id = interview_id
        self.turn_counter = 0
        self.summary_cache = ""
        self._summary_cache_last_refresh_s = 0.0
        self._summary_refresh_task: asyncio.Task | None = None
        super().__init__(
            instructions="""You are an AI consultant interviewer called Noah. Your goal is to deeply understand how an employee works — their role, daily tasks, knowledge, expertise, strengths, personal interests, frustrations, bottlenecks, and future ambitions — so that later we can identify opportunities for automation or AI assistance.""",
            chat_ctx=ChatContext(),
        )

    def _load_db_summary(self) -> str:
        db.connect(reuse_if_open=True)
        try:
            interview = Interview.get_or_none(Interview.id == int(self.interview_id))
            return (interview.summary or "").strip() if interview else ""
        finally:
            db.close()

    async def _refresh_summary_cache(self) -> None:
        # Run the blocking peewee query off the event loop.
        try:
            summary = await asyncio.to_thread(self._load_db_summary)
        except Exception as e:
            print(f"[SYSTEM] failed to refresh summary cache: {e}")
            return

        self.summary_cache = summary
        self._summary_cache_last_refresh_s = time.monotonic()

    def _maybe_schedule_summary_refresh(self, *, force: bool = False) -> None:
        # Avoid spawning unlimited refresh tasks; keep at most one in-flight.
        if self._summary_refresh_task and not self._summary_refresh_task.done():
            return

        if not force:
            # Throttle refreshes; we don't need sub-second updates.
            now = time.monotonic()
            if now - self._summary_cache_last_refresh_s < 3.0:
                return

        self._summary_refresh_task = asyncio.create_task(self._refresh_summary_cache())

    def _reply_chat_ctx(self) -> ChatContext:
        # Only the last 10 items + the persisted summary should ever go to the LLM.
        recent = (
            self.chat_ctx.copy(
                exclude_config_update=True,
                exclude_handoff=True,
                exclude_empty_message=True,
            )
            .truncate(max_items=10)
        )

        recent.add_message(
            role="system",
            content=f"Summary so far (from database):\n{self.summary_cache}",
            created_at=0.0,
        )
        return recent

    def _enqueue_summary_job(self) -> None:
        # Summarizer only needs role + content (user/assistant messages only).
        raw = self.chat_ctx.to_dict()
        items = raw.get("items") if isinstance(raw, dict) else None
        filtered = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "message":
                    continue
                if item.get("role") not in ("user", "assistant"):
                    continue
                filtered.append(
                    {
                        "role": item.get("role"),
                        "content": item.get("content"),
                    }
                )
        transcript_json = json.dumps({"items": filtered}, ensure_ascii=False)
        summarize_interview_turns.delay(
            interview_id=self.interview_id,
            transcript_json=transcript_json,
        )

    async def on_enter(self) -> None:
        print(f"[SYSTEM] setup complete | id: {self.interview_id} | counter: {self.turn_counter}")
        # Prime summary cache once at session start.
        await self._refresh_summary_cache()
        return await super().on_enter()

    async def on_exit(self) -> None:
        try:
            self._enqueue_summary_job()
            print("[SYSTEM] summary job enqueued")
            # Best-effort: refresh cache shortly after enqueue (job runs async).
            self._maybe_schedule_summary_refresh(force=True)
        except Exception as e:
            print(f"[SYSTEM] failed to enqueue summary job: {e}")
        return await super().on_exit()
    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        self.turn_counter += 1
        print(f"[SYSTEM] add turn counter: turncounter = {self.turn_counter}")

        # Force the LLM context to be: DB summary + last 10 items.
        # Refresh summary cache in background if needed (no DB calls in hot path).
        self._maybe_schedule_summary_refresh()
        reply_ctx = self._reply_chat_ctx()
        # LiveKit passes `turn_ctx` by reference as "the context about to be sent";
        # swap its internal items to fully control what the model sees.
        turn_ctx._items = list(reply_ctx.items)  # type: ignore[attr-defined]

        # start job if above SUMMARY_AMOUNT amount
        summary_every = int(os.getenv("SUMMARY_AMOUNT", "5"))
        if self.turn_counter >= summary_every:
            try:
                self._enqueue_summary_job()
                print("[SYSTEM] periodic summary job enqueued")
                # Once we request a new summary, start refreshing cache in background.
                self._maybe_schedule_summary_refresh(force=True)
            except Exception as e:
                print(f"[SYSTEM] failed to enqueue periodic summary job: {e}")
            self.turn_counter = 0
        return await super().on_user_turn_completed(turn_ctx, new_message)


server = AgentServer()


@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()

    room_name = getattr(ctx.room, "name", "") or ""
    m = _ROOM_INTERVIEW_ID_RE.match(room_name)
    if not m:
        raise RuntimeError(f"Unexpected room name format: {room_name!r}")
    interview_id = m.group("id")

    session = AgentSession(
        stt=elevenlabs.STT(model_id="scribe_v2_realtime"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(
            voice_id="1SM7GgM6IMuvQlz2BwM3",
            model="eleven_flash_v2_5"
        ),
        vad=silero.VAD.load(),
        preemptive_generation=False,
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            interruption={"enabled": False},
        ),
    )

    agent = Interviewer(interview_id=interview_id)

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        if not isinstance(event.item, ChatMessage):
            return
        print(f"[SYSTEM] Conversation item added: {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}")

    disconnected_event = asyncio.Event()

    @ctx.room.on("disconnected")
    def _on_room_disconnected(*args, **kwargs):
        disconnected_event.set()

    try:
        await session.start(room=ctx.room, agent=agent)
        await session.generate_reply(
            instructions="Greet the user and give an one sentence introduction of what you do.",
            chat_ctx=agent._reply_chat_ctx(),
        )
        await disconnected_event.wait()

    except asyncio.CancelledError:
        raise

    except Exception:
        raise


if __name__ == "__main__":
    reset_and_seed()

    def _run_api():
        import uvicorn

        uvicorn.run(
            fastapi_app,
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            log_level=os.getenv("API_LOG_LEVEL", "info"),
        )

    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()

    try:
        agents.cli.run_app(server)
    finally:
        clean_database()
