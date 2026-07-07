from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
from pathlib import Path

from .app import YueCore
from .config import load_settings
from .desktop_demo import launch_tk_desktop_demo, run_desktop_headless_smoke_test
from .transport import JsonLineServer
from .version import VERSION
from .contracts import CORE_API_VERSION


def _write_stdout_text(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        payload = f"{text}\n".encode("utf-8", errors="replace")
        buffer = getattr(sys.stdout, "buffer", None)
        if buffer is None:
            sys.stdout.write(payload.decode("utf-8", errors="replace"))
        else:
            buffer.write(payload)
            buffer.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yue-core")
    parser.add_argument("--config", type=Path, help="Path to a TOML configuration file")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    subparsers.add_parser("list-tools")
    invoke = subparsers.add_parser("invoke")
    invoke.add_argument("tool")
    argument_source = invoke.add_mutually_exclusive_group()
    argument_source.add_argument("--arguments", default="{}", help="JSON object")
    argument_source.add_argument(
        "--arguments-file",
        type=Path,
        help="Read the JSON argument object from a UTF-8 file",
    )
    chat = subparsers.add_parser("chat")
    chat.add_argument("text")
    chat.add_argument("--provider")
    chat.add_argument("--provider-role", default="chat")
    subparsers.add_parser("providers-health")
    subparsers.add_parser("serve")
    desktop_demo = subparsers.add_parser("desktop-demo")
    desktop_demo.add_argument(
        "--headless-smoke-test",
        action="store_true",
        help="Exercise the desktop demo controller without opening windows",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    if args.command == "doctor":
        print(
            json.dumps(
                {
                    "status": "ok",
                    "version": VERSION,
                    "core_api": CORE_API_VERSION,
                    "python": sys.version,
                    "platform": platform.platform(),
                    "data_dir": str(settings.core.data_dir),
                    "permission_profile": settings.permissions.profile,
                    "plugins_enabled": settings.plugins.enabled,
                    "conversation_store": settings.conversation.store_backend,
                    "default_provider": settings.conversation.default_provider,
                    "conversation_routes": settings.conversation.routes,
                    "prompt_profiles": sorted(
                        settings.conversation.prompt_profiles.keys()
                    ),
                    "desktop_hotkey": settings.desktop.hotkey,
                    "desktop_window_anchor": settings.desktop.window_anchor,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "desktop-demo" and args.headless_smoke_test:
        print(
            json.dumps(
                run_desktop_headless_smoke_test(settings),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return 0

    core = YueCore(settings)
    if args.command == "serve":
        await JsonLineServer(core).serve()
        return 0

    async with core:
        if args.command == "list-tools":
            for spec in core.registry.list_specs():
                print(f"{spec.name}\t{spec.capability.value}\t{spec.risk.value}")
            return 0
        if args.command == "providers-health":
            print(json.dumps(await core.providers.health(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "invoke":
            raw_arguments = (
                args.arguments_file.read_text(encoding="utf-8")
                if args.arguments_file is not None
                else args.arguments
            )
            arguments = json.loads(raw_arguments)
            if not isinstance(arguments, dict):
                raise ValueError("--arguments must decode to a JSON object")
            result = await core.invoke(args.tool, arguments)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
            return 0 if result.ok else 1
        if args.command == "chat":
            conversation = await core.conversations.create(title="CLI chat")
            assistant = await core.conversations.send(
                conversation.id,
                args.text,
                provider_name=args.provider,
                provider_role=args.provider_role,
                actor="cli",
            )
            _write_stdout_text(assistant.content)
            return 0
    if args.command == "desktop-demo":
        launch_tk_desktop_demo(settings)
        return 0
    return 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
