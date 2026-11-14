"""Minimal aiogram 3 bot for verifying the managed runtime."""

from __future__ import annotations

import asyncio
import os

from aiogram import Dispatcher, F
from aiogram.types import Message

from tgws_botapi.aiogram import create_aiogram_bot


async def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not configured")

    bot = create_aiogram_bot(token)
    dispatcher = Dispatcher()

    @dispatcher.message(F.text)
    async def echo(message: Message) -> None:
        await message.answer(message.text)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
