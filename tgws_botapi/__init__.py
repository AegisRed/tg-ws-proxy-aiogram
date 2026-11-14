"""Headless Telegram Bot API runtime backed by the Flowseal WS transport."""

from .runtime import GatewayRuntime, GatewaySettings, GatewayStartupError

__version__ = "0.1.0"

__all__ = ["GatewayRuntime", "GatewaySettings", "GatewayStartupError", "__version__"]
