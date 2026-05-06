import asyncio
import json
import re
import threading
import os
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
        super().__init__(
            instructions="""You are an AI consultant interviewer called Noah. Your goal is to deeply understand how an employee works — their role, daily tasks, knowledge, expertise, strengths, personal interests, frustrations, bottlenecks, and future ambitions — so that later we can identify opportunities for automation or AI assistance.""",
            chat_ctx=ChatContext(),
        )

    def _enqueue_summary_job(self) -> None:
        transcript_json = json.dumps(self.chat_ctx.to_dict(), ensure_ascii=False)
        summarize_interview_turns.delay(
            interview_id=self.interview_id,
            transcript_json=transcript_json,
        )

    async def on_enter(self) -> None:
        print(f"[SYSTEM] setup complete | id: {self.interview_id} | counter: {self.turn_counter}")
        return await super().on_enter()

    async def on_exit(self) -> None:
        try:
            self._enqueue_summary_job()
            print("[SYSTEM] summary job enqueued")
        except Exception as e:
            print(f"[SYSTEM] failed to enqueue summary job: {e}")
        return await super().on_exit()
    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage) -> None:
        self.turn_counter += 1
        print(f"[SYSTEM] add turn counter: turncounter = {self.turn_counter}")
        # start job if above SUMMARY_AMOUNT amount
        summary_every = int(os.getenv("SUMMARY_AMOUNT", "5"))
        if self.turn_counter >= summary_every:
            try:
                self._enqueue_summary_job()
                print("[SYSTEM] periodic summary job enqueued")
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
            instructions="Greet the user and give an introduction of who you are and what you do."
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
