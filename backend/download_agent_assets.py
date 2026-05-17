"""
Pre-download LiveKit plugin models during Docker build.

Usage (from backend/):
    python download_agent_assets.py
"""

from __future__ import annotations

# Import plugins used by interviewer.py so they register with Plugin.registered_plugins.
from livekit.plugins import elevenlabs, groq, openai, silero  # noqa: F401
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # noqa: F401

from livekit.agents.plugin import Plugin


def main() -> None:
    if not Plugin.registered_plugins:
        raise RuntimeError("No LiveKit plugins registered; check imports above.")

    for plugin in Plugin.registered_plugins:
        print(f"Downloading files for {plugin.package}...")
        plugin.download_files()
        print(f"Finished {plugin.package}")


if __name__ == "__main__":
    main()
