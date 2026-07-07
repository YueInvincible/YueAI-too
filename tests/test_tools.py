import unittest
import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from yue_core.app import CODING_AGENT_TOOL_ALIASES, ToolAlias
from yue_core.audit import AuditLog
from yue_core.builtin_tools import (
    ApprovalRequestTool,
    AskUserApprovalTool,
    EchoTool,
    FileDeleteTool,
    FileEditTool,
    FileListTool,
    FileMoveTool,
    FileReadTool,
    FileSearchTool,
    FileWriteTool,
    GitDiffTool,
    GitStatusTool,
    PackageInstallTool,
    ProcessKillTool,
    ProcessListTool,
    ShellExecTool,
    ShellSessionTool,
    ShellRunTool,
    _sanitize_command_output,
    TodoUpdateTool,
    WorkspaceEditTool,
    WorkspaceGrepTool,
    WorkspaceListTool,
    WorkspaceOpsTool,
    WorkspaceReadTool,
    WorkspaceSearchTool,
    WorkspaceWriteTool,
)
from yue_core.contracts import (
    Capability,
    RiskLevel,
    ToolContext,
    ToolOutputKind,
    ToolRequest,
    ToolSpec,
    ToolStatus,
)
from yue_core.events import EventBus
from yue_core.permissions import PermissionEngine
from yue_core.shell_sessions import ShellSessionManager
from yue_core.tools import ToolExecutor, ToolRegistry
from tests.support import workspace_temp_dir


class FakeProcess:
    def __init__(self, *, stdout: bytes = b"", stderr: bytes = b"", pid: int = 4321):
        self.pid = pid
        self.returncode = None
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stdout.feed_eof()
        self.stderr.feed_data(stderr)
        self.stderr.feed_eof()
        self.killed = False

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


class AllowApprovalProvider:
    async def request_approval(self, request, spec, reason):
        return True


class DirtyShellRunTool:
    spec = ToolSpec(
        name="demo.command.output",
        description="Return intentionally unsanitized command output.",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        capability=Capability.SHELL_EXECUTE,
        risk=RiskLevel.HIGH,
        output_kind=ToolOutputKind.COMMAND_OUTPUT,
    )

    async def invoke(self, arguments, context: ToolContext):
        return {
            "stdout": "start\n\n\x1b[31mred\x1b[0m\n",
            "stderr": "\x1b[33mwarn\x1b[0m\n",
            "sessions": [
                {
                    "stdout": "nested\n\n\x1b[32mok\x1b[0m\n",
                    "stderr": "",
                }
            ],
        }


class ParallelReadTool:
    spec = ToolSpec(
        name="demo.parallel.read",
        description="Parallel-safe read tool.",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        capability=Capability.FILE_READ,
        risk=RiskLevel.LOW,
        metadata={"parallel_safe": True, "mutates_state": False},
    )

    async def invoke(self, arguments, context: ToolContext):
        await asyncio.sleep(0.01)
        return {"value": arguments["value"]}


class ToolExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_context = workspace_temp_dir()
        self.temp = self.temp_context.__enter__()
        registry = ToolRegistry()
        registry.register(ApprovalRequestTool())
        registry.register(AskUserApprovalTool())
        registry.register(EchoTool())
        registry.register(FileReadTool())
        registry.register(FileListTool())
        registry.register(FileSearchTool())
        registry.register(WorkspaceListTool())
        registry.register(WorkspaceReadTool())
        registry.register(WorkspaceSearchTool())
        registry.register(WorkspaceGrepTool())
        registry.register(TodoUpdateTool())
        registry.register(ShellSessionTool())
        for name, tool in list(registry._tools.items()):
            alias_name = CODING_AGENT_TOOL_ALIASES.get(name)
            if alias_name:
                registry.register(ToolAlias(tool, alias_name))
        self.shell_sessions = ShellSessionManager()
        self.observe_audit = AuditLog(self.temp / "audit.jsonl")
        self.executor = ToolExecutor(
            registry,
            PermissionEngine("observe", interactive_approval=True, approval_provider=AllowApprovalProvider()),
            EventBus(),
            self.observe_audit,
            services={
                "core.workspace_root": self.temp,
                "core.shell_sessions": self.shell_sessions,
                "core.audit": self.observe_audit,
                "core.permissions": PermissionEngine(
                    "observe",
                    interactive_approval=True,
                    approval_provider=AllowApprovalProvider(),
                ),
            },
        )
        self.observe_permissions = self.executor.permissions
        self.executor.services["core.permissions"] = self.observe_permissions
        admin_registry = ToolRegistry()
        for tool in (
            ApprovalRequestTool(),
            AskUserApprovalTool(),
            EchoTool(),
            FileReadTool(),
            FileListTool(),
            FileSearchTool(),
            FileWriteTool(),
            FileMoveTool(),
            FileDeleteTool(),
            FileEditTool(),
            ShellExecTool(),
            ShellSessionTool(),
            ShellRunTool(),
            ProcessListTool(),
            ProcessKillTool(),
            GitStatusTool(),
            GitDiffTool(),
            PackageInstallTool(),
            WorkspaceListTool(),
            WorkspaceReadTool(),
            WorkspaceSearchTool(),
            WorkspaceGrepTool(),
            WorkspaceWriteTool(),
            WorkspaceEditTool(),
            WorkspaceOpsTool(),
            TodoUpdateTool(),
        ):
            admin_registry.register(tool)
        for name, tool in list(admin_registry._tools.items()):
            alias_name = CODING_AGENT_TOOL_ALIASES.get(name)
            if alias_name:
                admin_registry.register(ToolAlias(tool, alias_name))
        self.admin_audit = AuditLog(self.temp / "audit-admin.jsonl")
        self.admin_executor = ToolExecutor(
            admin_registry,
            PermissionEngine("admin", interactive_approval=True, approval_provider=AllowApprovalProvider()),
            EventBus(),
            self.admin_audit,
            services={
                "core.workspace_root": self.temp,
                "core.shell_sessions": self.shell_sessions,
                "core.audit": self.admin_audit,
                "core.permissions": PermissionEngine(
                    "admin",
                    interactive_approval=True,
                    approval_provider=AllowApprovalProvider(),
                ),
            },
        )
        self.admin_permissions = self.admin_executor.permissions
        self.admin_executor.services["core.permissions"] = self.admin_permissions

    async def asyncTearDown(self):
        self.temp_context.__exit__(None, None, None)

    async def test_executes_valid_tool(self):
        result = await self.executor.execute(
            ToolRequest("core.echo", {"text": "hello"})
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(result.output, {"text": "hello"})

    async def test_rejects_invalid_arguments(self):
        result = await self.executor.execute(
            ToolRequest("core.echo", {"wrong": "hello"})
        )
        self.assertEqual(result.status, ToolStatus.FAILED)

    async def test_unknown_tool_is_audited_and_failed(self):
        result = await self.executor.execute(ToolRequest("missing.tool", {}))
        self.assertEqual(result.status, ToolStatus.FAILED)
        audit_text = (self.temp / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn("tool.request", audit_text)
        self.assertIn("tool.result", audit_text)

    async def test_timeout(self):
        class SlowTool:
            spec = ToolSpec(
                "test.slow",
                "slow",
                {"type": "object", "properties": {}, "additionalProperties": False},
                Capability.CORE_READ,
                RiskLevel.LOW,
                timeout_seconds=0.01,
            )

            async def invoke(self, arguments, context):
                import asyncio

                await asyncio.sleep(1)

        self.executor.registry.register(SlowTool())
        result = await self.executor.execute(ToolRequest("test.slow", {}))
        self.assertEqual(result.status, ToolStatus.TIMED_OUT)

    async def test_file_tools_round_trip(self):
        write_result = await self.admin_executor.execute(
            ToolRequest(
                "file.write",
                {"path": "notes/example.txt", "content": "alpha\nbeta\nalpha"},
            )
        )
        self.assertEqual(write_result.status, ToolStatus.SUCCEEDED)

        read_result = await self.executor.execute(
            ToolRequest("file.read", {"path": "notes/example.txt", "start_line": 2})
        )
        self.assertEqual(read_result.output["content"], "beta\nalpha")
        self.assertFalse(read_result.output["truncated"])

        edit_result = await self.admin_executor.execute(
            ToolRequest(
                "file.edit",
                {
                    "path": "notes/example.txt",
                    "old_text": "beta",
                    "new_text": "gamma",
                },
            )
        )
        self.assertEqual(edit_result.output["replacements"], 1)

        search_result = await self.executor.execute(
            ToolRequest("file.search", {"pattern": "alpha|gamma", "path": "notes"})
        )
        self.assertGreaterEqual(len(search_result.output["matches"]), 3)

        list_result = await self.executor.execute(
            ToolRequest("file.list", {"path": "notes", "recursive": True})
        )
        self.assertEqual(list_result.output["entries"][0]["path"], "notes/example.txt")

    async def test_file_read_reports_truncation_metadata(self):
        content = "\n".join(f"line {index}" for index in range(1, 201))
        await self.admin_executor.execute(
            ToolRequest("file.write", {"path": "notes/large.txt", "content": content})
        )

        result = await self.executor.execute(ToolRequest("file.read", {"path": "notes/large.txt"}))

        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["truncated"])
        self.assertEqual(result.output["total_lines"], 200)
        self.assertEqual(result.output["returned_lines"], 160)
        self.assertIn("[TRUNCATED: Output too long.", result.output["content"])

    async def test_file_read_sanitizes_file_content_output(self):
        await self.admin_executor.execute(
            ToolRequest(
                "file.write",
                {
                    "path": "notes/dirty.txt",
                    "content": "alpha\n\n\x1b[31mbeta\x1b[0m\n\n\ngamma\n",
                },
            )
        )

        result = await self.executor.execute(
            ToolRequest("file.read", {"path": "notes/dirty.txt"})
        )

        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertNotIn("\x1b", result.output["content"])
        self.assertNotIn("\n\n\n", result.output["content"])
        self.assertEqual(result.output["content"], "alpha\n\nbeta\n\ngamma")
        self.assertEqual(result.output["returned_lines"], 5)

    async def test_file_search_sanitizes_match_lines(self):
        await self.admin_executor.execute(
            ToolRequest(
                "file.write",
                {
                    "path": "notes/search.txt",
                    "content": "prefix \x1b[31mmatch\x1b[0m suffix\n",
                },
            )
        )

        result = await self.executor.execute(
            ToolRequest("file.search", {"pattern": "match", "path": "notes"})
        )

        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(result.output["matches"][0]["line"], "prefix match suffix")
        self.assertFalse(result.output["matches"][0]["line_truncated"])

    async def test_file_move_and_delete(self):
        await self.admin_executor.execute(
            ToolRequest("file.write", {"path": "drafts/item.txt", "content": "payload"})
        )
        move_result = await self.admin_executor.execute(
            ToolRequest(
                "file.move",
                {
                    "source_path": "drafts/item.txt",
                    "destination_path": "archive/item.txt",
                },
            )
        )
        self.assertEqual(move_result.status, ToolStatus.SUCCEEDED)
        self.assertTrue((self.temp / "archive" / "item.txt").exists())

        delete_result = await self.admin_executor.execute(
            ToolRequest("file.delete", {"path": "archive/item.txt"})
        )
        self.assertEqual(delete_result.status, ToolStatus.SUCCEEDED)
        self.assertFalse((self.temp / "archive" / "item.txt").exists())

    async def test_shell_exec_supports_dry_run(self):
        result = await self.admin_executor.execute(
            ToolRequest(
                "shell.exec",
                {"command": f'"{sys.executable}" -c "print(123)"', "dry_run": True},
            )
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["dry_run"])
        if sys.platform == "win32":
            self.assertIn("powershell", result.output["argv"][0].lower())
            self.assertIn("-NoProfile", result.output["argv"])
            self.assertIn("-NonInteractive", result.output["argv"])
        else:
            self.assertTrue(
                result.output["argv"][0].endswith("bash")
                or result.output["argv"][0] == "/bin/sh"
            )

    async def test_command_output_sanitizer_strips_ansi_and_truncates(self):
        raw = "start\n\n\x1b[31mred\x1b[0m\n" + ("line\n" * 220)
        cleaned, truncated = _sanitize_command_output(raw)

        self.assertTrue(truncated)
        self.assertNotIn("\x1b", cleaned)
        self.assertIn("red", cleaned)
        self.assertNotIn("\n\n\n", cleaned)
        self.assertIn("[TRUNCATED: Output too long.", cleaned)

    async def test_executor_sanitizes_command_style_output_after_tool_returns(self):
        registry = ToolRegistry()
        registry.register(DirtyShellRunTool())
        audit = AuditLog(self.temp / "audit-dirty-shell.jsonl")
        executor = ToolExecutor(
            registry,
            PermissionEngine("admin", interactive_approval=False),
            EventBus(),
            audit,
            services={"core.audit": audit},
        )
        result = await executor.execute(ToolRequest("demo.command.output", {}))
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertNotIn("\x1b", result.output["stdout"])
        self.assertNotIn("\x1b", result.output["stderr"])
        self.assertNotIn("\n\n\n", result.output["stdout"])
        self.assertNotIn("\x1b", result.output["sessions"][0]["stdout"])

    async def test_execute_many_runs_parallel_safe_batch(self):
        registry = ToolRegistry()
        registry.register(ParallelReadTool())
        audit = AuditLog(self.temp / "audit-parallel.jsonl")
        executor = ToolExecutor(
            registry,
            PermissionEngine("admin", interactive_approval=False),
            EventBus(),
            audit,
            services={"core.audit": audit},
        )
        results = await executor.execute_many(
            [
                ToolRequest("demo.parallel.read", {"value": "a"}),
                ToolRequest("demo.parallel.read", {"value": "b"}),
            ],
            parallel=True,
        )
        self.assertEqual([item.output["value"] for item in results], ["a", "b"])

    async def test_execute_many_rejects_non_parallel_safe_batch(self):
        registry = ToolRegistry()
        registry.register(DirtyShellRunTool())
        audit = AuditLog(self.temp / "audit-nonparallel.jsonl")
        executor = ToolExecutor(
            registry,
            PermissionEngine("admin", interactive_approval=False),
            EventBus(),
            audit,
            services={"core.audit": audit},
        )
        with self.assertRaises(ValueError):
            await executor.execute_many(
                [ToolRequest("demo.command.output", {})],
                parallel=True,
            )

    async def test_package_install_supports_dry_run(self):
        result = await self.admin_executor.execute(
            ToolRequest(
                "package.install",
                {
                    "manager": "pip",
                    "packages": ["requests"],
                    "dry_run": True,
                },
            )
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["dry_run"])
        self.assertEqual(result.output["argv"][:4], [sys.executable, "-m", "pip", "install"])

    async def test_process_tools_support_dry_run(self):
        list_result = await self.admin_executor.execute(
            ToolRequest("process.list", {"dry_run": True})
        )
        self.assertEqual(list_result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(list_result.output["dry_run"])

        kill_result = await self.admin_executor.execute(
            ToolRequest("process.kill", {"pid": 123, "dry_run": True})
        )
        self.assertEqual(kill_result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(kill_result.output["pid"], 123)

    async def test_git_tools_support_dry_run(self):
        status_result = await self.admin_executor.execute(
            ToolRequest("git.status", {"dry_run": True})
        )
        self.assertEqual(status_result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(status_result.output["argv"][:2], ["git", "status"])

        diff_result = await self.admin_executor.execute(
            ToolRequest("git.diff", {"dry_run": True, "pathspec": "src"})
        )
        self.assertEqual(diff_result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(diff_result.output["argv"][:2], ["git", "diff"])

    async def test_git_diff_truncates_with_head_and_tail(self):
        diff_body = "HEAD\n" + ("x" * 200) + "\nTAIL"
        completed = subprocess.CompletedProcess(
            args=["git", "diff"],
            returncode=0,
            stdout=diff_body,
            stderr="",
        )
        with patch("yue_core.builtin_tools._run_command_args", return_value=completed):
            result = await self.admin_executor.execute(
                ToolRequest("git.diff", {"max_chars": 80})
            )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["truncated"])
        self.assertIn("HEAD", result.output["diff"])
        self.assertIn("TAIL", result.output["diff"])
        self.assertTrue(
            "[TRUNCATED: Output too long." in result.output["diff"]
            or "...[truncated]..." in result.output["diff"]
        )

    async def test_workspace_tool_aliases_round_trip(self):
        write_result = await self.admin_executor.execute(
            ToolRequest(
                "workspace_write",
                {
                    "path": "workspace/sample.txt",
                    "content": "alpha\nbeta\n",
                    "mode": "create_only",
                },
            )
        )
        self.assertEqual(write_result.status, ToolStatus.SUCCEEDED)

        append_result = await self.admin_executor.execute(
            ToolRequest(
                "workspace_write",
                {
                    "path": "workspace/sample.txt",
                    "content": "gamma\n",
                    "mode": "append",
                },
            )
        )
        self.assertEqual(append_result.status, ToolStatus.SUCCEEDED)

        read_result = await self.executor.execute(
            ToolRequest("workspace_read", {"path": "workspace/sample.txt"})
        )
        self.assertIn("gamma", read_result.output["content"])

        edit_result = await self.admin_executor.execute(
            ToolRequest(
                "workspace_edit",
                {
                    "path": "workspace/sample.txt",
                    "search_block": "beta",
                    "replace_block": "delta",
                },
            )
        )
        self.assertEqual(edit_result.output["replacements"], 1)

        grep_result = await self.executor.execute(
            ToolRequest("workspace_grep", {"pattern": "delta", "path": "workspace"})
        )
        self.assertEqual(grep_result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(grep_result.output["matches"][0]["path"], "workspace/sample.txt")

        search_result = await self.executor.execute(
            ToolRequest("workspace_search", {"query": "sample", "type": "path"})
        )
        self.assertTrue(any(item["path"] == "workspace/sample.txt" for item in search_result.output["matches"]))

        list_result = await self.executor.execute(
            ToolRequest("workspace_list", {"path": "workspace", "depth": 2})
        )
        self.assertTrue(any(item["path"] == "workspace/sample.txt" for item in list_result.output["entries"]))

    async def test_workspace_read_sanitizes_file_content_output(self):
        await self.admin_executor.execute(
            ToolRequest(
                "workspace.write",
                {
                    "path": "workspace/dirty.txt",
                    "content": "one\n\n\x1b[32mtwo\x1b[0m\n\n\nthree\n",
                    "mode": "create_only",
                },
            )
        )

        result = await self.executor.execute(
            ToolRequest("workspace.read", {"path": "workspace/dirty.txt"})
        )

        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(result.output["path"], "workspace/dirty.txt")
        self.assertEqual(result.output["content"], "one\n\ntwo\n\nthree")
        self.assertEqual(result.output["returned_lines"], 5)
        self.assertNotIn("\x1b", result.output["content"])
        self.assertNotIn("\n\n\n", result.output["content"])

    async def test_workspace_grep_sanitizes_match_lines(self):
        await self.admin_executor.execute(
            ToolRequest(
                "workspace.write",
                {
                    "path": "workspace/search.txt",
                    "content": "start \x1b[32mneedle\x1b[0m end\n",
                    "mode": "create_only",
                },
            )
        )

        result = await self.executor.execute(
            ToolRequest("workspace.grep", {"pattern": "needle", "path": "workspace"})
        )

        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(result.output["matches"][0]["line"], "start needle end")
        self.assertFalse(result.output["matches"][0]["line_truncated"])

    async def test_workspace_ops_and_todo_update(self):
        await self.admin_executor.execute(
            ToolRequest(
                "workspace.write",
                {"path": "drafts/todo.txt", "content": "payload", "mode": "create_only"},
            )
        )

        mkdir_result = await self.admin_executor.execute(
            ToolRequest("workspace.ops", {"action": "mkdir", "from": "archive"})
        )
        self.assertEqual(mkdir_result.status, ToolStatus.SUCCEEDED)

        copy_result = await self.admin_executor.execute(
            ToolRequest(
                "workspace.ops",
                {"action": "copy", "from": "drafts/todo.txt", "to": "archive/todo.txt"},
            )
        )
        self.assertEqual(copy_result.status, ToolStatus.SUCCEEDED)

        trash_result = await self.admin_executor.execute(
            ToolRequest("workspace.ops", {"action": "delete_to_trash", "from": "drafts/todo.txt"})
        )
        self.assertEqual(trash_result.status, ToolStatus.SUCCEEDED)
        self.assertFalse((self.temp / "drafts" / "todo.txt").exists())

        todo_result = await self.executor.execute(
            ToolRequest(
                "todo_update",
                {"items": [{"text": "audit runtime", "done": False}]},
                session_id="session-1",
            )
        )
        self.assertEqual(todo_result.status, ToolStatus.SUCCEEDED)
        self.assertEqual(todo_result.output["session_id"], "session-1")

    async def test_shell_run_supports_dry_run(self):
        result = await self.admin_executor.execute(
            ToolRequest(
                "shell_run",
                {"command": f'"{sys.executable}" -c "print(123)"', "timeout": 5, "dry_run": True},
            )
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["dry_run"])
        self.assertEqual(result.output["risk_level"], "high")
        if sys.platform == "win32":
            self.assertIn("-NoProfile", result.output["argv"])

    async def test_approval_request_tool_returns_structured_approval(self):
        topics = []

        async def collect(event):
            topics.append(event.topic)

        self.executor.events.subscribe("approval.*", collect)
        result = await self.executor.execute(
            ToolRequest(
                "approval.request",
                {
                    "action_description": "Allow deleting temp files",
                    "risk_level": "medium",
                },
                actor="model",
                session_id="session-1",
            )
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["approved"])
        self.assertEqual(result.output["outcome"], "allow")
        self.assertEqual(topics, ["approval.requested", "approval.resolved"])
        audit_text = (self.temp / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn("approval.requested", audit_text)
        self.assertIn("approval.resolved", audit_text)

    async def test_ask_user_approval_alias_returns_structured_approval(self):
        result = await self.executor.execute(
            ToolRequest(
                "ask_user_approval",
                {
                    "action_description": "Allow deleting temp files",
                    "risk_level": "medium",
                },
                actor="model",
                session_id="session-1",
            )
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["approved"])
        self.assertEqual(result.output["outcome"], "allow")

    async def test_shell_session_supports_dry_run(self):
        result = await self.admin_executor.execute(
            ToolRequest(
                "shell_session",
                {
                    "action": "start",
                    "session_id": "dev-server",
                    "command": f'"{sys.executable}" -m http.server',
                    "dry_run": True,
                },
            )
        )
        self.assertEqual(result.status, ToolStatus.SUCCEEDED)
        self.assertTrue(result.output["dry_run"])
        self.assertEqual(result.output["session_id"], "dev-server")
        if sys.platform == "win32":
            self.assertIn("-NoProfile", result.output["argv"])

    async def test_shell_session_manager_start_read_stop(self):
        fake_process = FakeProcess(stdout=b"hello\n", stderr=b"\x1b[31mwarn\x1b[0m\n")
        manager = ShellSessionManager()
        with patch("yue_core.shell_sessions.asyncio.create_subprocess_exec", return_value=fake_process):
            started = await manager.start("dev-server", "echo hi", self.temp)
            await asyncio.sleep(0)
            snapshot = await manager.read("dev-server")
            listed = await manager.list()
            stopped = await manager.stop("dev-server")

        self.assertEqual(started["session_id"], "dev-server")
        self.assertIn("hello", snapshot["stdout"])
        self.assertIn("warn", snapshot["stderr"])
        self.assertNotIn("\x1b", snapshot["stderr"])
        self.assertEqual(len(listed), 1)
        self.assertFalse(stopped["running"])
        self.assertTrue(fake_process.killed)

    async def test_shell_session_tool_emits_events_and_audit(self):
        fake_process = FakeProcess(stdout=b"hello\n")
        topics = []

        async def collect(event):
            topics.append(event.topic)

        self.admin_executor.events.subscribe("shell.session.*", collect)
        with patch("yue_core.shell_sessions.asyncio.create_subprocess_exec", return_value=fake_process):
            started = await self.admin_executor.execute(
                ToolRequest(
                    "shell.session",
                    {"action": "start", "session_id": "dev-server", "command": "echo hi"},
                )
            )
            read = await self.admin_executor.execute(
                ToolRequest("shell.session", {"action": "read", "session_id": "dev-server"})
            )
            listed = await self.admin_executor.execute(
                ToolRequest("shell.session", {"action": "list"})
            )
            stopped = await self.admin_executor.execute(
                ToolRequest("shell.session", {"action": "stop", "session_id": "dev-server"})
            )

        self.assertEqual(started.status, ToolStatus.SUCCEEDED)
        self.assertEqual(read.status, ToolStatus.SUCCEEDED)
        self.assertEqual(listed.status, ToolStatus.SUCCEEDED)
        self.assertEqual(stopped.status, ToolStatus.SUCCEEDED)
        self.assertEqual(
            topics,
            [
                "shell.session.started",
                "shell.session.read",
                "shell.session.listed",
                "shell.session.stopped",
            ],
        )
        audit_text = (self.temp / "audit-admin.jsonl").read_text(encoding="utf-8")
        self.assertIn("shell.session.start", audit_text)
        self.assertIn("shell.session.read", audit_text)
        self.assertIn("shell.session.list", audit_text)
        self.assertIn("shell.session.stop", audit_text)


if __name__ == "__main__":
    unittest.main()
