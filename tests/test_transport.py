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
        self.assertIn("shell.exec", names)
        self.assertIn("shell.run", names)
        self.assertIn("shell.session", names)
        self.assertIn("git.status", names)
        self.assertIn("process.list", names)
        self.assertIn("todo.update", names)

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


if __name__ == "__main__":
    unittest.main()
