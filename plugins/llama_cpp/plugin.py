from __future__ import annotations

from yue_core.openai_compat import OpenAICompatibleProvider


class LlamaCppPlugin:
    async def setup(self, context) -> None:
        config = {"backend": "llama.cpp", **context.config}
        context.register_model_provider(OpenAICompatibleProvider(config))

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None
