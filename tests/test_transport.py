import json
import io
import unittest
from pathlib import Path

from yue_core.app import YueCore
from yue_core.config import Settings
from yue_core.transport import JsonLineServer
from tests.support import workspace_temp_dir


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
