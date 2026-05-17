"""
LiveKit voice agent (Noah interviewer): session wiring, discovery state, summarization hooks.

Run from `backend/`:

    python interviewer.py dev
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time

from env_loader import load_app_env
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

from bpmn_redis import append_buffer_line, delete_room_discovery_keys, ensure_default_state
from database import db
from discovery_persist import persist_discovery_state_to_db
from models import Interview
from prompts import (
    AGENT_INSTRUCTIONS_NOAH,
    OPENING_AFTER_FIRST_USER_TURN,
    OPENING_AFTER_SECOND_USER_TURN,
    SUMMARY_FROM_DB_PREFIX,
    format_greeting_instructions,
)
from tasks import summarize_interview_turns
from livekit.plugins import groq

load_app_env()

print("--- STARTING WITH URL:", os.getenv("LIVEKIT_URL"), "---")

_ROOM_INTERVIEW_ID_RE = re.compile(r"^interview-(?P<id>\d+)-")


class Interviewer(Agent):
    def __init__(self, *, interview_id: str, room_name: str) -> None:
        self.interview_id = interview_id
        self.room_name = room_name
        self.turn_counter = 0
        self.tracker_turn_counter = 0
        self.summary_cache = ""
        self._bpmn_directive_message = ""
        self._opening_directive_message = ""
        self._opening_user_turn_index = 0
        self.interviewee_username = ""
        self._summary_cache_last_refresh_s = 0.0
        self._last_discovery_persist_s = 0.0
        self._summary_refresh_task: asyncio.Task | None = None
        super().__init__(
            instructions=AGENT_INSTRUCTIONS_NOAH,
            chat_ctx=ChatContext(),
        )

    def _load_db_summary(self) -> str:
        db.connect(reuse_if_open=True)
        try:
            interview = Interview.get_or_none(Interview.id == int(self.interview_id))
            return (interview.summary or "").strip() if interview else ""
        finally:
            db.close()

    def _load_interviewee_username(self) -> str:
        db.connect(reuse_if_open=True)
        try:
            interview = Interview.get_or_none(Interview.id == int(self.interview_id))
            return (interview.username or "").strip() if interview else ""
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
            content=f"{SUMMARY_FROM_DB_PREFIX}{self.summary_cache}",
            created_at=0.0,
        )

        if (self._bpmn_directive_message or "").strip():
            recent.add_message(
                role="system",
                content=self._bpmn_directive_message,
                created_at=0.0,
            )

        if (self._opening_directive_message or "").strip():
            recent.add_message(
                role="system",
                content=self._opening_directive_message,
                created_at=0.0,
            )

        if (self.interviewee_username or "").strip():
            recent.add_message(
                role="system",
                content=(
                    f"Interviewee name (use in greeting and naturally in conversation): "
                    f"{self.interviewee_username.strip()}"
                ),
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
            interview_id=int(self.interview_id),
            transcript_json=transcript_json,
        )

    async def on_enter(self) -> None:
        self.tracker_turn_counter = 0
        self._opening_user_turn_index = 0
        self._opening_directive_message = ""
        print(f"[SYSTEM] setup complete | id: {self.interview_id} | counter: {self.turn_counter}")
        try:
            await asyncio.to_thread(ensure_default_state, self.room_name)
        except Exception as e:
            print(f"[SYSTEM] ensure_default_state failed: {e}")
        # Prime summary cache once at session start.
        await self._refresh_summary_cache()
        try:
            self.interviewee_username = await asyncio.to_thread(self._load_interviewee_username)
        except Exception as e:
            print(f"[SYSTEM] failed to load interviewee username: {e}")
        return await super().on_enter()

    def _persist_discovery_debounced(self) -> None:
        now = time.monotonic()
        debounce = float(os.getenv("DISCOVERY_PERSIST_DEBOUNCE_S", "3"))
        if now - self._last_discovery_persist_s < debounce:
            return
        self._last_discovery_persist_s = now
        persist_discovery_state_to_db(
            interview_id=int(self.interview_id),
            room_name=self.room_name,
        )

    def _recent_transcript_for_tracker(self, *, max_messages: int = 8) -> list[dict[str, str]]:
        """Last user/assistant lines from chat for a final state-tracker pass."""
        raw = self.chat_ctx.to_dict()
        items = raw.get("items") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            return []
        lines: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            role = item.get("role")
            if role not in ("user", "assistant"):
                continue
            content = item.get("content")
            text = ""
            if isinstance(content, str):
                text = content.strip()
            elif isinstance(content, list):
                parts = [
                    p.get("text", "")
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                text = " ".join(p for p in parts if p).strip()
            if text:
                lines.append({"role": role, "content": text})
        return lines[-max_messages:]

    async def _finalize_discovery_state(self) -> None:
        rn = self.room_name
        iid = int(self.interview_id)
        tail = self._recent_transcript_for_tracker()

        def work() -> None:
            from state_tracker import flush_tracker_final

            flush_tracker_final(room_name=rn, tail_transcript=tail)
            persist_discovery_state_to_db(interview_id=iid, room_name=rn)
            delete_room_discovery_keys(rn)

        await asyncio.to_thread(work)

    async def _append_assistant_buffer(self, text: str) -> None:
        await asyncio.to_thread(
            append_buffer_line,
            self.room_name,
            "assistant",
            text,
        )

    async def _on_assistant_interrupted(self) -> None:
        await asyncio.to_thread(self._persist_discovery_debounced)

    async def on_exit(self) -> None:
        try:
            await self._finalize_discovery_state()
        except Exception as e:
            print(f"[SYSTEM] finalize discovery state failed: {e}")
        try:
            self._enqueue_summary_job()
            print("[SYSTEM] summary job enqueued")
            # Best-effort: refresh cache shortly after enqueue (job runs async).
            self._maybe_schedule_summary_refresh(force=True)
        except Exception as e:
            print(f"[SYSTEM] failed to enqueue summary job: {e}")
        return await super().on_exit()

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        user_text = (new_message.text_content or "").strip()
        if user_text:
            try:
                await asyncio.to_thread(
                    append_buffer_line,
                    self.room_name,
                    "user",
                    user_text,
                )
            except Exception as e:
                print(f"[SYSTEM] append user buffer failed: {e}")

        self._opening_user_turn_index += 1
        if self._opening_user_turn_index == 1:
            self._opening_directive_message = OPENING_AFTER_FIRST_USER_TURN
        elif self._opening_user_turn_index == 2:
            self._opening_directive_message = OPENING_AFTER_SECOND_USER_TURN
        else:
            self._opening_directive_message = ""

        self.turn_counter += 1
        print(f"[SYSTEM] add turn counter: turncounter = {self.turn_counter}")
        self._maybe_schedule_summary_refresh()

        rn = self.room_name

        def _tracker_and_directive() -> tuple[bool, str]:
            from bpmn_redis import buffer_length, get_state_dict
            from hobby_schema import PHASE_DEEPDIVE, meta_phase
            from directive_prompt import (
                build_deepdive_entry_block,
                build_dynamic_directive_block,
            )
            from state_tracker import run_state_tracker

            before = get_state_dict(rn)
            before_discovery = before.get("discovery") if isinstance(before.get("discovery"), dict) else {}
            before_done = bool(before_discovery.get("is_completed"))
            before_phase = meta_phase(before)

            flushed = True
            if buffer_length(rn) > 0:
                flushed = run_state_tracker(room_name=rn, allow_empty_buffer=False)

            after = get_state_dict(rn)
            after_discovery = after.get("discovery") if isinstance(after.get("discovery"), dict) else {}
            after_done = bool(after_discovery.get("is_completed"))
            after_phase = meta_phase(after)
            just_completed = not before_done and after_done
            just_entered_deepdive = (
                before_phase != PHASE_DEEPDIVE and after_phase == PHASE_DEEPDIVE
            )

            if just_completed or just_entered_deepdive:
                directive = build_deepdive_entry_block(after)
            else:
                directive = build_dynamic_directive_block(after)
            return flushed, directive

        try:
            _flushed_ok, directive = await asyncio.to_thread(_tracker_and_directive)
            self._bpmn_directive_message = directive
        except Exception as e:
            print(f"[SYSTEM] state tracker / directive failed: {e}")
            self._bpmn_directive_message = ""

        reply_ctx = self._reply_chat_ctx()
        turn_ctx._items = list(reply_ctx.items)

        # start job if above SUMMARY_AMOUNT amount
        summary_every = int(os.getenv("SUMMARY_AMOUNT", "5"))
        if self.turn_counter >= summary_every:
            try:
                self._enqueue_summary_job()
                print("[SYSTEM] periodic summary job enqueued")
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

    loop = asyncio.get_running_loop()

    session = AgentSession(
        stt=elevenlabs.STT(model_id="scribe_v2_realtime"),
        llm=openai.LLM(model="gpt-5.4-mini"),
        tts=elevenlabs.TTS(
            voice_id="1SM7GgM6IMuvQlz2BwM3",
            model="eleven_flash_v2_5",
        ),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(
                unlikely_threshold=float(
                    os.getenv("TURN_EOU_UNLIKELY_THRESHOLD", "0.78")
                ),
            ),
            endpointing={
                "min_delay": float(os.getenv("TURN_MIN_ENDPOINTING_DELAY", "1.0")),
                "max_delay": float(os.getenv("TURN_MAX_ENDPOINTING_DELAY", "4.0")),
            },
            interruption={
                "enabled": True,
                "min_duration": 0.75,
                "min_words": 2,
                "resume_false_interruption": False,
            },
            preemptive_generation={"enabled": False},
        ),
    )

    agent = Interviewer(interview_id=interview_id, room_name=room_name)

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        if not isinstance(event.item, ChatMessage):
            return
        msg = event.item
        print(
            f"[SYSTEM] Conversation item added: {msg.role}: {msg.text_content}. interrupted: {msg.interrupted}"
        )
        if msg.role == "assistant" and getattr(msg, "interrupted", False):
            loop.create_task(agent._on_assistant_interrupted())
            return
        if msg.role != "assistant":
            return
        text = (msg.text_content or "").strip()
        if not text:
            return
        loop.create_task(agent._append_assistant_buffer(text))

    disconnected_event = asyncio.Event()

    @ctx.room.on("disconnected")
    def _on_room_disconnected(*args, **kwargs):
        disconnected_event.set()

    try:
        try:
            agent.interviewee_username = await asyncio.to_thread(agent._load_interviewee_username)
        except Exception as e:
            print(f"[SYSTEM] failed to load interviewee username before start: {e}")

        await session.start(room=ctx.room, agent=agent)

        def _initial_directive() -> str:
            from bpmn_redis import get_state_dict
            from directive_prompt import build_dynamic_directive_block

            return build_dynamic_directive_block(get_state_dict(room_name))

        agent._bpmn_directive_message = await asyncio.to_thread(_initial_directive)

        greeting = format_greeting_instructions(agent.interviewee_username)
        await session.generate_reply(
            instructions=greeting,
            chat_ctx=agent._reply_chat_ctx(),
        )
        await disconnected_event.wait()

    except asyncio.CancelledError:
        raise

    except Exception:
        raise


if __name__ == "__main__":
    from seeder import clean_database

    _clean_on_exit = os.getenv("CLEAN_DATABASE_ON_EXIT", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    try:
        agents.cli.run_app(server)
    finally:
        if _clean_on_exit:
            clean_database()
