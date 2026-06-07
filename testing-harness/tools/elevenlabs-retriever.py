import json
from pathlib import Path

from elevenlabs import ElevenLabs

from interviewees.env import require_env

client = ElevenLabs(api_key=require_env("ELEVENLABS_API_KEY"))

conversations = ["conv_9501ktek6r66eb6v55nc0360ne2g", "conv_3901ktekbw55f06avmks3xb49f8q", "conv_0001ktekg5y0f5xahv209hpqh8s3", "conv_5301ktekn50sehjsfg4ddaqnw8c5"]


def get_information(conv_id: str, label: str) -> None:
    conversation = client.conversational_ai.conversations.get(
        conversation_id=conv_id,
    )

    out_dir = Path("results/elevenlabs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{label}.json"

    transcript = [
        {"role": turn.role, "message": turn.message}
        for turn in conversation.transcript
    ]
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(transcript, file, indent=2, ensure_ascii=False)
        file.write("\n")


for index, conv_id in enumerate(conversations):
    get_information(conv_id, chr(ord("A") + index))