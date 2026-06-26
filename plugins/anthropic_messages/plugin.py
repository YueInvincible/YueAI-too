from __future__ import annotations

from yue_core.anthropic import AnthropicMessagesProvider, coerce_provider_configs


class AnthropicMessagesPlugin:
    async def setup(self, context) -> None:
        for provider_config in coerce_provider_configs(context.config):
            context.register_model_provider(AnthropicMessagesProvider(provider_config))

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None
