"""CLI for running an existing Python bot with the bundled local gateway."""

from __future__ import annotations

import argparse
import signal
import sys

from .runtime import GatewayRuntime, GatewaySettings, GatewayStartupError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telegram Bot API over MTProto WebSocket")
    actions = parser.add_subparsers(dest="action", required=True)
    runner = actions.add_parser("run", help="Run your bot with a managed local Bot API")
    runner.add_argument("command", nargs=argparse.REMAINDER, help="-- python bot.py")
    args = parser.parse_args(argv)

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("Specify bot command after -- (example: run -- python bot.py)")

    # The wrapper is PID 1 in Docker. Forward normal container shutdown through
    # the runtime context manager so both local servers and the bot are reaped.
    previous_sigterm = signal.getsignal(signal.SIGTERM)

    def _handle_sigterm(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        with GatewayRuntime(GatewaySettings.from_env()) as gateway:
            return gateway.run_bot(command)
    except KeyboardInterrupt:
        return 130
    except (GatewayStartupError, ValueError, OSError) as exc:
        print(f"tgws-botapi: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    raise SystemExit(main())
