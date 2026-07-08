import io
import json
import sys
import unittest
from argparse import Namespace
from unittest.mock import patch

from tests.support import workspace_temp_dir
from yue_core.agent_exports import render_agent_starter_pack_output
from yue_core.tool_guidance import render_tool_guide_output
from yue_core.cli import _write_stdout_text, run


class CliTests(unittest.TestCase):
    def test_write_stdout_text_falls_back_to_utf8_bytes(self):
        buffer = io.BytesIO()
        stdout = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
        with patch.object(sys, "stdout", stdout):
            _write_stdout_text("Dạ, em đây")
            stdout.flush()
        self.assertEqual(buffer.getvalue(), "Dạ, em đây\n".encode("utf-8"))

    def test_export_agent_starter_pack_writes_text_file(self):
        with workspace_temp_dir() as temp:
            output_path = temp / "starter-pack.md"
            exit_code = self._run_async(
                run(
                    Namespace(
                        config=None,
                        command="export-agent-starter-pack",
                        provider_role="coding_agent",
                        format="text",
                        output=output_path,
                    )
                )
            )
            self.assertEqual(exit_code, 0)
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("# YueAI coding_agent starter pack", content)
            self.assertIn("## Codex-style tool manifest", content)
            self.assertIn("## Common tool recipes", content)

    def test_export_tool_guide_writes_text_file(self):
        with workspace_temp_dir() as temp:
            output_path = temp / "tool-guide.md"
            exit_code = self._run_async(
                run(
                    Namespace(
                        config=None,
                        command="export-tool-guide",
                        provider_role="coding_agent",
                        format="text",
                        output=output_path,
                    )
                )
            )
            self.assertEqual(exit_code, 0)
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("Coding agent tool guide:", content)
            self.assertIn("Execution rules:", content)
            self.assertIn("Common recipes:", content)

    def test_export_agent_starter_pack_writes_json_stdout(self):
        buffer = io.StringIO()
        with patch.object(sys, "stdout", buffer):
            exit_code = self._run_async(
                run(
                    Namespace(
                        config=None,
                        command="export-agent-starter-pack",
                        provider_role="coding_agent",
                        format="json",
                        output=None,
                    )
                )
            )
        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["provider_role"], "coding_agent")
        self.assertIn("starter_prompt", payload)
        self.assertIn("codex_manifest", payload)

    def test_export_tool_guide_writes_json_stdout(self):
        buffer = io.StringIO()
        with patch.object(sys, "stdout", buffer):
            exit_code = self._run_async(
                run(
                    Namespace(
                        config=None,
                        command="export-tool-guide",
                        provider_role="coding_agent",
                        format="json",
                        output=None,
                    )
                )
            )
        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["provider_role"], "coding_agent")
        self.assertIn("execution_rules", payload)
        self.assertGreater(len(payload["recipes"]), 0)

    def test_render_agent_starter_pack_output_supports_focused_formats(self):
        payload = {
            "starter_prompt": "starter",
            "system_prompt": "system",
            "tool_manifest_json": "{\n  \"provider_role\": \"coding_agent\"\n}",
            "integration_checklist": ["first", "second"],
            "text": "full text",
        }
        self.assertEqual(render_agent_starter_pack_output(payload, "text"), "full text")
        self.assertEqual(render_agent_starter_pack_output(payload, "starter-prompt"), "starter")
        self.assertEqual(render_agent_starter_pack_output(payload, "system-prompt"), "system")
        self.assertIn("\"provider_role\"", render_agent_starter_pack_output(payload, "manifest-json"))
        self.assertEqual(
            render_agent_starter_pack_output(payload, "checklist"),
            "- first\n- second",
        )

    def test_render_tool_guide_output_supports_json_and_text(self):
        payload = {
            "text": "guide text",
            "recipes": [{"name": "inspect-and-patch"}],
        }
        self.assertEqual(render_tool_guide_output(payload, "text"), "guide text")
        self.assertIn("\"recipes\"", render_tool_guide_output(payload, "json"))

    @staticmethod
    def _run_async(coro):
        import asyncio

        return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
