import unittest

from tests.support import workspace_temp_dir
from yue_core.config import Settings, load_settings, save_settings
from yue_core.errors import ConfigurationError


class ConfigTests(unittest.TestCase):
    def test_default_coding_prompt_profile_includes_tool_guidance(self):
        settings = Settings()
        self.assertIn(
            "Inspect relevant files before editing",
            settings.conversation.prompt_profiles["coding_agent"]["tool_instruction"],
        )
        self.assertIn(
            "call multiple read tools in the same turn",
            settings.conversation.prompt_profiles["coding_agent"]["tool_instruction"],
        )

    def test_conversation_settings_load(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                """
[conversation]
default_provider = "demo.provider"
max_tool_iterations = 2
max_tool_output_chars = 2048
max_history_messages = 20
max_history_chars = 8192
max_message_chars = 2048
max_system_instruction_chars = 4096

[conversation.routes.chat]
provider = "demo.chat"
prompt_profile = "assistant"

[conversation.routes.coding_agent]
provider = "demo.coder"
prompt_profile = "coding"

[conversation.prompt_profiles.assistant]
personality = "Concise"
system_instruction = "Help the user."

[conversation.prompt_profiles.coding]
system_instruction = "Write code."
tool_instruction = "Use tools when needed."
""".strip(),
                encoding="utf-8",
            )
            settings = load_settings(path, base_dir=temp)
        self.assertEqual(settings.conversation.default_provider, "demo.provider")
        self.assertEqual(settings.conversation.routes["chat"]["provider"], "demo.chat")
        self.assertEqual(
            settings.conversation.routes["coding_agent"]["provider"],
            "demo.coder",
        )
        self.assertEqual(
            settings.conversation.prompt_profiles["assistant"]["personality"],
            "Concise",
        )
        self.assertEqual(settings.conversation.store_backend, "sqlite")
        self.assertEqual(settings.conversation.max_tool_iterations, 2)
        self.assertEqual(settings.conversation.max_tool_output_chars, 2048)
        self.assertEqual(settings.conversation.max_history_messages, 20)
        self.assertEqual(settings.conversation.max_history_chars, 8192)
        self.assertEqual(settings.conversation.max_message_chars, 2048)
        self.assertEqual(settings.conversation.max_system_instruction_chars, 4096)
        self.assertEqual(settings.conversation.max_model_tools, 64)
        self.assertEqual(settings.conversation.max_tool_spec_chars, 8000)
        self.assertEqual(settings.conversation.max_tool_catalog_chars, 48000)

    def test_rejects_too_small_tool_output_limit(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                "[conversation]\nmax_tool_output_chars = 10\n",
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                load_settings(path, base_dir=temp)

    def test_rejects_message_limit_larger_than_history_budget(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                "[conversation]\nmax_history_chars = 1024\nmax_message_chars = 2048\n",
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                load_settings(path, base_dir=temp)

    def test_rejects_missing_prompt_profile_reference(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                """
[conversation.routes.chat]
provider = "demo.chat"
prompt_profile = "missing"
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                load_settings(path, base_dir=temp)

    def test_save_settings_round_trip_preserves_conversation_updates(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.local.toml"
            settings = Settings()
            settings.config_path = path
            settings.conversation.default_provider = "fake.echo"
            settings.conversation.routes["chat"]["provider"] = "fake.echo"
            settings.conversation.routes["coding_agent"]["provider"] = "fake.echo"
            settings.conversation.prompt_profiles["default"]["personality"] = "Concise"
            settings.conversation.prompt_profiles["coding_agent"][
                "system_instruction"
            ] = "Write code"
            save_settings(settings, base_dir=temp)
            loaded = load_settings(path, base_dir=temp)

        self.assertEqual(loaded.conversation.default_provider, "fake.echo")
        self.assertEqual(
            loaded.conversation.prompt_profiles["default"]["personality"],
            "Concise",
        )
        self.assertEqual(
            loaded.conversation.prompt_profiles["coding_agent"][
                "system_instruction"
            ],
            "Write code",
        )


if __name__ == "__main__":
    unittest.main()
