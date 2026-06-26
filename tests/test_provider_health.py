import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from yue_core.openai_compat import OpenAICompatibleProvider
from yue_core.providers import ModelProviderRegistry


class ProviderHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {
            "data": [
                {"id": "qwen2.5:7b-instruct"},
                {"id": "gpt-4.1-mini"},
            ]
        }
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        self.wfile.flush()

    def log_message(self, format, *args):
        return None


class ProviderHealthTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_compatible_provider_health(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), ProviderHealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider = OpenAICompatibleProvider(
                {
                    "provider_name": "ollama.chat",
                    "backend": "ollama",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model": "qwen2.5:7b-instruct",
                }
            )
            health = await provider.health()
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(timeout=2)

        self.assertTrue(health["ok"])
        self.assertTrue(health["reachable"])
        self.assertTrue(health["model_available"])

    async def test_registry_collects_provider_health(self):
        registry = ModelProviderRegistry()
        registry.register(
            OpenAICompatibleProvider(
                {
                    "provider_name": "custom.test",
                    "backend": "custom",
                    "base_url": "http://127.0.0.1:9/v1",
                    "model": "missing-model",
                    "health_timeout_seconds": 0.2,
                }
            ),
            owner="test",
        )
        health = await registry.health()
        self.assertEqual(health[0]["provider"], "custom.test")
        self.assertFalse(health[0]["ok"])


if __name__ == "__main__":
    unittest.main()
