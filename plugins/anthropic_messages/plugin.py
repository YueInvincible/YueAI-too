from __future__ import annotations

from yue_core.contracts import CoreEvent
from yue_core.anthropic import AnthropicMessagesProvider, coerce_provider_configs


class AnthropicMessagesPlugin:
    async def setup(self, context) -> None:
        for provider_config in coerce_provider_configs(context.config):
            try:
                provider = AnthropicMessagesProvider(provider_config)
            except ValueError as exc:
                if "API key must not be empty" not in str(exc):
                    raise
                await context.publish(
                    CoreEvent(
                        "plugin.provider.skipped",
                        {
                            "plugin_id": context.plugin_id,
                            "provider_name": str(provider_config.get("provider_name", "")),
                            "reason": str(exc),
                        },
                        source=context.plugin_id,
                    )
                )
                continue
            context.register_model_provider(provider)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None
