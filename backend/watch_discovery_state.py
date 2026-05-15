"""
Live terminal view of the discovery state manager JSON in Redis.

Run from the backend directory (second terminal) while an interview is active:

    cd backend
    python watch_discovery_state.py --room interview-42-a1b2c3d4

Room names look like `interview-{id}-{8 hex chars}` (from the livekit-token API). Use that exact string.
Environment: REDIS_URL (default redis://localhost:6379/0), same as the agent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BACKEND_DIR, ".env.local"), override=True)
sys.path.insert(0, _BACKEND_DIR)

from bpmn_redis import buf_key, state_key  # noqa: E402


def _clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _pretty(raw: str | None) -> str:
    if not raw or not raw.strip():
        return "(no state key yet — waiting for agent to join this room)\n"
    try:
        data = json.loads(raw)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch lk:bpmn:state Redis JSON for a room.")
    parser.add_argument(
        "--room",
        required=True,
        help="LiveKit room name, e.g. interview-1-a1b2c3d4",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Poll interval in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear the screen; print updates when JSON changes only",
    )
    parser.add_argument(
        "--show-buffer",
        action="store_true",
        help="Also show transcript buffer length (lk:bpmn:buf)",
    )
    args = parser.parse_args()

    import redis

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(url, decode_responses=True)

    room = args.room.strip()
    sk = state_key(room)
    bk = buf_key(room)

    last_payload: str | None = None

    try:
        while True:
            raw = r.get(sk)
            if not isinstance(raw, str):
                raw = None

            buf_len = int(r.llen(bk)) if args.show_buffer else 0

            if args.no_clear:
                payload = raw or ""
                if payload != last_payload:
                    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
                    print(f"\n--- {ts} UTC ---\n{_pretty(raw)}", flush=True)
                    if args.show_buffer:
                        print(f"buffer_lines: {buf_len}\n", flush=True)
                    last_payload = payload
            else:
                _clear_screen()
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                print(f"Redis discovery state  |  room={room!r}\nkey={sk}\nupdated view: {ts}\n")
                print(_pretty(raw))
                if args.show_buffer:
                    print(f"\n--- transcript buffer ({bk}) ---\nlines: {buf_len}")
                print(f"\nPoll every {args.interval}s  ·  Ctrl+C to exit", flush=True)

            time.sleep(max(0.1, args.interval))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
