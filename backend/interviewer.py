"""
LiveKit voice agent (Noah interviewer): session wiring, RAG, BPMN state, summarization hooks.

Run from `backend/`:

    python interviewer.py dev
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    AgentServer,
    AgentSession,
    Agent,
    ChatContext,
    ConversationItemAddedEvent,
    StopResponse,
    TurnHandlingOptions,
    llm,
    room_io,
)
from livekit.agents.types import NOT_GIVEN
from livekit.agents.voice.speech_handle import SpeechHandle
from livekit.agents.voice.room_io.types import TextInputEvent
from livekit.agents.llm import ChatMessage
from livekit.plugins import silero, openai, elevenlabs
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from pinecone import Pinecone

from bpmn_redis import append_buffer_line, delete_room_discovery_keys, ensure_default_state, get_state_dict
from interview_close import (
    build_premature_close_recovery_instruction,
    can_close_interview,
    is_interviewer_closing_message,
)
from declined_answers import (
    build_repeat_question_recovery_instruction,
    reply_reasks_after_decline,
    user_declined_to_answer,
)
from bpmn_schema import first_active_step, resolve_focus_process_name, step_missing_fields
from database import db
from discovery_persist import persist_discovery_state_to_db
from models import Interview, Project
from prompts import (
    AGENT_INSTRUCTIONS_NOAH,
    OPENING_AFTER_FIRST_USER_TURN,
    OPENING_AFTER_SECOND_USER_TURN,
    RAG_CONTEXT_PREAMBLE,
    SUMMARY_FROM_DB_PREFIX,
    format_greeting_instructions,
)
from rag.embeddings import embed_texts
from tasks import summarize_interview_turns
from livekit.plugins import groq

load_dotenv(".env.local", override=True)

logger = logging.getLogger("noah.interviewer")


def _configure_interviewer_logging() -> None:
    level_name = (os.getenv("NOAH_LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    if logging.getLogger("noah").handlers:
        logging.getLogger("noah").setLevel(level)
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger("noah")
    root.addHandler(handler)
    root.setLevel(level)


_configure_interviewer_logging()
logger.info("Starting interviewer (LIVEKIT_URL=%s)", os.getenv("LIVEKIT_URL"))

_ROOM_INTERVIEW_ID_RE = re.compile(r"^interview-(?P<id>\d+)-")


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _interviewer_text_only() -> bool:
    return _env_flag("NOAH_INTERVIEWER_TEXT_ONLY")


def _keep_session_on_disconnect() -> bool:
    """When true, a brief harness disconnect does not tear down the agent session."""
    return _env_flag("NOAH_KEEP_SESSION_ON_DISCONNECT")


def _room_options_for_session(
    *,
    text_input_cb,
    text_only: bool,
    participant_identity: str,
) -> room_io.RoomOptions:
    identity = (participant_identity or "").strip()
    common: dict = {
        "text_input": room_io.TextInputOptions(text_input_cb=text_input_cb),
        "close_on_disconnect": not _keep_session_on_disconnect(),
    }
    if identity:
        common["participant_identity"] = identity
    if text_only:
        return room_io.RoomOptions(
            **common,
            text_output=room_io.TextOutputOptions(sync_transcription=False),
            audio_input=False,
            audio_output=False,
        )
    return room_io.RoomOptions(**common)


def _run_tracker_and_directive(room_name: str, *, last_user_text: str | None = None) -> str:
    from bpmn_redis import buffer_length, get_state_dict, read_buffer_lines
    from bpmn_schema import PHASE_DEEPDIVE, meta_phase
    from directive_prompt import build_deepdive_entry_block, build_dynamic_directive_block
    from state_tracker import run_state_tracker

    t0 = time.monotonic()
    buf_len = buffer_length(room_name)
    logger.info("state_tracker start room=%s buffer_lines=%s", room_name, buf_len)

    before = get_state_dict(room_name)
    before_discovery = before.get("discovery") if isinstance(before.get("discovery"), dict) else {}
    before_done = bool(before_discovery.get("is_completed"))
    before_phase = meta_phase(before)

    if buffer_length(room_name) > 0:
        run_state_tracker(room_name=room_name, allow_empty_buffer=False)

    after = get_state_dict(room_name)
    after_discovery = after.get("discovery") if isinstance(after.get("discovery"), dict) else {}
    after_done = bool(after_discovery.get("is_completed"))
    after_phase = meta_phase(after)
    just_completed = not before_done and after_done
    just_entered_deepdive = before_phase != PHASE_DEEPDIVE and after_phase == PHASE_DEEPDIVE

    if not (last_user_text or "").strip():
        for line in reversed(read_buffer_lines(room_name)):
            if line.get("role") == "user":
                last_user_text = (line.get("content") or "").strip()
                break

    if just_completed or just_entered_deepdive:
        block = build_deepdive_entry_block(after)
    else:
        block = build_dynamic_directive_block(after, last_user_text=last_user_text)

    elapsed = time.monotonic() - t0
    logger.info(
        "state_tracker done room=%s phase=%s->%s elapsed=%.2fs directive_chars=%s",
        room_name,
        before_phase,
        after_phase,
        elapsed,
        len(block),
    )
    return block


class Interviewer(Agent):
    def __init__(self, *, interview_id: str, room_name: str) -> None:
        self.interview_id = interview_id
        self.room_name = room_name
        self.turn_counter = 0
        self.tracker_turn_counter = 0
        self.summary_cache = ""
        self._latest_rag_context_message = ""
        self._rag_disabled = False
        self._bpmn_directive_message = ""
        self._opening_directive_message = ""
        self._opening_user_turn_index = 0
        self.interviewee_username = ""
        self.project_namespace = ""
        self._summary_cache_last_refresh_s = 0.0
        self._last_discovery_persist_s = 0.0
        self._summary_refresh_task: asyncio.Task | None = None
        self._buffer_tasks: set[asyncio.Task[None]] = set()
        self._text_input_lock = asyncio.Lock()
        self._tracker_lock = asyncio.Lock()
        self._last_user_turn_text = ""
        super().__init__(
            instructions=AGENT_INSTRUCTIONS_NOAH,
            chat_ctx=ChatContext(),
        )

    def _build_rag_context_message(self, *, query_text: str) -> str:
        if self._rag_disabled:
            return ""

        query = (query_text or "").strip()
        if not query:
            return ""

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            return ""
        namespace = (self.project_namespace or "").strip()
        if not namespace:
            return ""

        index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
        max_score = float(os.getenv("RAG_MAX_MATCH_SCORE", "0.85"))
        top_k = int(os.getenv("RAG_TOP_K", "5"))
        # Fetch more than we need so the < max_score filter still yields results.
        fetch_k = max(top_k * 5, 25)

        try:
            emb = embed_texts([query])[0]
            pc = Pinecone(api_key=api_key)
            index = pc.Index(index_name)
            res = index.query(
                namespace=namespace,
                vector=emb,
                top_k=fetch_k,
                include_metadata=True,
            )
        except Exception as e:
            print(f"[SYSTEM] pinecone RAG query failed: {e}")
            return ""

        # Pinecone python client returns either dict-like or object-like results depending on version.
        matches = None
        if isinstance(res, dict):
            matches = res.get("matches")
        else:
            matches = getattr(res, "matches", None)
        if not isinstance(matches, list):
            return ""

        picked: list[dict] = []
        for m in matches:
            if not isinstance(m, dict):
                # Some client versions return objects; support those too.
                score = getattr(m, "score", None)
                md = getattr(m, "metadata", None)
                m = {"score": score, "metadata": md}

            score = m.get("score")
            if not isinstance(score, (int, float)):
                continue
            if score >= max_score:
                continue

            md = m.get("metadata")
            if not isinstance(md, dict):
                continue
            text = (md.get("text") or "").strip()
            if not text:
                continue
            if (md.get("source_filename") or "") == "__namespace__":
                continue
            picked.append({"score": float(score), "metadata": md, "text": text})

        if not picked:
            return ""

        picked.sort(key=lambda x: x["score"], reverse=True)
        picked = picked[:top_k]

        lines: list[str] = []
        for i, item in enumerate(picked, start=1):
            md = item["metadata"]
            source = (md.get("source_filename") or "unknown").strip()
            chunk_id = md.get("chunk_id")
            score_pct = item["score"] * 100.0
            header = f"[KB {i}] {source}"
            if isinstance(chunk_id, int):
                header += f" (chunk {chunk_id})"
            header += f" — match: {score_pct:.1f}%"
            lines.append(header)
            lines.append(item["text"])
            lines.append("")

        return RAG_CONTEXT_PREAMBLE + "\n".join(lines).strip()

    def _load_db_summary(self) -> str:
        db.connect(reuse_if_open=True)
        try:
            interview = Interview.get_or_none(Interview.id == int(self.interview_id))
            return (interview.summary or "").strip() if interview else ""
        finally:
            db.close()

    def _load_project_context(self) -> tuple[str, bool]:
        """Return (pinecone namespace, rag_disabled). RAG off for output-test* projects."""
        db.connect(reuse_if_open=True)
        try:
            interview = (
                Interview.select(Interview, Project)
                .join(Project)
                .where(Interview.id == int(self.interview_id))
                .first()
            )
            if not interview:
                return "", _env_flag("NOAH_DISABLE_RAG")
            project = interview.project
            ns = (project.namespace or "").strip() or f"project-{project.id}"
            title = (project.title or "").strip().lower()
            rag_disabled = _env_flag("NOAH_DISABLE_RAG") or title.startswith("output-test")
            return ns, rag_disabled
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

        # add message with RAG chunks
        if (self._latest_rag_context_message or "").strip():
            recent.add_message(
                role="system",
                content=self._latest_rag_context_message,
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
            ns, rag_disabled = await asyncio.to_thread(self._load_project_context)
            self.project_namespace = ns
            self._rag_disabled = rag_disabled
            if rag_disabled:
                print("[SYSTEM] RAG disabled for this interview (output-test project or NOAH_DISABLE_RAG)")
        except Exception as e:
            print(f"[SYSTEM] failed to load project context: {e}")
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

    async def _wait_buffer_tasks(self) -> None:
        """Let pending transcript→Redis buffer writes finish before state tracker runs."""
        pending = [t for t in self._buffer_tasks if not t.done()]
        if not pending:
            return
        await asyncio.gather(*pending, return_exceptions=True)
        self._buffer_tasks.clear()

    def _tracker_timeout_s(self) -> float:
        raw = (os.getenv("STATE_TRACKER_TIMEOUT_S") or "90").strip()
        try:
            return max(15.0, float(raw))
        except ValueError:
            return 90.0

    def _reply_playout_timeout_s(self) -> float:
        raw = (os.getenv("NOAH_REPLY_PLAYOUT_TIMEOUT_S") or "120").strip()
        try:
            return max(30.0, float(raw))
        except ValueError:
            return 120.0

    async def _refresh_bpmn_directive(self) -> None:
        await self._wait_buffer_tasks()
        timeout_s = self._tracker_timeout_s()
        t0 = time.monotonic()
        logger.info(
            "refresh_bpmn_directive start room=%s interview_id=%s timeout=%.0fs",
            self.room_name,
            self.interview_id,
            timeout_s,
        )
        try:
            last_user = (self._last_user_turn_text or "").strip() or None
            directive = await asyncio.wait_for(
                asyncio.to_thread(
                    _run_tracker_and_directive,
                    self.room_name,
                    last_user_text=last_user,
                ),
                timeout=timeout_s,
            )
            self._bpmn_directive_message = directive
        except asyncio.TimeoutError:
            logger.warning(
                "state tracker timed out after %.0fs room=%s; keeping prior directive",
                timeout_s,
                self.room_name,
            )
        except Exception as e:
            logger.exception(
                "state tracker / directive failed room=%s: %s",
                self.room_name,
                e,
            )
        try:
            await asyncio.to_thread(self._persist_discovery_debounced)
        except Exception as e:
            logger.warning("discovery persist failed room=%s: %s", self.room_name, e)

        logger.info(
            "refresh_bpmn_directive done room=%s elapsed=%.2fs",
            self.room_name,
            time.monotonic() - t0,
        )

        summary_every = int(os.getenv("SUMMARY_AMOUNT", "5"))
        if self.turn_counter >= summary_every:
            try:
                self._enqueue_summary_job()
                logger.info("periodic summary job enqueued interview_id=%s", self.interview_id)
                self._maybe_schedule_summary_refresh(force=True)
            except Exception as e:
                logger.warning("failed to enqueue periodic summary job: %s", e)
            self.turn_counter = 0

    def _schedule_bpmn_refresh_after_turn(self) -> None:
        """Run state tracker off the text-input lock so the next lk.chat turn is not blocked."""

        async def _run() -> None:
            async with self._tracker_lock:
                await self._refresh_bpmn_directive()

        asyncio.create_task(_run())

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

    async def _prepare_user_turn(self, user_text: str) -> None:
        """Buffer user text, opening hints, and RAG — without blocking on state tracker."""
        text = (user_text or "").strip()
        if text:
            try:
                await asyncio.to_thread(
                    append_buffer_line,
                    self.room_name,
                    "user",
                    text,
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
        self._last_user_turn_text = text
        logger.info(
            "prepare_user_turn room=%s turn_counter=%s text_chars=%s",
            self.room_name,
            self.turn_counter,
            len(text),
        )
        self._maybe_schedule_summary_refresh()
        if not self._rag_disabled:
            try:
                self._latest_rag_context_message = await asyncio.to_thread(
                    self._build_rag_context_message,
                    query_text=text,
                )
            except Exception as e:
                print(f"[SYSTEM] failed to build RAG context message: {e}")
                self._latest_rag_context_message = ""
        else:
            self._latest_rag_context_message = ""

    async def _on_user_text_for_discovery(self, user_text: str) -> None:
        """STT path: update buffer/RAG, then state tracker before the agent replies."""
        await self._prepare_user_turn(user_text)
        await self._refresh_bpmn_directive()

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        """STT path: refresh state, generate reply with premature-close guard."""
        await self._on_user_text_for_discovery(new_message.text_content or "")
        reply_ctx = self._reply_chat_ctx()
        turn_ctx._items = list(reply_ctx.items)
        await _generate_reply_with_fallback(
            self.session,
            agent=self,
            user_input=new_message.text_content or "",
            chat_ctx=reply_ctx,
        )
        if (new_message.text_content or "").strip():
            self._schedule_bpmn_refresh_after_turn()
        raise StopResponse()


def _empty_reply_fallback() -> str:
    text = (os.getenv("NOAH_EMPTY_REPLY_FALLBACK") or "Could you repeat that?").strip()
    return text or "Could you repeat that?"


def _empty_reply_max_retries() -> int:
    raw = (os.getenv("NOAH_EMPTY_REPLY_MAX_RETRIES") or "1").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 1


def _prior_assistant_message(chat_ctx: ChatContext) -> str:
    """Most recent assistant message already in context (before the turn being generated)."""
    parts: list[str] = []
    for item in reversed(chat_ctx.items):
        if isinstance(item, ChatMessage) and item.role == "assistant":
            text = (item.text_content or "").strip()
            if text:
                return text
    return ""


def _assistant_text_from_speech_handle(handle: SpeechHandle) -> str:
    parts: list[str] = []
    for item in handle.chat_items:
        if isinstance(item, ChatMessage) and item.role == "assistant":
            text = (item.text_content or "").strip()
            if text:
                parts.append(text)
    return " ".join(parts).strip()


async def _wait_reply_playout(
    *,
    agent: Interviewer,
    handle: SpeechHandle,
    room_name: str,
    gen_t0: float,
) -> bool:
    """Wait for playout; return False on timeout (handle interrupted)."""
    playout_timeout = agent._reply_playout_timeout_s()
    try:
        await asyncio.wait_for(handle.wait_for_playout(), timeout=playout_timeout)
    except asyncio.TimeoutError:
        logger.error(
            "generate_reply playout timed out after %.0fs room=%s speech_id=%s interrupted=%s",
            playout_timeout,
            room_name,
            getattr(handle, "id", "?"),
            getattr(handle, "interrupted", None),
        )
        handle.interrupt(force=True)
        return False
    logger.info(
        "generate_reply playout done room=%s elapsed=%.2fs interrupted=%s",
        room_name,
        time.monotonic() - gen_t0,
        getattr(handle, "interrupted", None),
    )
    return True


async def _regenerate_if_premature_close(
    session: AgentSession,
    *,
    agent: Interviewer,
    handle: SpeechHandle,
    chat_ctx: ChatContext,
    room_name: str,
) -> bool:
    """
    If the model tried to close while BPMN state is incomplete, regenerate once.

    Returns True when a replacement reply was generated successfully.
    """
    reply_text = _assistant_text_from_speech_handle(handle)
    if not reply_text or not is_interviewer_closing_message(reply_text):
        return False

    try:
        state = await asyncio.to_thread(get_state_dict, room_name)
    except Exception:
        logger.exception("premature_close guard: failed to load state room=%s", room_name)
        return False

    if can_close_interview(state):
        return False

    recovery = build_premature_close_recovery_instruction(state)
    logger.warning(
        "premature_close blocked room=%s phase=%s reply_preview=%r",
        room_name,
        (state.get("meta") or {}).get("phase"),
        reply_text[:160],
    )
    await session.interrupt()
    gen_t0 = time.monotonic()
    retry_handle = session.generate_reply(
        instructions=recovery,
        allow_interruptions=False,
        input_modality="text",
        chat_ctx=chat_ctx,
    )
    if not await _wait_reply_playout(
        agent=agent, handle=retry_handle, room_name=room_name, gen_t0=gen_t0
    ):
        return False
    retry_text = _assistant_text_from_speech_handle(retry_handle)
    if retry_text and is_interviewer_closing_message(retry_text) and not can_close_interview(
        await asyncio.to_thread(get_state_dict, room_name)
    ):
        logger.error(
            "premature_close guard: retry still closing room=%s preview=%r",
            room_name,
            retry_text[:160],
        )
    return bool(retry_text)


async def _regenerate_if_repeat_question(
    session: AgentSession,
    *,
    agent: Interviewer,
    handle: SpeechHandle,
    chat_ctx: ChatContext,
    room_name: str,
    user_text: str,
) -> bool:
    """Regenerate when the model repeats a question after the user declined to answer."""
    if not user_declined_to_answer(user_text):
        return False

    reply_text = _assistant_text_from_speech_handle(handle)
    previous = _prior_assistant_message(chat_ctx)
    if not reply_text or not previous:
        return False

    try:
        state = await asyncio.to_thread(get_state_dict, room_name)
    except Exception:
        logger.exception("repeat_question guard: failed to load state room=%s", room_name)
        return False

    focus = resolve_focus_process_name(state, prefer_tracker_focus=True)
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    proc = pd.get(focus) if focus and isinstance(pd.get(focus), dict) else {}
    active_step, _ = first_active_step(proc if isinstance(proc, dict) else {})
    missing = step_missing_fields(active_step) if active_step else []

    if not reply_reasks_after_decline(
        previous_assistant=previous,
        new_assistant=reply_text,
        user_text=user_text,
        missing_fields=missing,
    ):
        return False

    recovery = build_repeat_question_recovery_instruction(state, user_text=user_text)
    logger.warning(
        "repeat_question blocked room=%s focus=%r prev=%r new=%r",
        room_name,
        focus,
        previous[:120],
        reply_text[:120],
    )
    await session.interrupt()
    gen_t0 = time.monotonic()
    retry_handle = session.generate_reply(
        instructions=recovery,
        allow_interruptions=False,
        input_modality="text",
        chat_ctx=chat_ctx,
    )
    if not await _wait_reply_playout(
        agent=agent, handle=retry_handle, room_name=room_name, gen_t0=gen_t0
    ):
        return False
    return bool(_assistant_text_from_speech_handle(retry_handle))


async def _generate_reply_with_fallback(
    session: AgentSession,
    *,
    agent: Interviewer,
    user_input: str,
    chat_ctx: ChatContext,
) -> None:
    """
    Generate an assistant turn; retry on empty/timeout, then emit a short fallback line.
    """
    room_name = agent.room_name
    max_retries = _empty_reply_max_retries()
    fallback = _empty_reply_fallback()
    user_text = (user_input or "").strip()

    for attempt in range(max_retries + 1):
        gen_t0 = time.monotonic()
        handle = session.generate_reply(
            user_input=user_text if attempt == 0 else NOT_GIVEN,
            input_modality="text",
            chat_ctx=chat_ctx,
            instructions=(
                "Respond with a brief, relevant follow-up. Do not leave your reply empty."
                if attempt > 0
                else NOT_GIVEN
            ),
        )
        logger.info(
            "generate_reply scheduled room=%s speech_id=%s attempt=%s",
            room_name,
            getattr(handle, "id", "?"),
            attempt,
        )
        if not await _wait_reply_playout(
            agent=agent, handle=handle, room_name=room_name, gen_t0=gen_t0
        ):
            await session.interrupt()
            continue

        reply_text = _assistant_text_from_speech_handle(handle)
        if reply_text:
            if await _regenerate_if_repeat_question(
                session,
                agent=agent,
                handle=handle,
                chat_ctx=chat_ctx,
                room_name=room_name,
                user_text=user_text,
            ):
                return
            if await _regenerate_if_premature_close(
                session,
                agent=agent,
                handle=handle,
                chat_ctx=chat_ctx,
                room_name=room_name,
            ):
                return
            return

        logger.warning(
            "empty assistant reply room=%s attempt=%s interrupted=%s",
            room_name,
            attempt,
            handle.interrupted,
        )
        await session.interrupt()

    gen_t0 = time.monotonic()
    logger.warning(
        "emitting empty-reply fallback room=%s text=%r",
        room_name,
        fallback[:80],
    )
    handle = session.generate_reply(
        instructions=(
            "Say exactly the following to the user, verbatim, with no other words: "
            f"{fallback}"
        ),
        allow_interruptions=False,
        input_modality="text",
        chat_ctx=chat_ctx,
    )
    logger.info(
        "generate_reply fallback scheduled room=%s speech_id=%s",
        room_name,
        getattr(handle, "id", "?"),
    )
    if not await _wait_reply_playout(
        agent=agent, handle=handle, room_name=room_name, gen_t0=gen_t0
    ):
        logger.error("fallback reply playout timed out room=%s", room_name)


async def _noah_text_input_cb(
    session: AgentSession,
    ev: TextInputEvent,
    *,
    agent: Interviewer,
) -> None:
    """
    Text on lk.chat uses generate_reply(), which bypasses on_user_turn_completed.

    Reply first using the directive from the previous turn, then run the state tracker
    so a slow OpenAI merge cannot block lk.transcription for the harness.
    """
    async with agent._text_input_lock:
        turn_t0 = time.monotonic()
        preview = (ev.text or "").strip().replace("\n", " ")[:120]
        logger.info(
            "text_input_cb start room=%s preview=%r",
            agent.room_name,
            preview,
        )
        try:
            await session.interrupt()
            await agent._wait_buffer_tasks()
            user_text = (ev.text or "").strip()
            if user_text:
                await agent._prepare_user_turn(user_text)
                async with agent._tracker_lock:
                    await agent._refresh_bpmn_directive()

            await _generate_reply_with_fallback(
                session,
                agent=agent,
                user_input=ev.text or "",
                chat_ctx=agent._reply_chat_ctx(),
            )

            if user_text:
                agent._schedule_bpmn_refresh_after_turn()
        except Exception:
            logger.exception("text_input_cb failed room=%s", agent.room_name)
            try:
                await _generate_reply_with_fallback(
                    session,
                    agent=agent,
                    user_input="",
                    chat_ctx=agent._reply_chat_ctx(),
                )
            except Exception:
                raise
        finally:
            logger.info(
                "text_input_cb end room=%s total_elapsed=%.2fs",
                agent.room_name,
                time.monotonic() - turn_t0,
            )


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
    text_only = _interviewer_text_only()

    agent = Interviewer(interview_id=interview_id, room_name=room_name)

    async def text_input_cb(session: AgentSession, ev: TextInputEvent) -> None:
        await _noah_text_input_cb(session, ev, agent=agent)

    participant_identity = ""

    if text_only:
        session = AgentSession(llm=openai.LLM(model="gpt-5.4-mini"))
    else:
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

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        if not isinstance(event.item, ChatMessage):
            return
        msg = event.item
        preview = (msg.text_content or "").replace("\n", " ")[:120]
        logger.info(
            "conversation_item_added room=%s role=%s interrupted=%s preview=%r",
            agent.room_name,
            msg.role,
            getattr(msg, "interrupted", False),
            preview,
        )
        if msg.role == "assistant" and getattr(msg, "interrupted", False):
            loop.create_task(agent._on_assistant_interrupted())
            return
        if msg.role != "assistant":
            return
        text = (msg.text_content or "").strip()
        if not text:
            return
        task = loop.create_task(agent._append_assistant_buffer(text))
        agent._buffer_tasks.add(task)
        task.add_done_callback(lambda t: agent._buffer_tasks.discard(t))

    disconnected_event = asyncio.Event()

    @ctx.room.on("disconnected")
    def _on_room_disconnected(*args, **kwargs):
        disconnected_event.set()

    try:
        try:
            agent.interviewee_username = await asyncio.to_thread(agent._load_interviewee_username)
            participant_identity = agent.interviewee_username
        except Exception as e:
            print(f"[SYSTEM] failed to load interviewee username before start: {e}")

        room_options = _room_options_for_session(
            text_input_cb=text_input_cb,
            text_only=text_only,
            participant_identity=participant_identity,
        )
        logger.info(
            "session room_options room=%s text_only=%s participant_identity=%r "
            "close_on_disconnect=%s",
            room_name,
            text_only,
            participant_identity or None,
            room_options.close_on_disconnect,
        )

        await session.start(room=ctx.room, agent=agent, room_options=room_options)

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
    try:
        agents.cli.run_app(server)
    finally:
        # Dev-only: wiping the DB on agent exit breaks harness / evaluation runs.
        if os.getenv("NOAH_CLEAN_DB_ON_AGENT_EXIT", "").strip() in ("1", "true", "yes"):
            from seeder import clean_database

            clean_database()
