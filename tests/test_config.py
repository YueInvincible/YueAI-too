import unittest

from tests.support import workspace_temp_dir
from yue_core.config import load_settings
from yue_core.errors import ConfigurationError


class ConfigTests(unittest.TestCase):
    def test_conversation_settings_load(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                """
[conversation]
default_provider = "demo.provider"
max_tool_iterations = 2
max_tool_output_chars = 2048

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

    def test_rejects_too_small_tool_output_limit(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                "[conversation]\nmax_tool_output_chars = 10\n",
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


if __name__ == "__main__":
    unittest.main()
