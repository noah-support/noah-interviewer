import os
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, TurnHandlingOptions
# Import the specific plugins
from livekit.plugins import silero, openai, deepgram, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local", override=True)

print('--- STARTING WITH URL:', os.getenv('LIVEKIT_URL'), '---')

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant called Noah.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

server = AgentServer()

# Omit agent_name so LiveKit uses automatic dispatch for each room. If you set
# agent_name="noah", you MUST dispatch explicitly (API / lk dispatch / agent in JWT).
@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # 1. Connect to the local Docker room
    await ctx.connect()

    # 2. Use the direct plugins instead of the Inference Gateway strings!
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"), # Changed to a real OpenAI model
        tts=cartesia.TTS(voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
        ),
    )

    # Optional: Print to the terminal so we can literally see the AI thinking
    @session.on("agent_speech_committed")
    def on_speech(msg):
        print(f"\n🗣️ NOAH SAYS: {msg.content}\n")

    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)