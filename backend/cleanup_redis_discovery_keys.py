#!/usr/bin/env python3
"""
Remove stale LiveKit interview discovery keys from Redis (lk:bpmn:state:*, lk:bpmn:buf:*).

These keys are normally deleted when an interview ends cleanly; abrupt exits (killed agent,
browser closed, etc.) can leave them behind until TTL (default 48h, see BPMN_REDIS_TTL_S).

Uses REDIS_URL (default redis://localhost:6379/0), same as bpmn_redis / Celery.

Examples:
  cd backend && source .venv/bin/activate
  python cleanup_redis_discovery_keys.py --dry-run
  python cleanup_redis_discovery_keys.py --execute
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    _here = Path(__file__).resolve().parent
    load_dotenv(_here / ".env.local")
    load_dotenv(_here / ".env")
except ImportError:
    pass

import redis


STATE_PREFIX = "lk:bpmn:state:"
BUF_PREFIX = "lk:bpmn:buf:"


def _client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


def _scan_keys(r: redis.Redis, pattern: str) -> list[str]:
    out: list[str] = []
    for key in r.scan_iter(match=pattern, count=500):
        if isinstance(key, bytes):
            key = key.decode("utf-8", errors="replace")
        if isinstance(key, str):
            out.append(key)
    out.sort()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete stale Redis keys for interview discovery state / transcript buffer.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List keys that would be deleted (default if neither flag is set).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete the keys.",
    )
    args = parser.parse_args()

    if args.execute and args.dry_run:
        print("Use only one of --dry-run or --execute.", file=sys.stderr)
        return 2

    dry_run = not args.execute

    r = _client()
    try:
        r.ping()
    except redis.RedisError as e:
        print(f"Redis unavailable ({e}). Check REDIS_URL.", file=sys.stderr)
        return 1

    state_keys = _scan_keys(r, f"{STATE_PREFIX}*")
    buf_keys = _scan_keys(r, f"{BUF_PREFIX}*")
    all_keys = sorted(set(state_keys) | set(buf_keys))

    if not all_keys:
        print("No lk:bpmn:state:* or lk:bpmn:buf:* keys found.")
        return 0

    print(f"Found {len(state_keys)} state key(s), {len(buf_keys)} buffer key(s), {len(all_keys)} unique key(s) total.")
    for k in all_keys:
        print(f"  {k}")

    if dry_run:
        print("\nDry run only. Re-run with --execute to delete these keys.")
        return 0

    # Delete in batches (avoid huge single DELETE on some servers)
    batch = 500
    deleted = 0
    for i in range(0, len(all_keys), batch):
        chunk = all_keys[i : i + batch]
        deleted += int(r.delete(*chunk))
    print(f"\nDeleted {deleted} key(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
