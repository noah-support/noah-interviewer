"""Redis URL helpers for local redis:// and TLS rediss:// (e.g. Northflank addons)."""

from __future__ import annotations

import os
import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import redis

_CELERY_SSL_PARAM_VALUES = frozenset({"CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"})

_SSL_ALIASES: dict[str, int] = {
    "cert_required": ssl.CERT_REQUIRED,
    "required": ssl.CERT_REQUIRED,
    "cert_optional": ssl.CERT_OPTIONAL,
    "optional": ssl.CERT_OPTIONAL,
    "cert_none": ssl.CERT_NONE,
    "none": ssl.CERT_NONE,
}


def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def is_rediss(url: str | None = None) -> bool:
    return urlparse(url or redis_url()).scheme == "rediss"


def ssl_cert_reqs() -> ssl.VerifyMode:
    """ssl.CERT_* value for redis-py clients."""
    raw = os.getenv("REDIS_SSL_CERT_REQS", "CERT_REQUIRED").strip()
    key = raw.lower().replace("-", "_")
    if key in _SSL_ALIASES:
        return _SSL_ALIASES[key]
    upper = raw.upper()
    if upper in _SSL_ALIASES:
        return _SSL_ALIASES[upper.lower()]
    raise ValueError(
        f"Invalid REDIS_SSL_CERT_REQS={raw!r}; "
        "use CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE, or required/optional/none"
    )


def celery_ssl_cert_reqs_param() -> str:
    """Query-string value required by Celery/kombu for rediss:// URLs."""
    raw = os.getenv("REDIS_SSL_CERT_REQS", "CERT_REQUIRED").strip().upper()
    if raw in _CELERY_SSL_PARAM_VALUES:
        return raw
    alias = {
        "REQUIRED": "CERT_REQUIRED",
        "OPTIONAL": "CERT_OPTIONAL",
        "NONE": "CERT_NONE",
    }.get(raw)
    if alias:
        return alias
    raise ValueError(
        f"Invalid REDIS_SSL_CERT_REQS={raw!r}; "
        "use CERT_REQUIRED, CERT_OPTIONAL, or CERT_NONE"
    )


def normalize_redis_url_for_celery(url: str) -> str:
    """
    Celery's Redis backend requires ssl_cert_reqs on rediss:// URLs.
    Northflank addon URLs often omit it.
    """
    parsed = urlparse(url)
    if parsed.scheme != "rediss":
        return url

    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "ssl_cert_reqs" not in qs:
        qs["ssl_cert_reqs"] = [celery_ssl_cert_reqs_param()]

    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))


def redis_client(**kwargs: object) -> redis.Redis:
    """redis.Redis client with TLS options when REDIS_URL uses rediss://."""
    url = redis_url()
    if is_rediss(url):
        kwargs.setdefault("ssl_cert_reqs", ssl_cert_reqs())
    return redis.from_url(url, decode_responses=True, **kwargs)
