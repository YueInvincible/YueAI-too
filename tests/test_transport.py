import io
import json
import os
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from yue_core.app import YueCore
from yue_core.config import Settings, load_settings
from yue_core.contracts import Capability, RiskLevel, ToolRequest, ToolSpec
from yue_core.transport import JsonLineServer
from tests.support import workspace_temp_dir


class AllowApprovalProvider:
    async def request_approval(self, request, spec, reason):
        return True


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_invoke_request(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "1",
                            "method": "tools.invoke",
                            "params": {
                                "name": "core.echo",
                                "arguments": {"text": "hello"},
                            },
                        }
                    )
                )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["output"]["text"], "hello")

    async def test_invoke_many_parallel_request(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "batch",
                            "method": "tools.invoke_many",
                            "params": {
                                "parallel": True,
                                "calls": [
                                    {
                                        "name": "workspace.read",
                                        "arguments": {"path": "PROJECT_HANDOFF.md"},
                                    },
                                    {
                                        "name": "workspace.read",
                                        "arguments": {"path": "docs/notes/agent_start_here.md"},
                                    },
                                ],
                            },
                        }
                    )
                )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"]["parallel"])
        self.assertEqual(len(response["result"]["results"]), 2)
        self.assertIn("YueAI Project Handoff", response["result"]["results"][0]["output"]["content"])
        self.assertIn("Agent Start Here", response["result"]["results"][1]["output"]["content"])

    async def test_accepts_utf8_bom(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    "\ufeff" + json.dumps({"id": "1", "method": "tools.list"})
                )
        self.assertTrue(response["ok"])
        names = {item["name"] for item in response["result"]}
        self.assertIn("file.read", names)
        self.assertIn("workspace.read", names)
        self.assertIn("workspace_read", names)
        self.assertIn("shell.exec", names)
        self.assertIn("shell.run", names)
        self.assertIn("shell_run", names)
        self.assertIn("shell.session", names)
        self.assertIn("shell_session", names)
        self.assertIn("ask_user_approval", names)
        self.assertIn("git.status", names)
        self.assertIn("git_status", names)
        self.assertIn("process.list", names)
        self.assertIn("todo.update", names)
        self.assertIn("todo_update", names)
        tools_by_name = {item["name"]: item for item in response["result"]}
        self.assertEqual(tools_by_name["workspace.read"]["output_kind"], "file_content")
        self.assertTrue(tools_by_name["workspace.read"]["metadata"]["parallel_safe"])
        self.assertIn(
            "line-range metadata",
            tools_by_name["workspace.read"]["model_description"],
        )
        self.assertEqual(tools_by_name["shell.run"]["output_kind"], "command_output")
        self.assertFalse(tools_by_name["shell.run"]["metadata"]["parallel_safe"])
        self.assertIn(
            "sanitized command-style output",
            tools_by_name["shell.run"]["model_description"],
        )

    async def test_tools_list_can_filter_for_coding_agent_role(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "coding-tools",
                            "method": "tools.list",
                            "params": {"provider_role": "coding_agent"},
                        }
                    )
                )
        self.assertTrue(response["ok"])
        names = {item["name"] for item in response["result"]}
        self.assertIn("workspace_read", names)
        self.assertIn("shell_run", names)
        self.assertIn("ask_user_approval", names)
        self.assertIn("git_diff", names)
        self.assertIn("todo_update", names)
        self.assertNotIn("workspace.read", names)
        self.assertNotIn("shell.run", names)
        self.assertNotIn("file.read", names)
        self.assertNotIn("shell.exec", names)
        self.assertNotIn("approval.request", names)

    async def test_tools_guide_returns_coding_agent_playbook(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "guide",
                            "method": "tools.guide",
                            "params": {"provider_role": "coding_agent"},
                        }
                    )
                )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["provider_role"], "coding_agent")
        self.assertIn("Start with read-only inspection", response["result"]["workflow"][0])
        tool_names = {item["name"] for item in response["result"]["tools"]}
        self.assertIn("workspace_read", tool_names)
        self.assertIn("workspace_edit", tool_names)
        self.assertIn("shell_run", tool_names)
        self.assertIn("ask_user_approval", tool_names)
        self.assertIn("Coding agent tool guide:", response["result"]["text"])
        self.assertIn("workspace_read:", response["result"]["text"])

    async def test_prompt_preview_returns_runtime_system_instruction(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "prompt-preview",
                            "method": "conversations.prompt_preview",
                            "params": {"provider_role": "coding_agent"},
                        }
                    )
                )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["provider_role"], "coding_agent")
        self.assertEqual(response["result"]["prompt_profile"], "coding_agent")
        self.assertIn("Inspect relevant files before editing.", response["result"]["system_instruction"])
        self.assertIn("Coding agent tool guide:", response["result"]["system_instruction"])
        self.assertGreater(response["result"]["tool_count"], 0)

    async def test_agent_bundle_returns_exportable_coding_agent_snapshot(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "agent-bundle",
                            "method": "agents.bundle",
                            "params": {"provider_role": "coding_agent"},
                        }
                    )
                )
        self.assertTrue(response["ok"])
        bundle = response["result"]
        self.assertEqual(bundle["provider_role"], "coding_agent")
        self.assertEqual(bundle["route"]["prompt_profile"], "coding_agent")
        self.assertIn("system_instruction", bundle["prompt_preview"])
        self.assertIn("Coding agent tool guide:", bundle["prompt_preview"]["system_instruction"])
        self.assertIn("tools", bundle)
        self.assertIn("tool_guide", bundle)
        self.assertIn("codex_manifest", bundle)
        self.assertEqual(bundle["codex_manifest"]["provider_role"], "coding_agent")
        self.assertIn("system_prompt", bundle["codex_manifest"])
        self.assertGreater(len(bundle["codex_manifest"]["tools"]), 0)
        tool_names = {item["name"] for item in bundle["tools"]}
        self.assertIn("workspace_read", tool_names)
        self.assertIn("shell_run", tool_names)

    async def test_agent_starter_pack_returns_copy_ready_agent_payload(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "agent-starter-pack",
                            "method": "agents.starter_pack",
                            "params": {"provider_role": "coding_agent"},
                        }
                    )
                )
        self.assertTrue(response["ok"])
        pack = response["result"]
        self.assertEqual(pack["provider_role"], "coding_agent")
        self.assertIn("starter_prompt", pack)
        self.assertIn("system_prompt", pack)
        self.assertIn("codex_manifest", pack)
        self.assertIn("integration_checklist", pack)
        self.assertGreater(len(pack["integration_checklist"]), 0)
        self.assertIn("# YueAI coding_agent starter pack", pack["text"])
        self.assertIn("## Codex-style tool manifest", pack["text"])

    async def test_agent_starter_pack_can_return_focused_format_slice(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "agent-starter-pack-system",
                            "method": "agents.starter_pack",
                            "params": {
                                "provider_role": "coding_agent",
                                "format": "system-prompt",
                            },
                        }
                    )
                )
        self.assertTrue(response["ok"])
        pack = response["result"]
        self.assertEqual(pack["provider_role"], "coding_agent")
        self.assertEqual(pack["format"], "system-prompt")
        self.assertIn("Coding agent tool guide:", pack["content"])

    async def test_conversation_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                created = await server.handle_line(
                    json.dumps(
                        {
                            "id": "create",
                            "method": "conversations.create",
                            "params": {"title": "Test"},
                        }
                    )
                )
                conversation_id = created["result"]["id"]
                sent = await server.handle_line(
                    json.dumps(
                        {
                            "id": "send",
                            "method": "conversations.send",
                            "params": {
                                "conversation_id": conversation_id,
                                "content": "hello",
                                "run_id": "transport-run",
                            },
                        }
                    )
                )
                history = await server.handle_line(
                    json.dumps(
                        {
                            "id": "history",
                            "method": "conversations.messages",
                            "params": {"conversation_id": conversation_id},
                        }
                    )
                )
        self.assertEqual(sent["result"]["message"]["content"], "Echo: hello")
        self.assertEqual(len(history["result"]), 2)

    async def test_provider_health_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps({"id": "health", "method": "providers.health"})
                )
        self.assertTrue(response["ok"])
        self.assertTrue(any(item["provider"] == "fake.echo" for item in response["result"]))

    async def test_approval_request_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.permissions.interactive_approval = True
            core = YueCore(settings, approval_provider=AllowApprovalProvider())
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "approve",
                            "method": "approval.request",
                            "params": {
                                "action_description": "Allow shell action",
                                "risk_level": "high",
                                "actor": "model",
                                "session_id": "conversation-1",
                            },
                        }
                    )
                )
        self.assertTrue(response["ok"])
        self.assertTrue(response["result"]["output"]["approved"])

    async def test_allow_all_cmd_grant_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.permissions.profile = "assist"
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                updated = await server.handle_line(
                    json.dumps(
                        {
                            "id": "grant",
                            "method": "permissions.allow_all_cmd.set",
                            "params": {
                                "session_id": "conversation-1",
                                "allowed": True,
                                "actor": "ui",
                            },
                        }
                    )
                )
                current = await server.handle_line(
                    json.dumps(
                        {
                            "id": "get",
                            "method": "permissions.allow_all_cmd.get",
                            "params": {"session_id": "conversation-1"},
                        }
                    )
                )
                invoke = await server.handle_line(
                    json.dumps(
                        {
                            "id": "invoke",
                            "method": "tools.invoke",
                            "params": {
                                "name": "shell.run",
                                "arguments": {
                                    "command": "echo hi",
                                    "dry_run": True,
                                },
                                "actor": "model",
                                "session_id": "conversation-1",
                            },
                        }
                    )
                )
        self.assertTrue(updated["ok"])
        self.assertTrue(current["ok"])
        self.assertTrue(current["result"]["allow_all_cmd"])
        self.assertTrue(invoke["ok"])
        self.assertEqual(invoke["result"]["status"], "succeeded")

    async def test_allow_all_cmd_grant_rejects_model_actor(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.permissions.profile = "assist"
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "deny-model",
                            "method": "permissions.allow_all_cmd.set",
                            "params": {
                                "session_id": "conversation-1",
                                "allowed": True,
                                "actor": "model",
                            },
                        }
                    )
                )
        self.assertFalse(response["ok"])
        self.assertIn("model actor cannot change allow-all-cmd", response["error"])

    async def test_allow_all_cmd_grant_rejects_observe_profile(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.permissions.profile = "observe"
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                response = await server.handle_line(
                    json.dumps(
                        {
                            "id": "deny-observe",
                            "method": "permissions.allow_all_cmd.set",
                            "params": {
                                "session_id": "conversation-1",
                                "allowed": True,
                                "actor": "desktop-ui",
                            },
                        }
                    )
                )
        self.assertFalse(response["ok"])
        self.assertIn("observe profile cannot change allow-all-cmd", response["error"])

    async def test_pending_approval_bridge_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                approvals = core.services["core.approvals"]
                pending_task = asyncio.create_task(
                    approvals.request_approval(
                        ToolRequest(
                            tool_name="shell.run",
                            arguments={"command": "git push"},
                            actor="model",
                            session_id="conversation-1",
                        ),
                        ToolSpec(
                            name="shell.run",
                            description="Run a shell command",
                            input_schema={},
                            capability=Capability.SHELL_EXECUTE,
                            risk=RiskLevel.HIGH,
                        ),
                        "Command requires explicit approval",
                    )
                )
                await asyncio.sleep(0)
                listed = await server.handle_line(
                    json.dumps(
                        {
                            "id": "pending",
                            "method": "approval.pending.list",
                        }
                    )
                )
                approval_id = listed["result"][0]["approval_id"]
                responded = await server.handle_line(
                    json.dumps(
                        {
                            "id": "respond",
                            "method": "approval.respond",
                            "params": {
                                "approval_id": approval_id,
                                "approved": True,
                            },
                        }
                    )
                )
                decision = await pending_task
        self.assertTrue(listed["ok"])
        self.assertEqual(listed["result"][0]["tool_name"], "shell.run")
        self.assertTrue(responded["ok"])
        self.assertTrue(responded["result"]["approved"])
        self.assertTrue(decision)

    async def test_tool_activity_snapshot_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                approvals = core.services["core.approvals"]
                pending_task = asyncio.create_task(
                    approvals.request_approval(
                        ToolRequest(
                            tool_name="shell.run",
                            arguments={"command": "git push"},
                            actor="model",
                            session_id="conversation-1",
                        ),
                        ToolSpec(
                            name="shell.run",
                            description="Run a shell command",
                            input_schema={},
                            capability=Capability.SHELL_EXECUTE,
                            risk=RiskLevel.HIGH,
                        ),
                        "Command requires explicit approval",
                    )
                )
                await asyncio.sleep(0)
                listed = await server.handle_line(
                    json.dumps(
                        {
                            "id": "pending",
                            "method": "approval.pending.list",
                        }
                    )
                )
                snapshot = None
                for _ in range(20):
                    snapshot = await server.handle_line(
                        json.dumps(
                            {
                                "id": "tool-activity",
                                "method": "tool.activity.snapshot",
                            }
                        )
                    )
                    if snapshot["result"]["items"]:
                        break
                    await asyncio.sleep(0.01)
                approval_id = listed["result"][0]["approval_id"]
                responded = await server.handle_line(
                    json.dumps(
                        {
                            "id": "respond",
                            "method": "approval.respond",
                            "params": {
                                "approval_id": approval_id,
                                "approved": True,
                            },
                        }
                    )
                )
                decision = await pending_task
        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["result"]["status"], "Approval requested for shell.run")
        self.assertEqual(len(snapshot["result"]["items"]), 1)
        self.assertEqual(snapshot["result"]["items"][0]["tool_name"], "shell.run")
        self.assertEqual(snapshot["result"]["items"][0]["status"], "waiting_approval")
        self.assertTrue(responded["ok"])
        self.assertTrue(decision)

    async def test_conversation_settings_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                current = await server.handle_line(
                    json.dumps({"id": "get", "method": "settings.conversation.get"})
                )
                updated = await server.handle_line(
                    json.dumps(
                        {
                            "id": "update",
                            "method": "settings.conversation.update",
                            "params": {
                                "default_provider": "fake.echo",
                                "routes": {
                                    "chat": {
                                        "provider": "fake.echo",
                                        "prompt_profile": "default",
                                    },
                                    "coding_agent": {
                                        "provider": "fake.echo",
                                        "prompt_profile": "coding_agent",
                                    },
                                },
                                "prompt_profiles": {
                                    "default": {
                                        "personality": "Concise",
                                        "system_instruction": "",
                                        "tool_instruction": "",
                                        "response_instruction": "",
                                    },
                                    "coding_agent": {
                                        "personality": "",
                                        "system_instruction": "Code carefully",
                                        "tool_instruction": "",
                                        "response_instruction": "",
                                    },
                                },
                            },
                        }
                    )
                )
        self.assertTrue(current["ok"])
        self.assertEqual(
            updated["result"]["prompt_profiles"]["default"]["personality"],
            "Concise",
        )

    async def test_conversation_settings_persist_round_trip(self):
        with workspace_temp_dir() as temp:
            config_path = temp / "config.local.toml"
            settings = Settings()
            settings.core.data_dir = temp
            settings.config_path = config_path
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                updated = await server.handle_line(
                    json.dumps(
                        {
                            "id": "persist",
                            "method": "settings.conversation.update",
                            "params": {
                                "persist": True,
                                "default_provider": "fake.echo",
                                "routes": {
                                    "chat": {
                                        "provider": "fake.echo",
                                        "prompt_profile": "default",
                                    },
                                    "coding_agent": {
                                        "provider": "fake.echo",
                                        "prompt_profile": "coding_agent",
                                    },
                                },
                                "prompt_profiles": {
                                    "default": {
                                        "personality": "Saved",
                                        "system_instruction": "",
                                        "tool_instruction": "",
                                        "response_instruction": "",
                                    },
                                    "coding_agent": {
                                        "personality": "",
                                        "system_instruction": "Persisted",
                                        "tool_instruction": "",
                                        "response_instruction": "",
                                    },
                                },
                            },
                        }
                    )
                )
            reloaded = load_settings(config_path, base_dir=temp)

        self.assertTrue(updated["ok"])
        self.assertEqual(
            reloaded.conversation.prompt_profiles["default"]["personality"],
            "Saved",
        )
        self.assertEqual(
            reloaded.conversation.prompt_profiles["coding_agent"][
                "system_instruction"
            ],
            "Persisted",
        )

    async def test_openai_compatible_settings_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
            settings.plugins.enabled = ["openai.compat"]
            settings.plugins.options = {
                "openai.compat": {
                    "providers": [
                        {
                            "provider_name": "ollama.chat",
                            "backend": "ollama",
                            "base_url": "http://127.0.0.1:11434/v1",
                            "model": "qwen2.5:7b-instruct",
                        }
                    ]
                }
            }
            settings.conversation.default_provider = "ollama.chat"
            settings.conversation.routes["chat"] = {
                "provider": "ollama.chat",
                "prompt_profile": "default",
            }
            settings.conversation.routes["coding_agent"] = {
                "provider": "ollama.chat",
                "prompt_profile": "coding_agent",
            }
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                current = await server.handle_line(
                    json.dumps(
                        {
                            "id": "providers-get",
                            "method": "settings.providers.openai_compat.get",
                        }
                    )
                )
                updated = await server.handle_line(
                    json.dumps(
                        {
                            "id": "providers-update",
                            "method": "settings.providers.openai_compat.update",
                            "params": {
                                "providers": [
                                    {
                                        "provider_name": "ollama.chat",
                                        "backend": "ollama",
                                        "base_url": "http://127.0.0.1:11434/v1",
                                        "model": "qwen2.5-coder:7b",
                                        "timeout_seconds": 90,
                                        "health_timeout_seconds": 4,
                                        "temperature": 0.4,
                                        "max_tokens": 2048,
                                    }
                                ]
                            },
                        }
                    )
                )
        self.assertTrue(current["ok"])
        self.assertEqual(current["result"]["providers"][0]["provider_name"], "ollama.chat")
        self.assertEqual(updated["result"]["providers"][0]["provider_name"], "ollama.chat")
        self.assertEqual(updated["result"]["providers"][0]["model"], "qwen2.5-coder:7b")

    async def test_anthropic_messages_settings_round_trip(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with workspace_temp_dir() as temp:
                settings = Settings()
                settings.core.data_dir = temp
                settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
                settings.plugins.enabled = ["anthropic.messages"]
                settings.plugins.options = {
                    "anthropic.messages": {
                        "providers": [
                            {
                                "provider_name": "claude.coder",
                                "backend": "anthropic",
                                "base_url": "https://api.anthropic.com",
                                "model": "claude-sonnet-4-20250514",
                                "api_key_env": "ANTHROPIC_API_KEY",
                            }
                        ]
                    }
                }
                settings.conversation.default_provider = "claude.coder"
                settings.conversation.routes["chat"] = {
                    "provider": "claude.coder",
                    "prompt_profile": "default",
                }
                settings.conversation.routes["coding_agent"] = {
                    "provider": "claude.coder",
                    "prompt_profile": "coding_agent",
                }
                core = YueCore(settings)
                server = JsonLineServer(core)
                async with core:
                    current = await server.handle_line(
                        json.dumps(
                            {
                                "id": "anthropic-get",
                                "method": "settings.providers.anthropic_messages.get",
                            }
                        )
                    )
                    updated = await server.handle_line(
                        json.dumps(
                            {
                                "id": "anthropic-update",
                                "method": "settings.providers.anthropic_messages.update",
                                "params": {
                                    "providers": [
                                        {
                                            "provider_name": "claude.coder",
                                            "backend": "anthropic",
                                            "base_url": "https://api.anthropic.com",
                                            "model": "claude-3-7-sonnet-latest",
                                            "api_key_env": "ANTHROPIC_API_KEY",
                                            "timeout_seconds": 90,
                                            "health_timeout_seconds": 4,
                                            "temperature": 0.2,
                                            "max_tokens": 2048,
                                            "anthropic_version": "2023-06-01",
                                        }
                                    ]
                                },
                            }
                        )
                    )
        self.assertTrue(current["ok"])
        self.assertEqual(current["result"]["providers"][0]["provider_name"], "claude.coder")
        self.assertEqual(updated["result"]["providers"][0]["provider_name"], "claude.coder")
        self.assertEqual(updated["result"]["providers"][0]["model"], "claude-3-7-sonnet-latest")

    async def test_active_provider_settings_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
            settings.plugins.enabled = ["llama.cpp"]
            settings.plugins.options = {
                "llama.cpp": {
                    "provider_name": "localhost.chat",
                    "base_url": "http://127.0.0.1:8080",
                    "model": "Qwen3-4B-Q5_K_M.gguf",
                }
            }
            settings.conversation.default_provider = "localhost.chat"
            settings.conversation.routes["chat"] = {
                "provider": "localhost.chat",
                "prompt_profile": "default",
            }
            settings.conversation.routes["coding_agent"] = {
                "provider": "localhost.chat",
                "prompt_profile": "coding_agent",
            }
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                current = await server.handle_line(
                    json.dumps(
                        {
                            "id": "active-provider-get",
                            "method": "settings.providers.active.get",
                        }
                    )
                )
                updated = await server.handle_line(
                    json.dumps(
                        {
                            "id": "active-provider-update",
                            "method": "settings.providers.active.update",
                            "params": {
                                "provider": {
                                    "kind": "ollama",
                                    "provider_name": "ollama.chat",
                                    "host": "127.0.0.1",
                                    "port": 11434,
                                    "model": "qwen2.5-coder:7b",
                                    "temperature": 0.5,
                                    "max_tokens": 2048,
                                }
                            },
                        }
                    )
                )
        self.assertTrue(current["ok"])
        self.assertEqual(current["result"]["active_provider"]["kind"], "llama.cpp")
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["result"]["active_provider"]["kind"], "ollama")
        self.assertEqual(updated["result"]["conversation"]["default_provider"], "ollama.chat")

    async def test_active_provider_catalog_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                with patch("yue_core.app.OpenAICompatibleProvider.health", return_value={
                    "ok": True,
                    "reachable": True,
                    "models": ["gpt-4.1-mini", "gpt-4.1"],
                }):
                    response = await server.handle_line(
                        json.dumps(
                            {
                                "id": "active-provider-catalog",
                                "method": "settings.providers.active.catalog",
                                "params": {
                                    "provider": {
                                        "kind": "openai",
                                        "provider_name": "openai.chat",
                                        "api_key_env": "OPENAI_API_KEY",
                                    }
                                },
                            }
                        )
                    )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["selected_model"], "gpt-4.1-mini")
        self.assertEqual(response["result"]["models"][0], "gpt-4.1-mini")

    async def test_desktop_round_trip(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                attached = await server.handle_line(
                    json.dumps(
                        {
                            "id": "attach",
                            "method": "desktop.attach",
                            "params": {
                                "session_id": "desktop-ui",
                                "metadata": {"surface": "test"},
                            },
                        }
                    )
                )
                toggled = await server.handle_line(
                    json.dumps(
                        {
                            "id": "toggle",
                            "method": "desktop.command",
                            "params": {
                                "command": "hotkey.toggle_console",
                                "source": "test",
                            },
                        }
                    )
                )
                state = await server.handle_line(
                    json.dumps({"id": "state", "method": "desktop.state"})
                )
        self.assertEqual(attached["result"]["session_id"], "desktop-ui")
        self.assertTrue(toggled["result"]["state"]["console_open"])
        self.assertEqual(state["result"]["attached_session_ids"], ["desktop-ui"])

    async def test_serve_forwards_desktop_events(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            stdin = io.StringIO(
                json.dumps(
                    {
                        "id": "attach",
                        "method": "desktop.attach",
                        "params": {
                            "session_id": "desktop-ui",
                            "metadata": {"surface": "test"},
                        },
                    }
                )
                + "\n"
            )
            stdout = io.StringIO()
            core = YueCore(settings)
            server = JsonLineServer(core, stdin=stdin, stdout=stdout)
            await server.serve()

        messages = [
            json.loads(line)
            for line in stdout.getvalue().splitlines()
            if line.strip()
        ]
        event_topics = [
            message["event"]["topic"]
            for message in messages
            if "event" in message
        ]
        self.assertIn("desktop.session.attached", event_topics)
        self.assertIn("desktop.state.changed", event_topics)
        self.assertTrue(any(message.get("id") == "attach" for message in messages))

    async def test_serve_forwards_tool_events(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            stdin = io.StringIO(
                json.dumps(
                    {
                        "id": "invoke",
                        "method": "tools.invoke",
                        "params": {
                            "name": "process.list",
                            "arguments": {"dry_run": True},
                            "actor": "ui",
                            "session_id": "desktop-ui",
                        },
                    }
                )
                + "\n"
            )
            stdout = io.StringIO()
            core = YueCore(settings)
            server = JsonLineServer(core, stdin=stdin, stdout=stdout)
            await server.serve()

        messages = [
            json.loads(line)
            for line in stdout.getvalue().splitlines()
            if line.strip()
        ]
        event_topics = [
            message["event"]["topic"]
            for message in messages
            if "event" in message
        ]
        self.assertIn("tool.started", event_topics)
        self.assertIn("tool.finished", event_topics)
        self.assertTrue(any(message.get("id") == "invoke" for message in messages))


if __name__ == "__main__":
    unittest.main()
