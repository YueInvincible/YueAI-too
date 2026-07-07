import unittest
import asyncio
import os
from pathlib import Path
from unittest.mock import patch

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings
from yue_core.contracts import ModelEvent, ModelEventType
from tests.test_tools import FakeProcess


class BlockingProvider:
    name = "test.shutdown"

    async def generate(self, request, context):
        await asyncio.sleep(60)
        yield ModelEvent(ModelEventType.FINISH)


class AppLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_core_can_restart_cleanly(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            await core.stop()
            await core.start()
            result = await core.invoke("core.health", {})
            await core.stop()
        self.assertTrue(result.ok)

    async def test_stop_cancels_active_conversation(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            core.providers.register(BlockingProvider(), owner="test")
            conversation = await core.conversations.create()
            started = asyncio.Event()

            async def mark_started(event):
                if event.payload["run_id"] == "shutdown-run":
                    started.set()

            unsubscribe = core.events.subscribe(
                "conversation.run.started", mark_started
            )
            task = asyncio.create_task(
                core.conversations.send(
                    conversation.id,
                    "wait",
                    provider_name="test.shutdown",
                    run_id="shutdown-run",
                )
            )
            await asyncio.wait_for(started.wait(), timeout=1)
            await core.stop()
            self.assertTrue(task.cancelled())
            unsubscribe()

    async def test_update_conversation_settings_updates_runtime_routes(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            snapshot = await core.update_conversation_settings(
                {
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
                            "personality": "Short",
                            "system_instruction": "",
                            "tool_instruction": "",
                            "response_instruction": "",
                        },
                        "coding_agent": {
                            "personality": "",
                            "system_instruction": "Write code",
                            "tool_instruction": "",
                            "response_instruction": "",
                        },
                    },
                }
            )
            await core.stop()
        self.assertEqual(
            snapshot["prompt_profiles"]["coding_agent"]["system_instruction"],
            "Write code",
        )

    async def test_update_openai_compatible_settings_reloads_provider_registry(self):
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
            await core.start()
            snapshot = await core.update_openai_compatible_settings(
                {
                    "providers": [
                        {
                            "provider_name": "ollama.chat",
                            "backend": "ollama",
                            "base_url": "http://127.0.0.1:11434/v1",
                            "model": "qwen2.5-coder:7b",
                        }
                    ]
                }
            )
            await core.stop()
        self.assertEqual(snapshot["providers"][0]["provider_name"], "ollama.chat")
        self.assertEqual(snapshot["providers"][0]["model"], "qwen2.5-coder:7b")

    async def test_update_anthropic_messages_settings_reloads_provider_registry(self):
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
                await core.start()
                snapshot = await core.update_anthropic_messages_settings(
                    {
                        "providers": [
                            {
                                "provider_name": "claude.coder",
                                "backend": "anthropic",
                                "base_url": "https://api.anthropic.com",
                                "model": "claude-3-7-sonnet-latest",
                                "api_key_env": "ANTHROPIC_API_KEY",
                            }
                        ]
                    }
                )
                await core.stop()
        self.assertEqual(snapshot["providers"][0]["provider_name"], "claude.coder")
        self.assertEqual(snapshot["providers"][0]["model"], "claude-3-7-sonnet-latest")

    async def test_update_active_provider_settings_switches_to_single_local_provider(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
            settings.plugins.enabled = ["openai.compat", "llama.cpp"]
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
                },
                "llama.cpp": {
                    "provider_name": "localhost.chat",
                    "base_url": "http://127.0.0.1:8080",
                    "model": "Qwen3-4B-Q5_K_M.gguf",
                },
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
            await core.start()
            snapshot = await core.update_active_provider_settings(
                {
                    "provider": {
                        "kind": "llama.cpp",
                        "provider_name": "localhost.chat",
                        "host": "127.0.0.1",
                        "port": 9000,
                        "model": "qwen3-coder.gguf",
                        "temperature": 0.3,
                        "max_tokens": 4096,
                    }
                }
            )
            await core.stop()
        self.assertEqual(snapshot["active_provider"]["kind"], "llama.cpp")
        self.assertEqual(snapshot["active_provider"]["port"], 9000)
        self.assertEqual(snapshot["conversation"]["default_provider"], "localhost.chat")
        self.assertEqual(snapshot["conversation"]["routes"]["chat"]["provider"], "localhost.chat")

    async def test_active_provider_model_catalog_returns_discovered_models(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            with patch("yue_core.app.OpenAICompatibleProvider.health", return_value={
                "ok": True,
                "reachable": True,
                "models": ["qwen2.5:7b", "llama3.1:8b"],
            }):
                catalog = await core.active_provider_model_catalog(
                    {
                        "provider": {
                            "kind": "ollama",
                            "provider_name": "ollama.chat",
                            "host": "127.0.0.1",
                            "port": 11434,
                        }
                    }
                )
            await core.stop()
        self.assertTrue(catalog["ok"])
        self.assertEqual(catalog["selected_model"], "qwen2.5:7b")
        self.assertEqual(catalog["models"][1], "llama3.1:8b")

    async def test_stop_kills_active_shell_sessions(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            fake_process = FakeProcess(stdout=b"ready\n")
            with patch("yue_core.shell_sessions.asyncio.create_subprocess_exec", return_value=fake_process):
                await core.start()
                await core.shell_sessions.start("dev-server", "echo ready", temp)
                await asyncio.sleep(0)
                await core.stop()
        self.assertTrue(fake_process.killed)


if __name__ == "__main__":
    unittest.main()
