from __future__ import annotations

from yue_core.openai_compat import OpenAICompatibleProvider, coerce_provider_configs


class OpenAICompatiblePlugin:
    async def setup(self, context) -> None:
        for provider_config in coerce_provider_configs(context.config):
            context.register_model_provider(OpenAICompatibleProvider(provider_config))

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None
