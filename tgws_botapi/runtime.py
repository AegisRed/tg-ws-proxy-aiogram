"""Supervise the embedded MTProto WS bridge and a proxy-enabled Bot API binary.

The Bot API binary is *not* supplied by the Python wheel. It must implement
TDLib MTProto proxy flags (``--tdlib-proxy-type`` and friends). The Docker
runtime image includes such a binary; use ``TGWS_BOTAPI_BINARY`` otherwise.
"""

from __future__ import annotations

import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


class GatewayStartupError(RuntimeError):
    """An embedded component could not be started or became unhealthy."""


@dataclass(frozen=True)
class GatewaySettings:
    api_id: int
    api_hash: str = field(repr=False)
    proxy_secret: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)
    proxy_port: int = 1443
    bot_api_port: int = 8081
    host: str = "127.0.0.1"
    data_dir: Path = Path(".tgws-data")
    bot_api_binary: str = "telegram-bot-api"
    allow_direct_fallback: bool = False
    cfproxy_domains: tuple[str, ...] = ()
    startup_timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.api_id <= 0 or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
        if len(self.proxy_secret) != 32:
            raise ValueError("TGWS_SECRET must contain exactly 32 hex digits")
        try:
            bytes.fromhex(self.proxy_secret)
        except ValueError as exc:
            raise ValueError("TGWS_SECRET is not hexadecimal") from exc
        for port in (self.proxy_port, self.bot_api_port):
            if not 1 <= port <= 65535:
                raise ValueError("Ports must be between 1 and 65535")
        if self.proxy_port == self.bot_api_port:
            raise ValueError("Proxy and Bot API ports cannot be the same")
        if self.host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("Embedded runtime may bind only to loopback")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> GatewaySettings:
        values = os.environ if env is None else env
        api_id = values.get("TELEGRAM_API_ID", "")
        if not api_id.isdecimal():
            raise ValueError("Set TELEGRAM_API_ID to a positive integer")
        try:
            proxy_port = int(values.get("TGWS_PROXY_PORT", "1443"))
            bot_api_port = int(values.get("TGWS_BOT_API_PORT", "8081"))
        except ValueError as exc:
            raise ValueError("TGWS_PROXY_PORT and TGWS_BOT_API_PORT must be integers") from exc
        return cls(
            api_id=int(api_id),
            api_hash=values.get("TELEGRAM_API_HASH", ""),
            proxy_secret=values.get("TGWS_SECRET") or secrets.token_hex(16),
            proxy_port=proxy_port,
            bot_api_port=bot_api_port,
            data_dir=Path(values.get("TGWS_DATA_DIR", ".tgws-data")),
            bot_api_binary=values.get("TGWS_BOTAPI_BINARY", "telegram-bot-api"),
            allow_direct_fallback=values.get("TGWS_ALLOW_DIRECT_FALLBACK", "false").lower()
            in ("1", "true", "yes"),
            cfproxy_domains=tuple(filter(None, values.get("TGWS_CFPROXY_DOMAINS", "").replace(",", " ").split())),
        )

    @property
    def bot_api_url(self) -> str:
        host = "[::1]" if self.host == "::1" else self.host
        return f"http://{host}:{self.bot_api_port}"


class GatewayRuntime:
    """Start/stop both local services without depending on a GUI."""

    def __init__(self, settings: GatewaySettings):
        self.settings = settings
        self._processes: list[subprocess.Popen] = []

    def __enter__(self) -> GatewayRuntime:
        self.start()
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.stop()

    def _wait_for_port(self, process: subprocess.Popen, port: int) -> None:
        deadline = time.monotonic() + self.settings.startup_timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise GatewayStartupError(f"Gateway component exited with code {process.returncode}")
            try:
                with socket.create_connection((self.settings.host, port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        raise GatewayStartupError(f"Gateway component did not listen on {port} in time")

    def start(self) -> None:
        if self._processes:
            raise GatewayStartupError("Gateway is already running")
        cfg = self.settings
        executable = shutil.which(cfg.bot_api_binary)
        if executable is None:
            raise GatewayStartupError(
                "Proxy-enabled telegram-bot-api executable not found. "
                "Use the supplied Docker image or set TGWS_BOTAPI_BINARY."
            )

        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        proxy_cmd = [
            sys.executable, "-m", "proxy.tg_ws_proxy", "--host", cfg.host,
            "--port", str(cfg.proxy_port), "--secret", cfg.proxy_secret,
        ]
        if not cfg.allow_direct_fallback:
            proxy_cmd.append("--no-direct-fallback")
        for domain in cfg.cfproxy_domains:
            proxy_cmd.extend(("--cfproxy-domain", domain))

        api_cmd = [
            executable,
            "--local",
            f"--http-port={cfg.bot_api_port}",
            f"--http-ip-address={cfg.host}",
            f"--dir={cfg.data_dir.resolve()}",
            "--tdlib-proxy-type=mtproto",
            f"--proxy-server={cfg.host}",
            f"--proxy-port={cfg.proxy_port}",
            f"--proxy-secret=dd{cfg.proxy_secret}",
        ]
        api_env = os.environ.copy()
        api_env["TELEGRAM_API_ID"] = str(cfg.api_id)
        api_env["TELEGRAM_API_HASH"] = cfg.api_hash
        try:
            proxy = subprocess.Popen(proxy_cmd)
            self._processes.append(proxy)
            self._wait_for_port(proxy, cfg.proxy_port)
            bot_api = subprocess.Popen(api_cmd, env=api_env)
            self._processes.append(bot_api)
            self._wait_for_port(bot_api, cfg.bot_api_port)
        except BaseException:
            self.stop()
            raise

    def check_running(self) -> None:
        if len(self._processes) != 2:
            raise GatewayStartupError("Gateway is not running")
        for component in self._processes:
            if component.poll() is not None:
                raise GatewayStartupError(
                    f"Gateway component stopped unexpectedly (code {component.returncode})"
                )

    def bot_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["TGWS_BOT_API_URL"] = self.settings.bot_api_url
        return env

    def run_bot(self, command: Sequence[str]) -> int:
        if not command:
            raise ValueError("Bot command is required")
        self.check_running()
        bot = subprocess.Popen(command, env=self.bot_environment())
        try:
            while bot.poll() is None:
                self.check_running()
                time.sleep(0.25)
            return bot.returncode
        finally:
            if bot.poll() is None:
                bot.terminate()
                try:
                    bot.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    bot.kill()
                    bot.wait()

    def stop(self) -> None:
        processes, self._processes = self._processes[::-1], []
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
