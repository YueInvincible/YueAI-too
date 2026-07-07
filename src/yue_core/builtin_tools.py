from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .contracts import (
    Capability,
    PermissionOutcome,
    RiskLevel,
    ToolContext,
    ToolOutputKind,
    ToolSpec,
)
from .contracts import CoreEvent
from .shell_utils import build_shell_argv

_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_TOOL_OUTPUT_LINE_LIMIT = 160
_SEARCH_MATCH_CHAR_LIMIT = 500
_TRUNCATED_WARNING = (
    "[TRUNCATED: Output too long. Use grep or narrower filters to find specific info]"
)
_SHORT_TRUNCATED_MARKER = "...[truncated]..."


def _tool_metadata(
    *,
    parallel_safe: bool = False,
    mutates_state: bool = False,
) -> dict[str, bool]:
    return {
        "parallel_safe": parallel_safe,
        "mutates_state": mutates_state,
    }


def _workspace_root(context: ToolContext) -> Path:
    root = context.services.get("core.workspace_root")
    if not isinstance(root, Path):
        raise RuntimeError("core.workspace_root service is not registered")
    return root


def _resolve_workspace_path(context: ToolContext, raw_path: str) -> Path:
    root = _workspace_root(context).resolve()
    candidate = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Path escapes workspace root: {candidate}")
    return candidate


def _read_text_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _append_text(path: Path, content: str) -> int:
    with path.open("a", encoding="utf-8") as handle:
        return handle.write(content)


def _run_command_args(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _collapse_blank_lines(lines: Sequence[str]) -> list[str]:
    collapsed: list[str] = []
    last_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and last_blank:
            continue
        collapsed.append("" if is_blank else line)
        last_blank = is_blank
    return collapsed


def _truncate_lines(lines: Sequence[str], *, max_lines: int = _TOOL_OUTPUT_LINE_LIMIT) -> tuple[list[str], bool]:
    if len(lines) <= max_lines:
        return list(lines), False
    head = max_lines // 2
    tail = max_lines - head - 1
    truncated = [*lines[:head], _TRUNCATED_WARNING]
    if tail > 0:
        truncated.extend(lines[-tail:])
    return truncated, True


def _sanitize_command_output(text: str, *, max_lines: int = _TOOL_OUTPUT_LINE_LIMIT) -> tuple[str, bool]:
    normalized = _strip_ansi(text).replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines = _collapse_blank_lines(normalized.split("\n"))
    truncated_lines, truncated = _truncate_lines(cleaned_lines, max_lines=max_lines)
    return "\n".join(truncated_lines).strip("\n"), truncated


def _truncate_text_chars(
    text: str,
    *,
    max_chars: int,
    marker: str = _TRUNCATED_WARNING,
) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    selected_marker = marker
    available = max_chars - len(selected_marker)
    if available <= 1 and len(_SHORT_TRUNCATED_MARKER) < max_chars:
        selected_marker = _SHORT_TRUNCATED_MARKER
        available = max_chars - len(selected_marker)
    if available <= 1:
        return text[:max_chars], True
    head = available // 2
    tail = available - head
    return f"{text[:head]}{selected_marker}{text[-tail:]}", True


def _sanitize_search_match_line(line: str, *, max_chars: int = _SEARCH_MATCH_CHAR_LIMIT) -> tuple[str, bool]:
    normalized = _strip_ansi(line).replace("\r", " ").replace("\n", " ").strip()
    return _truncate_text_chars(normalized, max_chars=max_chars)


def _truncate_file_lines(lines: Sequence[str], *, max_lines: int = _TOOL_OUTPUT_LINE_LIMIT) -> tuple[list[str], bool]:
    return _truncate_lines(lines, max_lines=max_lines)


def _workspace_relative(context: ToolContext, path: Path) -> str:
    return path.relative_to(_workspace_root(context)).as_posix()


def _trash_dir(context: ToolContext) -> Path:
    settings = context.services.get("core.settings")
    data_dir = getattr(getattr(settings, "core", None), "data_dir", None)
    if isinstance(data_dir, Path):
        return data_dir / "trash"
    return _workspace_root(context) / ".yue_trash"


class EchoTool:
    spec = ToolSpec(
        name="core.echo",
        description="Return text unchanged. Used for health checks and integration tests.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "maxLength": 10000}},
            "required": ["text"],
            "additionalProperties": False,
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return {"text": arguments["text"]}


class HealthTool:
    spec = ToolSpec(
        name="core.health",
        description="Return a minimal health snapshot for the running core.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return {
            "status": "ok",
            "request_id": context.request.id,
            "services": sorted(context.services),
        }


class FileReadTool:
    spec = ToolSpec(
        name="file.read",
        description="Read a UTF-8 text file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
        output_kind=ToolOutputKind.FILE_CONTENT,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments["path"]))
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        lines = await asyncio.to_thread(_read_text_lines, path)
        start_line = int(arguments.get("start_line", 1))
        end_line = int(arguments.get("end_line", len(lines)))
        if end_line < start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        selected = lines[start_line - 1 : end_line]
        returned_lines, truncated = _truncate_file_lines(selected)
        return {
            "path": str(path),
            "content": "\n".join(returned_lines),
            "start_line": start_line,
            "end_line": min(end_line, len(lines)),
            "total_lines": len(lines),
            "returned_lines": len(returned_lines),
            "truncated": truncated,
        }


class FileWriteTool:
    spec = ToolSpec(
        name="file.write",
        description="Write full UTF-8 text content to a file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "content": {"type": "string"},
                "create_dirs": {"type": "boolean"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.MEDIUM,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments["path"]))
        if bool(arguments.get("create_dirs", True)):
            path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_text, str(arguments["content"]), "utf-8")
        return {"path": str(path), "bytes_written": path.stat().st_size}


