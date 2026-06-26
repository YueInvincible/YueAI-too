import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings


class OpenAICompatMockHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(payload)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        chunks = [
            {
                "choices": [
                    {
                        "delta": {"content": "ok"},
                        "finish_reason": None,
                    }
                ]
            },
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, format, *args):
        return None


class OpenAICompatiblePluginTests(unittest.IsolatedAsyncioTestCase):
    async def test_registers_multiple_providers_from_one_plugin(self):
        OpenAICompatMockHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), OpenAICompatMockHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with workspace_temp_dir() as temp:
                settings = Settings()
                settings.core.data_dir = temp
                settings.conversation.store_backend = "memory"
                settings.conversation.default_provider = "local.chat"
                settings.conversation.routes["chat"] = {
                    "provider": "local.chat",
                    "prompt_profile": "default",
                }
                settings.conversation.routes["coding_agent"] = {
                    "provider": "cloud.coder",
                    "prompt_profile": "coding_agent",
                }
                settings.plugins.roots = [(Path.cwd() / "plugins").resolve()]
                settings.plugins.enabled = ["openai.compat"]
                settings.plugins.options = {
                    "openai.compat": {
                        "providers": [
                            {
                                "provider_name": "local.chat",
                                "backend": "ollama",
                                "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                                "model": "qwen2.5",
                            },
                            {
                                "provider_name": "cloud.coder",
                                "backend": "openai",
                                "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                                "model": "gpt-4.1-mini",
                                "api_key": "test-key",
                            },
                        ]
                    }
                }
                core = YueCore(settings)
                async with core:
                    conversation = await core.conversations.create()
                    assistant = await core.conversations.send(
                        conversation.id,
                        "Hello",
                        provider_role="coding_agent",
                    )
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(assistant.content, "ok")
        self.assertEqual(assistant.metadata["provider"], "cloud.coder")
        self.assertEqual(len(OpenAICompatMockHandler.requests), 1)
        self.assertEqual(
            OpenAICompatMockHandler.requests[0]["model"],
            "gpt-4.1-mini",
        )


if __name__ == "__main__":
    unittest.main()
