from __future__ import annotations

import copy
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .errors import ConfigurationError


DEFAULT_CHAT_PROMPT_PROFILE = {
    "personality": "Local-first assistant. Short, clear, and practical.",
    "system_instruction": "",
    "tool_instruction": "Only call tools when they materially improve the answer or are explicitly requested.",
    "response_instruction": "Keep answers concise and preserve the user's language.",
}

DEFAULT_CODING_PROMPT_PROFILE = {
    "personality": "Senior coding agent. Direct, technical, and execution-focused.",
    "system_instruction": "You are responsible for implementing code changes safely and validating them with real checks.",
    "tool_instruction": (
        "Inspect relevant files before editing. Prefer targeted reads/searches first, then edit only what is needed. "
        "When several independent read-only inspections are needed, call multiple read tools in the same turn. "
        "Keep writes, edits, and shell actions sequential unless the tools explicitly indicate parallel safety. "
        "Run verification commands when they materially prove the change. Avoid destructive actions unless explicitly requested."
    ),
    "response_instruction": "State assumptions, verification, and remaining risks clearly.",
}


@dataclass(slots=True)
class CoreSettings:
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    tool_timeout_seconds: float = 30.0


@dataclass(slots=True)
class PermissionSettings:
    profile: str = "observe"
    interactive_approval: bool = False


@dataclass(slots=True)
class PluginSettings:
    roots: list[Path] = field(default_factory=lambda: [Path("plugins")])
    enabled: list[str] = field(default_factory=list)
    options: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(slots=True)
class ConversationSettings:
    default_provider: str = "fake.echo"
    routes: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            "chat": {"provider": "fake.echo", "prompt_profile": "default"},
            "coding_agent": {
                "provider": "fake.echo",
                "prompt_profile": "coding_agent",
            },
        }
    )
    prompt_profiles: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            "default": dict(DEFAULT_CHAT_PROMPT_PROFILE),
            "coding_agent": dict(DEFAULT_CODING_PROMPT_PROFILE),
        }
    )
    store_backend: str = "sqlite"
    sqlite_path: Path = Path("conversations.db")
    max_tool_iterations: int = 4
    max_tool_output_chars: int = 12000


@dataclass(slots=True)
class DesktopSettings:
    hotkey: str = "Ctrl+Shift+Y"
    window_anchor: str = "bottom-right"
    model_path: str | None = None
    click_opens_console: bool = True


@dataclass(slots=True)
class Settings:
    core: CoreSettings = field(default_factory=CoreSettings)
    permissions: PermissionSettings = field(default_factory=PermissionSettings)
    plugins: PluginSettings = field(default_factory=PluginSettings)
    conversation: ConversationSettings = field(default_factory=ConversationSettings)
    desktop: DesktopSettings = field(default_factory=DesktopSettings)
    config_path: Path | None = None


DEFAULTS: dict[str, Any] = {
    "core": {
        "data_dir": "data",
        "log_level": "INFO",
        "tool_timeout_seconds": 30.0,
    },
    "permissions": {
        "profile": "observe",
        "interactive_approval": False,
    },
    "plugins": {
        "roots": ["plugins"],
        "enabled": [],
        "options": {},
    },
    "conversation": {
        "default_provider": "fake.echo",
        "routes": {
            "chat": {"provider": "fake.echo", "prompt_profile": "default"},
            "coding_agent": {
                "provider": "fake.echo",
                "prompt_profile": "coding_agent",
            },
        },
        "prompt_profiles": {
            "default": dict(DEFAULT_CHAT_PROMPT_PROFILE),
            "coding_agent": dict(DEFAULT_CODING_PROMPT_PROFILE),
        },
        "store_backend": "sqlite",
        "sqlite_path": "data/conversations.db",
        "max_tool_iterations": 4,
        "max_tool_output_chars": 12000,
    },
    "desktop": {
        "hotkey": "Ctrl+Shift+Y",
        "window_anchor": "bottom-right",
        "model_path": None,
        "click_opens_console": True,
    },
}