class FileMoveTool:
    spec = ToolSpec(
        name="file.move",
        description="Move or rename a file or directory inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "source_path": {"type": "string", "minLength": 1},
                "destination_path": {"type": "string", "minLength": 1},
                "overwrite": {"type": "boolean"},
                "create_dirs": {"type": "boolean"},
            },
            "required": ["source_path", "destination_path"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.MEDIUM,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        source = _resolve_workspace_path(context, str(arguments["source_path"]))
        destination = _resolve_workspace_path(context, str(arguments["destination_path"]))
        if not source.exists():
            raise FileNotFoundError(source)
        if bool(arguments.get("create_dirs", True)):
            destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if not bool(arguments.get("overwrite", False)):
                raise FileExistsError(destination)
            if destination.is_dir():
                await asyncio.to_thread(shutil.rmtree, destination)
            else:
                await asyncio.to_thread(destination.unlink)
        await asyncio.to_thread(shutil.move, str(source), str(destination))
        return {"source_path": str(source), "destination_path": str(destination)}


class FileDeleteTool:
    spec = ToolSpec(
        name="file.delete",
        description="Delete a file or directory inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "recursive": {"type": "boolean"},
                "missing_ok": {"type": "boolean"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.HIGH,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments["path"]))
        if not path.exists():
            if bool(arguments.get("missing_ok", False)):
                return {"path": str(path), "deleted": False, "missing": True}
            raise FileNotFoundError(path)
        if path.is_dir():
            if not bool(arguments.get("recursive", False)):
                raise IsADirectoryError("Directory deletion requires recursive=true")
            await asyncio.to_thread(shutil.rmtree, path)
        else:
            await asyncio.to_thread(path.unlink)
        return {"path": str(path), "deleted": True}


class FileEditTool:
    spec = ToolSpec(
        name="file.edit",
        description="Replace exact text inside a UTF-8 file in the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["path", "old_text", "new_text"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.MEDIUM,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments["path"]))
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        old_text = str(arguments["old_text"])
        if not old_text:
            raise ValueError("old_text must not be empty")
        new_text = str(arguments["new_text"])
        replace_all = bool(arguments.get("replace_all", False))
        content = await asyncio.to_thread(path.read_text, "utf-8")
        occurrences = content.count(old_text)
        if occurrences == 0:
            raise ValueError("old_text was not found in file")
        if occurrences > 1 and not replace_all:
            raise ValueError("old_text appears multiple times; set replace_all=true")
        updated = content.replace(old_text, new_text) if replace_all else content.replace(old_text, new_text, 1)
        await asyncio.to_thread(path.write_text, updated, "utf-8")
        return {"path": str(path), "replacements": occurrences if replace_all else 1}


class FileListTool:
    spec = ToolSpec(
        name="file.list",
        description="List files and directories inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "recursive": {"type": "boolean"},
                "max_entries": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments.get("path", ".")))
        if not path.exists() or not path.is_dir():
            raise NotADirectoryError(path)
        recursive = bool(arguments.get("recursive", False))
        max_entries = int(arguments.get("max_entries", 200))
        iterator = path.rglob("*") if recursive else path.iterdir()
        entries = []
        for item in iterator:
            if len(entries) >= max_entries:
                break
            relative = item.relative_to(_workspace_root(context)).as_posix()
            entries.append(
                {
                    "path": relative,
                    "type": "dir" if item.is_dir() else "file",
                    "size": None if item.is_dir() else item.stat().st_size,
                }
            )
        return {"path": str(path), "entries": entries, "truncated": len(entries) >= max_entries}


class FileSearchTool:
    spec = ToolSpec(
        name="file.search",
        description="Search for a regex pattern in UTF-8 workspace files.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "minLength": 1},
                "path": {"type": "string"},
                "recursive": {"type": "boolean"},
                "case_sensitive": {"type": "boolean"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments.get("path", ".")))
        if not path.exists():
            raise FileNotFoundError(path)
        recursive = bool(arguments.get("recursive", True))
        max_results = int(arguments.get("max_results", 200))
        flags = 0 if bool(arguments.get("case_sensitive", False)) else re.IGNORECASE
        pattern = re.compile(str(arguments["pattern"]), flags)
        results = []
        files = path.rglob("*") if path.is_dir() and recursive else (path.iterdir() if path.is_dir() else [path])
        root = _workspace_root(context)
        for item in files:
            if len(results) >= max_results:
                break
            if not item.is_file():
                continue
            try:
                lines = await asyncio.to_thread(_read_text_lines, item)
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if pattern.search(line):
                    cleaned_line, line_truncated = _sanitize_search_match_line(line)
                    results.append(
                        {
                            "path": item.relative_to(root).as_posix(),
                            "line_number": line_number,
                            "line": cleaned_line,
                            "line_truncated": line_truncated,
                        }
                    )
                    if len(results) >= max_results:
                        break
        return {"matches": results, "truncated": len(results) >= max_results}


class ShellExecTool:
    spec = ToolSpec(
        name="shell.exec",
        description="Run a shell command inside the workspace and capture stdout/stderr.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "minLength": 1},
                "cwd": {"type": "string"},
                "timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
                "dry_run": {"type": "boolean"},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
        capability=Capability.SHELL_EXECUTE,
        risk=RiskLevel.HIGH,
        timeout_seconds=120.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        cwd = _resolve_workspace_path(context, str(arguments.get("cwd", ".")))
        timeout = float(arguments.get("timeout_seconds", 120.0))
        dry_run = bool(arguments.get("dry_run", False))
        shell_argv = build_shell_argv(str(arguments["command"]))
        if dry_run:
            return {
                "command": str(arguments["command"]),
                "cwd": str(cwd),
                "argv": shell_argv,
                "dry_run": True,
            }
        process = await asyncio.create_subprocess_exec(
            *shell_argv,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command exceeded {timeout:g}s timeout")
        stdout_text, stdout_truncated = _sanitize_command_output(
            stdout.decode("utf-8", errors="replace")
        )
        stderr_text, stderr_truncated = _sanitize_command_output(
            stderr.decode("utf-8", errors="replace")
        )
        return {
            "command": str(arguments["command"]),
            "cwd": str(cwd),
            "exit_code": process.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


class ProcessListTool:
    spec = ToolSpec(
        name="process.list",
        description="List operating-system processes with optional filtering.",
        input_schema={
            "type": "object",
            "properties": {
                "name_filter": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 1000},
                "dry_run": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        capability=Capability.PROCESS_READ,
        risk=RiskLevel.MEDIUM,
        timeout_seconds=60.0,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        name_filter = str(arguments.get("name_filter", "")).strip().lower()
        max_results = int(arguments.get("max_results", 200))
        command = ["tasklist", "/fo", "csv", "/nh"] if os.name == "nt" else ["ps", "-ax", "-o", "pid=,comm="]
        if bool(arguments.get("dry_run", False)):
            return {"argv": command, "dry_run": True}
        completed = await asyncio.to_thread(_run_command_args, command, _workspace_root(context))
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "process listing failed")
        results = _parse_process_output(completed.stdout, windows=os.name == "nt")
        if name_filter:
            results = [item for item in results if name_filter in item["name"].lower()]
        return {"processes": results[:max_results], "truncated": len(results) > max_results}


class ProcessKillTool:
    spec = ToolSpec(
        name="process.kill",
        description="Terminate a process by pid.",
        input_schema={
            "type": "object",
            "properties": {
                "pid": {"type": "integer", "minimum": 1},
                "force": {"type": "boolean"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["pid"],
            "additionalProperties": False,
        },
        capability=Capability.PROCESS_CONTROL,
        risk=RiskLevel.HIGH,
        timeout_seconds=30.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        pid = int(arguments["pid"])
        force = bool(arguments.get("force", False))
        command = (
            ["taskkill", "/pid", str(pid), *(["/f"] if force else [])]
            if os.name == "nt"
            else ["kill", *(["-9"] if force else ["-15"]), str(pid)]
        )
        if bool(arguments.get("dry_run", False)):
            return {"argv": command, "dry_run": True, "pid": pid}
        completed = await asyncio.to_thread(_run_command_args, command, _workspace_root(context))
        stdout_text, stdout_truncated = _sanitize_command_output(completed.stdout)
        stderr_text, stderr_truncated = _sanitize_command_output(completed.stderr)
        return {
            "pid": pid,
            "force": force,
            "exit_code": completed.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


class PackageInstallTool:
    spec = ToolSpec(
        name="package.install",
        description="Install packages with a supported package manager.",
        input_schema={
            "type": "object",
            "properties": {
                "manager": {
                    "type": "string",
                    "enum": ["pip", "uv", "npm", "pnpm", "yarn", "cargo"],
                },
                "packages": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 1,
                },
                "cwd": {"type": "string"},
                "dev": {"type": "boolean"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["manager", "packages"],
            "additionalProperties": False,
        },
        capability=Capability.NETWORK_ACCESS,
        risk=RiskLevel.HIGH,
        timeout_seconds=300.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        manager = str(arguments["manager"])
        packages = [str(item) for item in arguments["packages"]]
        cwd = _resolve_workspace_path(context, str(arguments.get("cwd", ".")))
        dev = bool(arguments.get("dev", False))
        dry_run = bool(arguments.get("dry_run", False))
        argv = _package_install_command(manager, packages, dev=dev)
        if dry_run:
            return {"manager": manager, "cwd": str(cwd), "argv": argv, "dry_run": True}

        executable = shutil.which(argv[0]) if os.path.sep not in argv[0] else argv[0]
        if executable is None:
            raise FileNotFoundError(f"Executable not found: {argv[0]}")
        process = await asyncio.create_subprocess_exec(
            executable,
            *argv[1:],
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        stdout_text, stdout_truncated = _sanitize_command_output(
            stdout.decode("utf-8", errors="replace")
        )
        stderr_text, stderr_truncated = _sanitize_command_output(
            stderr.decode("utf-8", errors="replace")
        )
        return {
            "manager": manager,
            "cwd": str(cwd),
            "argv": argv,
            "exit_code": process.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


class GitStatusTool:
    spec = ToolSpec(
        name="git.status",
        description="Return porcelain git status for a repository inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "dry_run": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        capability=Capability.PROCESS_READ,
        risk=RiskLevel.MEDIUM,
        timeout_seconds=30.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        repo_path = _resolve_workspace_path(context, str(arguments.get("repo_path", ".")))
        command = ["git", "status", "--short", "--branch"]
        if bool(arguments.get("dry_run", False)):
            return {"argv": command, "cwd": str(repo_path), "dry_run": True}
        completed = await asyncio.to_thread(_run_command_args, command, repo_path)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git status failed")
        status_text, truncated = _sanitize_command_output(completed.stdout)
        return {"cwd": str(repo_path), "status": status_text, "truncated": truncated}


class GitDiffTool:
    spec = ToolSpec(
        name="git.diff",
        description="Return git diff text for a repository inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "pathspec": {"type": "string"},
                "staged": {"type": "boolean"},
                "max_chars": {"type": "integer", "minimum": 256, "maximum": 200000},
                "dry_run": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        capability=Capability.PROCESS_READ,
        risk=RiskLevel.MEDIUM,
        timeout_seconds=60.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        repo_path = _resolve_workspace_path(context, str(arguments.get("repo_path", ".")))
        command = ["git", "diff"]
        if bool(arguments.get("staged", False)):
            command.append("--staged")
        pathspec = str(arguments.get("pathspec", "")).strip()
        if pathspec:
            command.extend(["--", pathspec])
        if bool(arguments.get("dry_run", False)):
            return {"argv": command, "cwd": str(repo_path), "dry_run": True}
        completed = await asyncio.to_thread(_run_command_args, command, repo_path)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git diff failed")
        max_chars = int(arguments.get("max_chars", 50000))
        diff_text, line_truncated = _sanitize_command_output(completed.stdout)
        diff_text, char_truncated = _truncate_text_chars(diff_text, max_chars=max_chars)
        return {
            "cwd": str(repo_path),
            "diff": diff_text,
            "truncated": line_truncated or char_truncated,
        }


class WorkspaceListTool:
    spec = ToolSpec(
        name="workspace.list",
        description="List files and directories in the workspace with depth and hidden-file controls.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "depth": {"type": "integer", "minimum": 0, "maximum": 32},
                "include_hidden": {"type": "boolean"},
                "max_entries": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments.get("path", ".")))
        if not path.exists() or not path.is_dir():
            raise NotADirectoryError(path)
        depth = int(arguments.get("depth", 3))
        include_hidden = bool(arguments.get("include_hidden", False))
        max_entries = int(arguments.get("max_entries", 200))
        root = _workspace_root(context)
        base_depth = len(path.relative_to(root).parts) if path != root else 0
        entries = []
        for item in path.rglob("*"):
            relative = item.relative_to(root)
            if not include_hidden and any(part.startswith(".") for part in relative.parts):
                continue
            item_depth = len(relative.parts) - base_depth
            if item_depth > depth:
                continue
            entries.append(
                {
                    "path": relative.as_posix(),
                    "type": "dir" if item.is_dir() else "file",
                    "size": None if item.is_dir() else item.stat().st_size,
                }
            )
            if len(entries) >= max_entries:
                break
        return {
            "path": _workspace_relative(context, path),
            "entries": entries,
            "truncated": len(entries) >= max_entries,
        }


class WorkspaceReadTool:
    spec = ToolSpec(
        name="workspace.read",
        description="Read a UTF-8 workspace file with line-range metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
        output_kind=ToolOutputKind.FILE_CONTENT,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        payload = await FileReadTool().invoke(arguments, context)
        payload["path"] = _workspace_relative(context, _resolve_workspace_path(context, str(arguments["path"])))
        return payload


class WorkspaceSearchTool:
    spec = ToolSpec(
        name="workspace.search",
        description="Search workspace paths by filename or content.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "type": {"type": "string", "enum": ["path", "content"]},
                "path": {"type": "string"},
                "include_hidden": {"type": "boolean"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments.get("path", ".")))
        query = str(arguments["query"]).strip()
        search_type = str(arguments.get("type", "path"))
        include_hidden = bool(arguments.get("include_hidden", False))
        max_results = int(arguments.get("max_results", 200))
        root = _workspace_root(context)
        if search_type == "content":
            return await FileSearchTool().invoke(
                {
                    "pattern": re.escape(query),
                    "path": str(path),
                    "recursive": True,
                    "case_sensitive": False,
                    "max_results": max_results,
                },
                context,
            )
        matches = []
        for item in path.rglob("*"):
            relative = item.relative_to(root)
            if not include_hidden and any(part.startswith(".") for part in relative.parts):
                continue
            if query.lower() in relative.name.lower():
                matches.append(
                    {
                        "path": relative.as_posix(),
                        "type": "dir" if item.is_dir() else "file",
                    }
                )
                if len(matches) >= max_results:
                    break
        return {"matches": matches, "truncated": len(matches) >= max_results}


class WorkspaceGrepTool:
    spec = ToolSpec(
        name="workspace.grep",
        description="Search workspace file contents by literal string or regex.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "minLength": 1},
                "path": {"type": "string"},
                "regex": {"type": "boolean"},
                "case_sensitive": {"type": "boolean"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
        metadata=_tool_metadata(parallel_safe=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        pattern = str(arguments["pattern"])
        return await FileSearchTool().invoke(
            {
                "pattern": pattern if bool(arguments.get("regex", False)) else re.escape(pattern),
                "path": str(arguments.get("path", ".")),
                "recursive": True,
                "case_sensitive": bool(arguments.get("case_sensitive", False)),
                "max_results": int(arguments.get("max_results", 200)),
            },
            context,
        )


class WorkspaceWriteTool:
    spec = ToolSpec(
        name="workspace.write",
        description="Create, append, or overwrite a UTF-8 file in the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["create_only", "append", "overwrite"]},
            },
            "required": ["path", "content", "mode"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.MEDIUM,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        path = _resolve_workspace_path(context, str(arguments["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = str(arguments["mode"])
        content = str(arguments["content"])
        if mode == "create_only":
            if path.exists():
                raise FileExistsError(path)
            await asyncio.to_thread(path.write_text, content, "utf-8")
        elif mode == "append":
            await asyncio.to_thread(_append_text, path, content)
        elif mode == "overwrite":
            await asyncio.to_thread(path.write_text, content, "utf-8")
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        return {"path": str(path), "mode": mode, "bytes_written": path.stat().st_size}


class WorkspaceEditTool:
    spec = ToolSpec(
        name="workspace.edit",
        description="Replace one exact search block with a new block in a UTF-8 workspace file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "search_block": {"type": "string", "minLength": 1},
                "replace_block": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["path", "search_block", "replace_block"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.MEDIUM,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return await FileEditTool().invoke(
            {
                "path": arguments["path"],
                "old_text": arguments["search_block"],
                "new_text": arguments["replace_block"],
                "replace_all": bool(arguments.get("replace_all", False)),
            },
            context,
        )


class WorkspaceOpsTool:
    spec = ToolSpec(
        name="workspace.ops",
        description="Perform copy, move, delete_to_trash, or mkdir operations inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["copy", "move", "delete_to_trash", "mkdir"]},
                "from": {"type": "string"},
                "to": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_WRITE,
        risk=RiskLevel.MEDIUM,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        action = str(arguments["action"])
        if action == "mkdir":
            target = _resolve_workspace_path(context, str(arguments.get("from") or arguments.get("to") or ""))
            target.mkdir(parents=True, exist_ok=True)
            return {"action": action, "path": str(target)}

        source_raw = str(arguments.get("from", "")).strip()
        if not source_raw:
            raise ValueError("from is required for this action")
        source = _resolve_workspace_path(context, source_raw)
        if not source.exists():
            raise FileNotFoundError(source)

        if action == "copy":
            target_raw = str(arguments.get("to", "")).strip()
            if not target_raw:
                raise ValueError("to is required for copy")
            target = _resolve_workspace_path(context, target_raw)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                await asyncio.to_thread(shutil.copytree, source, target, dirs_exist_ok=True)
            else:
                await asyncio.to_thread(shutil.copy2, source, target)
            return {"action": action, "from": str(source), "to": str(target)}

        if action == "move":
            target_raw = str(arguments.get("to", "")).strip()
            if not target_raw:
                raise ValueError("to is required for move")
            target = _resolve_workspace_path(context, target_raw)
            target.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.move, str(source), str(target))
            return {"action": action, "from": str(source), "to": str(target)}

        if action == "delete_to_trash":
            trash_root = _trash_dir(context)
            trash_root.mkdir(parents=True, exist_ok=True)
            target = trash_root / f"{source.name}.{context.request.id}"
            await asyncio.to_thread(shutil.move, str(source), str(target))
            return {"action": action, "from": str(source), "trashed_to": str(target)}

        raise ValueError(f"Unsupported action: {action}")


class ShellRunTool:
    spec = ToolSpec(
        name="shell.run",
        description="Run a shell command with explicit cwd, timeout, and risk metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "minLength": 1},
                "cwd": {"type": "string"},
                "timeout": {"type": "number", "exclusiveMinimum": 0},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "dry_run": {"type": "boolean"},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
        capability=Capability.SHELL_EXECUTE,
        risk=RiskLevel.HIGH,
        timeout_seconds=120.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        payload = await ShellExecTool().invoke(
            {
                "command": arguments["command"],
                "cwd": arguments.get("cwd", "."),
                "timeout_seconds": arguments.get("timeout", 120.0),
                "dry_run": bool(arguments.get("dry_run", False)),
            },
            context,
        )
        payload["risk_level"] = str(arguments.get("risk_level", "high"))
        return payload


class ShellSessionTool:
    spec = ToolSpec(
        name="shell.session",
        description="Manage a long-lived shell session for background commands.",
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["start", "read", "stop", "list"]},
                "session_id": {"type": "string", "minLength": 1},
                "command": {"type": "string", "minLength": 1},
                "cwd": {"type": "string"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "dry_run": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        capability=Capability.SHELL_EXECUTE,
        risk=RiskLevel.HIGH,
        timeout_seconds=30.0,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        manager = context.services.get("core.shell_sessions")
        if manager is None:
            raise RuntimeError("core.shell_sessions service is not registered")
        audit = context.services.get("core.audit")
        action = str(arguments["action"])
        if action == "list":
            payload = {"sessions": await manager.list()}
            if audit is not None:
                await audit.write(
                    "shell.session.list",
                    {
                        "request_id": context.request.id,
                        "session_count": len(payload["sessions"]),
                    },
                )
            await context.publish(
                CoreEvent(
                    "shell.session.listed",
                    {"request_id": context.request.id, "session_count": len(payload["sessions"])},
                    correlation_id=context.request.id,
                )
            )
            return payload
        session_id = str(arguments.get("session_id", "")).strip()
        if not session_id:
            raise ValueError("session_id is required")
        if action == "read":
            payload = await manager.read(session_id)
            if audit is not None:
                await audit.write(
                    "shell.session.read",
                    {
                        "request_id": context.request.id,
                        "session_id": session_id,
                        "running": payload["running"],
                    },
                )
            await context.publish(
                CoreEvent(
                    "shell.session.read",
                    {
                        "request_id": context.request.id,
                        "session_id": session_id,
                        "running": payload["running"],
                    },
                    correlation_id=context.request.id,
                )
            )
            return payload
        if action == "stop":
            payload = await manager.stop(session_id)
            if audit is not None:
                await audit.write(
                    "shell.session.stop",
                    {
                        "request_id": context.request.id,
                        "session_id": session_id,
                        "exit_code": payload["exit_code"],
                    },
                )
            await context.publish(
                CoreEvent(
                    "shell.session.stopped",
                    {
                        "request_id": context.request.id,
                        "session_id": session_id,
                        "exit_code": payload["exit_code"],
                    },
                    correlation_id=context.request.id,
                )
            )
            return payload
        if action != "start":
            raise ValueError(f"Unsupported action: {action}")
        command = str(arguments.get("command", "")).strip()
        if not command:
            raise ValueError("command is required for start")
        cwd = _resolve_workspace_path(context, str(arguments.get("cwd", ".")))
        if bool(arguments.get("dry_run", False)):
            return {
                "action": action,
                "session_id": session_id,
                "command": command,
                "cwd": str(cwd),
                "argv": build_shell_argv(command),
                "risk_level": str(arguments.get("risk_level", "high")),
                "dry_run": True,
            }
        snapshot = await manager.start(session_id, command, cwd)
        snapshot["risk_level"] = str(arguments.get("risk_level", "high"))
        if audit is not None:
            await audit.write(
                "shell.session.start",
                {
                    "request_id": context.request.id,
                    "session_id": session_id,
                    "command": command,
                    "cwd": str(cwd),
                    "pid": snapshot["pid"],
                },
            )
        await context.publish(
            CoreEvent(
                "shell.session.started",
                {
                    "request_id": context.request.id,
                    "session_id": session_id,
                    "command": command,
                    "cwd": str(cwd),
                    "pid": snapshot["pid"],
                },
                correlation_id=context.request.id,
            )
        )
        return snapshot


class TodoUpdateTool:
    spec = ToolSpec(
        name="todo.update",
        description="Update the agent's internal task checklist for the current session.",
        input_schema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "minLength": 1},
                            "done": {"type": "boolean"},
                        },
                        "required": ["text", "done"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
        metadata=_tool_metadata(mutates_state=True),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        items = [{"text": str(item["text"]), "done": bool(item["done"])} for item in arguments["items"]]
        state = context.services.get("core.todo_state")
        if isinstance(state, dict):
            state[context.request.session_id or "default"] = items
        return {"session_id": context.request.session_id, "items": items}


class ApprovalRequestTool:
    spec = ToolSpec(
        name="approval.request",
        description="Request explicit user approval for a proposed action.",
        input_schema={
            "type": "object",
            "properties": {
                "action_description": {"type": "string", "minLength": 1},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            },
            "required": ["action_description", "risk_level"],
            "additionalProperties": False,
        },
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
        metadata=_tool_metadata(mutates_state=False),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        permissions = context.services.get("core.permissions")
        if permissions is None:
            raise RuntimeError("core.permissions service is not registered")
        audit = context.services.get("core.audit")
        await context.publish(
            CoreEvent(
                "approval.requested",
                {
                    "request_id": context.request.id,
                    "actor": context.request.actor,
                    "session_id": context.request.session_id,
                    "action_description": str(arguments["action_description"]),
                    "risk_level": str(arguments["risk_level"]),
                },
                correlation_id=context.request.id,
            )
        )
        if audit is not None:
            await audit.write(
                "approval.requested",
                {
                    "request_id": context.request.id,
                    "actor": context.request.actor,
                    "session_id": context.request.session_id,
                    "action_description": str(arguments["action_description"]),
                    "risk_level": str(arguments["risk_level"]),
                },
            )
        decision = await permissions.request_explicit_approval(
            str(arguments["action_description"]),
            str(arguments["risk_level"]),
            actor=context.request.actor,
            session_id=context.request.session_id,
        )
        payload = {
            "approved": decision.outcome is PermissionOutcome.ALLOW,
            "outcome": decision.outcome.value,
            "reason": decision.reason,
            "rule_id": decision.rule_id,
            "action_description": str(arguments["action_description"]),
            "risk_level": str(arguments["risk_level"]),
        }
        if audit is not None:
            await audit.write(
                "approval.resolved",
                {
                    "request_id": context.request.id,
                    "actor": context.request.actor,
                    "session_id": context.request.session_id,
                    "outcome": decision.outcome.value,
                    "reason": decision.reason,
                    "risk_level": str(arguments["risk_level"]),
                },
            )
        await context.publish(
            CoreEvent(
                "approval.resolved",
                {
                    "request_id": context.request.id,
                    "actor": context.request.actor,
                    "session_id": context.request.session_id,
                    "outcome": decision.outcome.value,
                    "reason": decision.reason,
                    "risk_level": str(arguments["risk_level"]),
                },
                correlation_id=context.request.id,
            )
        )
        return payload


class AskUserApprovalTool:
    spec = ToolSpec(
        name="ask_user_approval",
        description="Alias for approval.request to request explicit user approval for a proposed action.",
        input_schema=ApprovalRequestTool.spec.input_schema,
        capability=Capability.CORE_READ,
        risk=RiskLevel.LOW,
        metadata=_tool_metadata(mutates_state=False),
    )

    async def invoke(self, arguments: Mapping[str, Any], context: ToolContext) -> Any:
        return await ApprovalRequestTool().invoke(arguments, context)


def _package_install_command(manager: str, packages: Sequence[str], *, dev: bool) -> list[str]:
    if manager == "pip":
        return [sys.executable, "-m", "pip", "install", *packages]
    if manager == "uv":
        return ["uv", "pip", "install", *packages]
    if manager == "npm":
        return ["npm", "install", *(["--save-dev"] if dev else []), *packages]
    if manager == "pnpm":
        return ["pnpm", "add", *(["-D"] if dev else []), *packages]
    if manager == "yarn":
        return ["yarn", "add", *(["--dev"] if dev else []), *packages]
    if manager == "cargo":
        return ["cargo", "add", *packages]
    raise ValueError(f"Unsupported package manager: {manager}")


def _parse_process_output(stdout: str, *, windows: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if windows:
        import csv

        reader = csv.reader(stdout.splitlines())
        for row in reader:
            if len(row) < 2:
                continue
            with contextlib.suppress(ValueError):
                results.append({"name": row[0], "pid": int(row[1])})
        return results
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        with contextlib.suppress(ValueError):
            results.append({"pid": int(parts[0]), "name": parts[1]})
    return results
