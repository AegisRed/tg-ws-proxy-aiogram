"""Offline unit tests for the bundled runtime. No Telegram credentials needed."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tgws_botapi.aiogram import aiogram_session
from tgws_botapi.runtime import GatewayRuntime, GatewaySettings, GatewayStartupError


class FakeProcess:
    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class GatewaySettingsTests(unittest.TestCase):
    def test_env_creates_secret_without_exposing_it_in_repr(self):
        settings = GatewaySettings.from_env({
            "TELEGRAM_API_ID": "1234",
            "TELEGRAM_API_HASH": "not_a_real_api_hash",
        })
        self.assertEqual(settings.api_id, 1234)
        self.assertEqual(len(settings.proxy_secret), 32)
        self.assertNotIn(settings.api_hash, repr(settings))
        self.assertNotIn(settings.proxy_secret, repr(settings))
        self.assertFalse(settings.allow_direct_fallback)

    def test_rejects_invalid_settings(self):
        with self.assertRaises(ValueError):
            GatewaySettings.from_env({})
        with self.assertRaises(ValueError):
            GatewaySettings(api_id=1, api_hash="hash", proxy_secret="nothex")
        with self.assertRaises(ValueError):
            GatewaySettings(api_id=1, api_hash="hash", host="0.0.0.0")
        with self.assertRaises(ValueError):
            GatewaySettings(api_id=1, api_hash="hash", proxy_port=8081, bot_api_port=8081)

    def test_aiogram_adapter_uses_local_bot_api_endpoint(self):
        session = aiogram_session(api_url="http://127.0.0.1:8081/")
        self.assertEqual(
            session.api.api_url(token="123:abc", method="getMe"),
            "http://127.0.0.1:8081/bot123:abc/getMe",
        )
        self.assertTrue(session.api.is_local)


class GatewayRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = GatewaySettings(
            api_id=1234, api_hash="not_a_real_api_hash",
            proxy_secret="ab" * 16,
            data_dir=Path(self.tmp.name),
        )

    def test_start_starts_proxy_before_bot_api_and_disables_direct_fallback(self):
        components = [FakeProcess(), FakeProcess()]
        gateway = GatewayRuntime(self.settings)
        with mock.patch("shutil.which", return_value="/usr/bin/telegram-bot-api"), \
                mock.patch("subprocess.Popen", side_effect=components) as popen, \
                mock.patch.object(GatewayRuntime, "_wait_for_port") as ready:
            gateway.start()
            self.assertEqual(ready.call_count, 2)
            proxy_command = popen.call_args_list[0].args[0]
            api_command = popen.call_args_list[1].args[0]
            self.assertIn("--no-direct-fallback", proxy_command)
            self.assertIn("--tdlib-proxy-type=mtproto", api_command)
            self.assertIn("--proxy-secret=dd" + self.settings.proxy_secret, api_command)
            self.assertIn("--http-ip-address=127.0.0.1", api_command)
            self.assertEqual(
                popen.call_args_list[1].kwargs["env"]["TELEGRAM_API_HASH"],
                self.settings.api_hash,
            )
            gateway.check_running()
            gateway.stop()
        self.assertTrue(all(component.terminated for component in components))

    def test_missing_bot_api_binary_fails_before_launching(self):
        gateway = GatewayRuntime(self.settings)
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(GatewayStartupError, "not found"):
                gateway.start()

    def test_direct_fallback_is_opt_in(self):
        settings = GatewaySettings(
            api_id=1234, api_hash="hash", allow_direct_fallback=True,
            data_dir=Path(self.tmp.name),
        )
        gateway = GatewayRuntime(settings)
        with mock.patch("shutil.which", return_value="telegram-bot-api"), \
                mock.patch("subprocess.Popen", side_effect=[FakeProcess(), FakeProcess()]) as popen, \
                mock.patch.object(GatewayRuntime, "_wait_for_port"):
            gateway.start()
            self.assertNotIn("--no-direct-fallback", popen.call_args_list[0].args[0])
            gateway.stop()

    def test_bot_inherits_local_endpoint(self):
        gateway = GatewayRuntime(self.settings)
        gateway._processes = [FakeProcess(), FakeProcess()]
        with mock.patch("subprocess.Popen", return_value=FakeProcess(0)) as popen:
            self.assertEqual(gateway.run_bot(["python", "bot.py"]), 0)
            self.assertEqual(
                popen.call_args.kwargs["env"]["TGWS_BOT_API_URL"],
                "http://127.0.0.1:8081",
            )

    def test_failed_start_cleans_up_started_proxy(self):
        proxy = FakeProcess()
        gateway = GatewayRuntime(self.settings)
        with mock.patch("shutil.which", return_value="telegram-bot-api"), \
                mock.patch("subprocess.Popen", return_value=proxy), \
                mock.patch.object(GatewayRuntime, "_wait_for_port", side_effect=GatewayStartupError("bad")):
            with self.assertRaises(GatewayStartupError):
                gateway.start()
        self.assertTrue(proxy.terminated)


if __name__ == "__main__":
    unittest.main()
