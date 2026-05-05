import asyncio
import threading
import os
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, TurnHandlingOptions
from livekit.plugins import silero, openai, deepgram, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from seeder import reset_and_seed, clean_database
from http_api import app as fastapi_app

load_dotenv(".env.local", override=True)

print("--- STARTING WITH URL:", os.getenv("LIVEKIT_URL"), "---")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant called Noah.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )


server = AgentServer()


@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            interruption={"enabled": False},
        ),
    )

    disconnected_event = asyncio.Event()

    @ctx.room.on("disconnected")
    def _on_room_disconnected(*args, **kwargs):
        disconnected_event.set()

    try:
        await session.start(room=ctx.room, agent=Assistant())
        await session.generate_reply(
            instructions="Greet the user and offer your assistance."
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
