import json
import asyncio
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings


class LlamaMockHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(payload)

        has_tool_result = any(
            message.get("role") == "tool" for message in payload["messages"]
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        if not has_tool_result:
            chunks = [
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call-1",
                                        "function": {
                                            "name": "core__echo",
                                            "arguments": '{"text":',
                                        },
                                    }
                                ]
                            },
                            "finish_reason": None,
                        }
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "function": {"arguments": '"hello"}'},
                                    }
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
            ]
        else:
            chunks = [
                {
                    "choices": [
                        {
                            "delta": {"content": "Tool completed."},
                            "finish_reason": None,
                        }
                    ]
                },
                {
                    "choices": [
                        {"delta": {}, "finish_reason": "stop"}
                    ]
                },
            ]

        for chunk in chunks:
            self.wfile.write(
                f"data: {json.dumps(chunk)}\n\n".encode("utf-8")
            )
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, format, *args):
        return None


class LlamaCppPluginTests(unittest.IsolatedAsyncioTestCase):
    async def test_streaming_tool_loop_against_openai_compatible_server(self):
        LlamaMockHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), LlamaMockHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with workspace_temp_dir() as temp:
                settings = Settings()
                settings.core.data_dir = temp
                settings.conversation.store_backend = "memory"
                settings.conversation.default_provider = "llama.local"
                settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
                settings.plugins.enabled = ["llama.cpp"]
                settings.plugins.options = {
                    "llama.cpp": {
                        "base_url": f"http://127.0.0.1:{server.server_port}",
                        "model": "mock-model",
                        "provider_name": "llama.local",
                    }
                }
                core = YueCore(settings)
                async with core:
                    conversation = await core.conversations.create()
                    assistant = await core.conversations.send(
                        conversation.id,
                        "Use echo",
                    )
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(assistant.content, "Tool completed.")
        self.assertEqual(len(LlamaMockHandler.requests), 2)
        tool_names = [
            item["function"]["name"]
            for item in LlamaMockHandler.requests[0]["tools"]
        ]
        self.assertIn("core__echo", tool_names)
        self.assertTrue(
            any(
                message["role"] == "tool"
                for message in LlamaMockHandler.requests[1]["messages"]
            )
        )


if __name__ == "__main__":
    unittest.main()
