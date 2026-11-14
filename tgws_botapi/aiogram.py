"""SOCKS5 transport for the standard Telegram Bot API in aiogram 3.

This transport does not start a local Telegram Bot API server or use TDLib.
It only requires a reachable SOCKS5 exit node and the bot token.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit


def resolve_socks5_url(proxy_url: str | None = None) -> str:
    """Require an explicit SOCKS5 endpoint; never silently fall back to direct."""
    value = proxy_url if proxy_url is not None else os.getenv("TGWS_SOCKS5_URL", "")
    value = value.strip()
    if not value:
        raise ValueError("TGWS_SOCKS5_URL is required when SOCKS5 transport is enabled")

    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("SOCKS5 proxy URL must contain a valid port") from exc

    if parsed.scheme.lower() != "socks5" or not parsed.hostname or port is None:
        raise ValueError("SOCKS5 proxy URL must look like socks5://host:port")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("SOCKS5 proxy URL cannot contain a path, query or fragment")
    return value


def aiogram_session(*, proxy_url: str | None = None):
    """Create a fail-closed aiogram session proxied to api.telegram.org."""
    try:
        from aiogram.client.session.aiohttp import AiohttpSession
    except ImportError as exc:
        raise RuntimeError(
            "aiogram is required: pip install 'tgws-botapi[aiogram]'"
        ) from exc

    return AiohttpSession(proxy=resolve_socks5_url(proxy_url))


def create_aiogram_bot(token: str, *, proxy_url: str | None = None):
    """Drop-in constructor; no API_ID, API_HASH or local Bot API required."""
    from aiogram import Bot

    return Bot(token=token, session=aiogram_session(proxy_url=proxy_url))
