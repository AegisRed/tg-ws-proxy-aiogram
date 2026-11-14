"""SOCKS5 transport tests without real network access or Telegram credentials."""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from tgws_botapi.aiogram import (
    aiogram_session,
    create_aiogram_bot,
    resolve_socks5_url,
)


class Socks5AdapterTests(unittest.TestCase):
    def test_proxy_url_from_environment(self):
        with patch.dict(os.environ, {"TGWS_SOCKS5_URL": "socks5://localhost:1080"}):
            self.assertEqual(resolve_socks5_url(), "socks5://localhost:1080")

    def test_explicit_url_overrides_environment(self):
        with patch.dict(os.environ, {"TGWS_SOCKS5_URL": "socks5://wrong:1080"}):
            session = aiogram_session(proxy_url="socks5://proxy.example:1081")
        self.assertEqual(session.proxy, "socks5://proxy.example:1081")
        self.assertFalse(session.api.is_local)

    def test_missing_proxy_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TGWS_SOCKS5_URL"):
                aiogram_session()

    def test_rejects_bad_proxy_urls(self):
        invalid = [
            "http://proxy.example:3128",
            "socks5://host",
            "socks5://:1080",
            "socks5://host:not-a-port",
            "socks5://host:1080/other-path",
            "socks5://host:1080?password=leak",
        ]
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                resolve_socks5_url(url)

    def test_authenticated_proxy_does_not_expose_credentials_in_error(self):
        url = "socks5://user:secret@proxy.example:1080"
        self.assertEqual(resolve_socks5_url(url), url)
        with self.assertRaises(ValueError) as caught:
            resolve_socks5_url("socks5://user:secret@proxy.example:nope")
        self.assertNotIn("secret", str(caught.exception))

    def test_bot_keeps_cloud_api_and_socks5_connector(self):
        bot = create_aiogram_bot(
            "123456:TEST_TOKEN",
            proxy_url="socks5://127.0.0.1:1080",
        )
        try:
            self.assertFalse(bot.session.api.is_local)
            self.assertIn("api.telegram.org", bot.session.api.base)
            self.assertEqual(bot.session.proxy, "socks5://127.0.0.1:1080")
        finally:
            asyncio.run(bot.session.close())


if __name__ == "__main__":
    unittest.main()
