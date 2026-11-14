"""aiogram SOCKS5 adapter, with optional legacy MTProto runtime."""

from .runtime import GatewayRuntime, GatewaySettings, GatewayStartupError

__version__ = "0.2.0"

__all__ = ["GatewayRuntime", "GatewaySettings", "GatewayStartupError", "__version__"]