def _deep_merge(target: dict[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def _string_table(
    value: Mapping[str, Any],
    *,
    field_name: str,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(item, (str, int, float, bool)) and item is not None:
            raise ValueError(f"{field_name}.{key} must be a scalar string value")
        result[str(key)] = "" if item is None else str(item)
    return result


def _conversation_routes(
    raw_conversation: Mapping[str, Any],
    default_provider: str,
) -> dict[str, dict[str, str]]:
    raw_routes = raw_conversation.get("routes", {})
    if not isinstance(raw_routes, Mapping):
        raise ValueError("conversation.routes must be a table")
    routes: dict[str, dict[str, str]] = {}
    for role, route in raw_routes.items():
        if not isinstance(route, Mapping):
            raise ValueError(f"conversation.routes.{role} must be a table")
        provider = str(route.get("provider", default_provider)).strip()
        prompt_profile = str(route.get("prompt_profile", role)).strip() or "default"
        if not provider:
            raise ValueError(f"conversation.routes.{role}.provider must not be empty")
        routes[str(role)] = {
            "provider": provider,
            "prompt_profile": prompt_profile,
        }
    routes.setdefault(
        "chat",
        {"provider": default_provider, "prompt_profile": "default"},
    )
    routes.setdefault(
        "coding_agent",
        {"provider": default_provider, "prompt_profile": "coding_agent"},
    )
    return routes


def _prompt_profiles(
    raw_conversation: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    raw_profiles = raw_conversation.get("prompt_profiles", {})
    if not isinstance(raw_profiles, Mapping):
        raise ValueError("conversation.prompt_profiles must be a table")
    profiles: dict[str, dict[str, str]] = {}
    for profile_name, profile in raw_profiles.items():
        if not isinstance(profile, Mapping):
            raise ValueError(
                f"conversation.prompt_profiles.{profile_name} must be a table"
            )
        normalized = _string_table(
            profile,
            field_name=f"conversation.prompt_profiles.{profile_name}",
        )
        profiles[str(profile_name)] = {
            "personality": normalized.get("personality", ""),
            "system_instruction": normalized.get("system_instruction", ""),
            "tool_instruction": normalized.get("tool_instruction", ""),
            "response_instruction": normalized.get("response_instruction", ""),
        }
    profiles.setdefault(
        "default",
        dict(DEFAULT_CHAT_PROMPT_PROFILE),
    )
    profiles.setdefault(
        "coding_agent",
        dict(DEFAULT_CODING_PROMPT_PROFILE),
    )
    return profiles


def _toml_key(key: str) -> str:
    if key and all(char.isalnum() or char in {"_", "-"} for char in key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Path):
        return json.dumps(str(value), ensure_ascii=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return '""'
    if isinstance(value, Mapping):
        return "{ " + ", ".join(
            f"{_toml_key(str(key))} = {_toml_value(item)}"
            for key, item in value.items()
        ) + " }"
    if isinstance(value, list):
        return "[ " + ", ".join(_toml_value(item) for item in value) + " ]"
    raise TypeError(f"Unsupported TOML value type: {type(value)!r}")


def _render_table(
    lines: list[str],
    path: tuple[str, ...],
    mapping: Mapping[str, Any],
    *,
    force_header: bool = False,
) -> None:
    scalar_items: list[tuple[str, Any]] = []
    nested_items: list[tuple[str, Mapping[str, Any]]] = []
    for key, value in mapping.items():
        if isinstance(value, Mapping):
            nested_items.append((str(key), value))
        else:
            scalar_items.append((str(key), value))

    should_emit_header = force_header or bool(scalar_items)
    if should_emit_header:
        if path:
            lines.append(f"[{'.'.join(_toml_key(part) for part in path)}]")
        for key, value in scalar_items:
            lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
        if nested_items:
            lines.append("")

    for index, (key, value) in enumerate(nested_items):
        if lines and lines[-1] != "":
            lines.append("")
        _render_table(lines, path + (key,), value, force_header=False)


def dump_settings(settings: Settings) -> str:
    lines: list[str] = []
    _render_table(
        lines,
        ("core",),
        {
            "data_dir": settings.core.data_dir,
            "log_level": settings.core.log_level,
            "tool_timeout_seconds": settings.core.tool_timeout_seconds,
        },
        force_header=True,
    )
    lines.append("")
    _render_table(
        lines,
        ("permissions",),
        {
            "profile": settings.permissions.profile,
            "interactive_approval": settings.permissions.interactive_approval,
        },
        force_header=True,
    )
    lines.append("")
    _render_table(
        lines,
        ("plugins",),
        {
            "roots": settings.plugins.roots,
            "enabled": settings.plugins.enabled,
            "options": settings.plugins.options,
        },
        force_header=True,
    )
    lines.append("")
    _render_table(
        lines,
        ("conversation",),
        {
            "default_provider": settings.conversation.default_provider,
            "store_backend": settings.conversation.store_backend,
            "sqlite_path": settings.conversation.sqlite_path,
            "max_tool_iterations": settings.conversation.max_tool_iterations,
            "max_tool_output_chars": settings.conversation.max_tool_output_chars,
            "routes": settings.conversation.routes,
            "prompt_profiles": settings.conversation.prompt_profiles,
        },
        force_header=True,
    )
    lines.append("")
    _render_table(
        lines,
        ("desktop",),
        {
            "hotkey": settings.desktop.hotkey,
            "window_anchor": settings.desktop.window_anchor,
            "model_path": settings.desktop.model_path,
            "click_opens_console": settings.desktop.click_opens_console,
        },
        force_header=True,
    )
    return "\n".join(lines).rstrip() + "\n"


def save_settings(
    settings: Settings,
    path: Path | None = None,
    *,
    base_dir: Path | None = None,
) -> Path:
    base = (base_dir or Path.cwd()).resolve()
    target = path or settings.config_path or (base / "config.local.toml")
    if not target.is_absolute():
        target = (base / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_settings(settings), encoding="utf-8")
    return target


def load_settings(path: Path | None = None, *, base_dir: Path | None = None) -> Settings:
    base = (base_dir or Path.cwd()).resolve()
    raw = copy.deepcopy(DEFAULTS)
    config_path: Path | None = None
    if path is not None:
        config_path = path if path.is_absolute() else base / path
        config_path = config_path.resolve()
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file does not exist: {config_path}")
        with config_path.open("rb") as handle:
            loaded = tomllib.load(handle)
        _deep_merge(raw, loaded)

    try:
        profile = str(raw["permissions"]["profile"])
        if profile not in {"observe", "assist", "admin"}:
            raise ValueError("permissions.profile must be observe, assist, or admin")
        timeout = float(raw["core"]["tool_timeout_seconds"])
        if timeout <= 0:
            raise ValueError("core.tool_timeout_seconds must be positive")
        max_tool_iterations = int(raw["conversation"]["max_tool_iterations"])
        max_tool_output_chars = int(raw["conversation"]["max_tool_output_chars"])
        if max_tool_iterations < 0:
            raise ValueError("conversation.max_tool_iterations must be non-negative")
        if max_tool_output_chars < 256:
            raise ValueError("conversation.max_tool_output_chars must be at least 256")
        store_backend = str(raw["conversation"]["store_backend"])
        if store_backend not in {"memory", "sqlite"}:
            raise ValueError("conversation.store_backend must be memory or sqlite")
        sqlite_path = Path(raw["conversation"]["sqlite_path"])
        default_provider = str(raw["conversation"]["default_provider"]).strip()
        if not default_provider:
            raise ValueError("conversation.default_provider must not be empty")
        routes = _conversation_routes(raw["conversation"], default_provider)
        prompt_profiles = _prompt_profiles(raw["conversation"])
        missing_profiles = sorted(
            {
                route["prompt_profile"]
                for route in routes.values()
                if route["prompt_profile"] not in prompt_profiles
            }
        )
        if missing_profiles:
            raise ValueError(
                f"conversation routes reference missing prompt profiles: {missing_profiles}"
            )

        data_dir = Path(raw["core"]["data_dir"])
        roots = [Path(item) for item in raw["plugins"]["roots"]]
        plugin_options = raw["plugins"].get("options", {})
        if not isinstance(plugin_options, Mapping):
            raise ValueError("plugins.options must be a table")
        invalid_plugin_options = [
            str(plugin_id)
            for plugin_id, options in plugin_options.items()
            if not isinstance(options, Mapping)
        ]
        if invalid_plugin_options:
            raise ValueError(
                f"Plugin options must be tables: {invalid_plugin_options}"
            )
        window_anchor = str(raw["desktop"]["window_anchor"])
        if window_anchor not in {
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        }:
            raise ValueError(
                "desktop.window_anchor must be top-left, top-right, bottom-left, or bottom-right"
            )
        return Settings(
            core=CoreSettings(
                data_dir=(data_dir if data_dir.is_absolute() else base / data_dir).resolve(),
                log_level=str(raw["core"]["log_level"]).upper(),
                tool_timeout_seconds=timeout,
            ),
            permissions=PermissionSettings(
                profile=profile,
                interactive_approval=bool(raw["permissions"]["interactive_approval"]),
            ),
            plugins=PluginSettings(
                roots=[(item if item.is_absolute() else base / item).resolve() for item in roots],
                enabled=[str(item) for item in raw["plugins"]["enabled"]],
                options={
                    str(plugin_id): dict(options)
                    for plugin_id, options in plugin_options.items()
                },
            ),
            conversation=ConversationSettings(
                default_provider=default_provider,
                routes=routes,
                prompt_profiles=prompt_profiles,
                store_backend=store_backend,
                sqlite_path=(
                    sqlite_path if sqlite_path.is_absolute() else base / sqlite_path
                ).resolve(),
                max_tool_iterations=max_tool_iterations,
                max_tool_output_chars=max_tool_output_chars,
            ),
            desktop=DesktopSettings(
                hotkey=str(raw["desktop"]["hotkey"]),
                window_anchor=window_anchor,
                model_path=(
                    None
                    if raw["desktop"]["model_path"] in {None, ""}
                    else str(raw["desktop"]["model_path"])
                ),
                click_opens_console=bool(raw["desktop"]["click_opens_console"]),
            ),
            config_path=config_path,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid configuration: {exc}") from exc
