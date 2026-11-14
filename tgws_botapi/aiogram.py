"""Opt-in aiogram 3 session pointing at the local Bot API runtime."""

from __future__ import annotations

import os

DEFAULT_API_URL = "http://127.0.0.1:8081"


def aiogram_session(*, api_url: str | None = None):
    """Create an aiogram session for the managed local Bot API server.

    Install the library from GitHub (or from a published wheel) with aiogram.
    This function does not start the runtime; use ``tgws-botapi run`` or
    ``GatewayRuntime`` for that.
    """
    try:
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.telegram import TelegramAPIServer
    except ImportError as exc:
        raise RuntimeError(
            "aiogram is required: pip install 'tgws-botapi[aiogram]'"
        ) from exc

    base = (api_url or os.environ.get("TGWS_BOT_API_URL") or DEFAULT_API_URL).rstrip("/")
    if not (base.startswith("http://") or base.startswith("https://")):
        raise ValueError("Bot API URL must begin with http:// or https://")
    return AiohttpSession(api=TelegramAPIServer.from_base(base, is_local=True))


def create_aiogram_bot(token: str, *, api_url: str | None = None):
    """Drop-in constructor replacing ``aiogram.Bot(token=...)``."""
    from aiogram import Bot

    return Bot(token=token, session=aiogram_session(api_url=api_url))
