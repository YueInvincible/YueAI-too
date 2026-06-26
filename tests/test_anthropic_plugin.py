import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings


class AnthropicMockHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps({"data": [{"id": "claude-sonnet-4-20250514"}]}).encode("utf-8")
        )
        self.wfile.flush()

    def do_POST(self):
        if self.path != "/v1/messages":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(payload)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        saw_tool_result = any(
            isinstance(message.get("content"), list)
            and any(block.get("type") == "tool_result" for block in message["content"])
            for message in payload.get("messages", [])
        )
        chunks = (
            [
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": 0,
                        "content_block": {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "core.echo",
                            "input": {},
                        },
                    },
                ),
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": '{"text":"from claude"}',
                        },
                    },
                ),
                ("message_stop", {"type": "message_stop"}),
            ]
            if not saw_tool_result
            else [
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": 0,
                        "content_block": {"type": "text", "text": "Claude used tool: "},
                    },
                ),
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": "done"},
                    },
                ),
                ("message_stop", {"type": "message_stop"}),
            ]
        )
        for event_name, event_payload in chunks:
            self.wfile.write(f"event: {event_name}\n".encode("utf-8"))
            self.wfile.write(f"data: {json.dumps(event_payload)}\n\n".encode("utf-8"))
            self.wfile.flush()

    def log_message(self, format, *args):
        return None


class AnthropicPluginTests(unittest.IsolatedAsyncioTestCase):
    async def test_streaming_tool_loop_against_anthropic_messages_server(self):
        AnthropicMockHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), AnthropicMockHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with workspace_temp_dir() as temp:
                settings = Settings()
                settings.core.data_dir = temp
                settings.conversation.store_backend = "memory"
                settings.conversation.default_provider = "claude.coder"
                settings.conversation.routes["chat"] = {
                    "provider": "claude.coder",
                    "prompt_profile": "default",
                }
                settings.conversation.routes["coding_agent"] = {
                    "provider": "claude.coder",
                    "prompt_profile": "coding_agent",
                }
                settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
                settings.plugins.enabled = ["anthropic.messages"]
                settings.plugins.options = {
                    "anthropic.messages": {
                        "providers": [
                            {
                                "provider_name": "claude.coder",
                                "backend": "anthropic",
                                "base_url": f"http://127.0.0.1:{server.server_port}",
                                "model": "claude-sonnet-4-20250514",
                                "api_key": "test-key",
                            }
                        ]
                    }
                }
                core = YueCore(settings)
                async with core:
                    health = await core.providers.health()
                    conversation = await core.conversations.create()
                    assistant = await core.conversations.send(
                        conversation.id,
                        "use tool",
                        provider_role="coding_agent",
                    )
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(timeout=2)

        self.assertTrue(health[0]["ok"])
        self.assertEqual(assistant.content, "Claude used tool: done")
        self.assertEqual(len(AnthropicMockHandler.requests), 2)
        self.assertEqual(
            AnthropicMockHandler.requests[1]["messages"][-1]["content"][0]["type"],
            "tool_result",
        )
