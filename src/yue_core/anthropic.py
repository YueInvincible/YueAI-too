from __future__ import annotations

import asyncio
import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (
    ChatMessage,
    MessageRole,
    ModelContext,
    ModelEvent,
    ModelEventType,
    ModelRequest,
    ModelToolCall,
)


def default_base_url(backend: str) -> str:
    normalized = backend.strip().lower()
    if normalized == "anthropic":
        return "https://api.anthropic.com"
    return "https://api.anthropic.com"


class AnthropicMessagesProvider:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.name = str(
            config.get("provider_name")
            or config.get("name")
            or config.get("provider")
            or ""
        ).strip()
        self.backend = str(config.get("backend", "anthropic")).strip().lower()
        self.base_url = str(
            config.get("base_url") or default_base_url(self.backend)
        ).rstrip("/")
        self.model = str(config.get("model", "")).strip()
        self.api_key = self._resolve_api_key(config)
        self.timeout_seconds = float(config.get("timeout_seconds", 120.0))
        self.health_timeout_seconds = float(
            config.get("health_timeout_seconds", min(self.timeout_seconds, 5.0))
        )
        self.temperature = float(config.get("temperature", 0.7))
        self.max_tokens = int(config.get("max_tokens", 1024))
        self.anthropic_version = str(
            config.get("anthropic_version", "2023-06-01")
        ).strip()
        self.extra_headers = self._coerce_headers(config.get("headers", {}))
        if not self.name:
            raise ValueError("provider_name must not be empty")
        if not self.model:
            raise ValueError(f"{self.name} model must not be empty")
        if not self.api_key:
            raise ValueError(f"{self.name} API key must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError(f"{self.name} timeout_seconds must be positive")
        if self.health_timeout_seconds <= 0:
            raise ValueError(f"{self.name} health_timeout_seconds must be positive")
        if self.max_tokens <= 0:
            raise ValueError(f"{self.name} max_tokens must be positive")

    async def generate(self, request: ModelRequest, context: ModelContext):
        system_parts = []
        messages = []
        for message in request.messages:
            if message.role is MessageRole.SYSTEM:
                if message.content:
                    system_parts.append(message.content)
                continue
            messages.append(self._message_payload(message))
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if request.tools:
            payload["tools"] = [self._tool_payload(spec) for spec in request.tools]

        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        stop_event = threading.Event()
        response_holder: list[Any] = []
        worker = threading.Thread(
            target=self._stream_worker,
            args=(payload, loop, queue, stop_event, response_holder),
            name=f"{self.name}-stream",
        )
        worker.start()

        tool_fragments: dict[int, dict[str, str]] = {}
        try:
            while True:
                if context.cancelled():
                    return
                kind, item = await queue.get()
                if kind == "error":
                    raise RuntimeError(str(item))
                if kind == "done":
                    break

                event_type = item.get("type")
                if event_type == "content_block_start":
                    block = item.get("content_block") or {}
                    if block.get("type") == "text" and block.get("text"):
                        yield ModelEvent(ModelEventType.TEXT_DELTA, text=str(block["text"]))
                    elif block.get("type") == "tool_use":
                        tool_fragments[int(item.get("index", 0))] = {
                            "id": str(block.get("id", "")),
                            "name": str(block.get("name", "")),
                            "arguments": (
                                json.dumps(block.get("input"), ensure_ascii=False)
                                if block.get("input")
                                else ""
                            ),
                        }
                elif event_type == "content_block_delta":
                    delta = item.get("delta") or {}
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield ModelEvent(ModelEventType.TEXT_DELTA, text=str(delta["text"]))
                    elif delta.get("type") == "input_json_delta":
                        aggregate = tool_fragments.setdefault(
                            int(item.get("index", 0)),
                            {"id": "", "name": "", "arguments": ""},
                        )
                        aggregate["arguments"] += str(delta.get("partial_json", ""))
                elif event_type == "message_stop":
                    break

            for index in sorted(tool_fragments):
                fragment = tool_fragments[index]
                if not fragment["name"]:
                    raise RuntimeError(
                        f"{self.name} emitted a tool call without a name"
                    )
                raw_arguments = fragment["arguments"] or "{}"
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"{self.name} emitted invalid tool arguments: {exc}"
                    ) from exc
                if not isinstance(arguments, dict):
                    raise RuntimeError("Tool-call arguments must decode to an object")
                yield ModelEvent(
                    ModelEventType.TOOL_CALL,
                    tool_call=ModelToolCall(
                        id=fragment["id"] or f"tool-{index}",
                        name=fragment["name"],
                        arguments=arguments,
                    ),
                )
            yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")
        finally:
            stop_event.set()
            if response_holder:
                try:
                    response_holder[0].close()
                except Exception:
                    pass
            await asyncio.to_thread(worker.join)

    async def health(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._health_sync)

    def _stream_worker(
        self,
        payload: dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue,
        stop_event: threading.Event,
        response_holder: list[Any],
    ) -> None:
        request = urllib.request.Request(
            self._messages_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(accept_sse=True),
            method="POST",
        )
        current_event = ""
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_holder.append(response)
                for raw_line in response:
                    if stop_event.is_set():
                        break
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if not data:
                            continue
                        payload_item = json.loads(data)
                        if payload_item.get("type") == "ping" or current_event == "ping":
                            continue
                        self._queue(loop, queue, ("data", payload_item))
            self._queue(loop, queue, ("done", None))
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:2000]
            except Exception:
                detail = ""
            self._queue(
                loop,
                queue,
                ("error", f"{self.name} HTTP {exc.code}: {detail or exc.reason}"),
            )
        except Exception as exc:
            if not stop_event.is_set():
                self._queue(loop, queue, ("error", f"{self.name} request failed: {exc}"))

    def _messages_url(self) -> str:
        if self.base_url.endswith("/v1/messages"):
            return self.base_url
        return f"{self.base_url}/v1/messages"

    def _models_url(self) -> str:
        if self.base_url.endswith("/v1/models"):
            return self.base_url
        return f"{self.base_url}/v1/models"

    def _headers(self, *, accept_sse: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            **self.extra_headers,
        }
        headers["Accept"] = "text/event-stream" if accept_sse else "application/json"
        return headers

    def _health_sync(self) -> dict[str, Any]:
        request = urllib.request.Request(
            self._models_url(),
            headers=self._headers(accept_sse=False),
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.health_timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                detail = exc.reason
            return {
                "provider": self.name,
                "backend": self.backend,
                "base_url": self.base_url,
                "model": self.model,
                "ok": False,
                "reachable": False,
                "error": f"HTTP {exc.code}: {detail}",
            }
        except Exception as exc:
            return {
                "provider": self.name,
                "backend": self.backend,
                "base_url": self.base_url,
                "model": self.model,
                "ok": False,
                "reachable": False,
                "error": str(exc),
            }

        models = payload.get("data") if isinstance(payload, dict) else None
        model_ids = [
            str(item.get("id"))
            for item in models or []
            if isinstance(item, Mapping) and item.get("id")
        ]
        return {
            "provider": self.name,
            "backend": self.backend,
            "base_url": self.base_url,
            "model": self.model,
            "ok": True,
            "reachable": True,
            "model_available": self.model in model_ids if model_ids else None,
            "models": model_ids,
        }

    @staticmethod
    def _queue(loop, queue, item) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:
            pass

    def _resolve_api_key(self, config: Mapping[str, Any]) -> str:
        direct = str(config.get("api_key", "")).strip()
        if direct:
            return direct
        env_name = str(config.get("api_key_env", "")).strip()
        if env_name:
            return os.environ.get(env_name, "")
        return os.environ.get("ANTHROPIC_API_KEY", "")

    @staticmethod
    def _coerce_headers(value: Any) -> dict[str, str]:
        if not isinstance(value, Mapping):
            raise ValueError("headers must be a table")
        return {str(key): str(item) for key, item in value.items()}

    @staticmethod
    def _tool_payload(spec) -> dict[str, Any]:
        return {
            "name": spec.name,
            "description": spec.description,
            "input_schema": dict(spec.input_schema),
        }

    @staticmethod
    def _message_payload(message: ChatMessage) -> dict[str, Any]:
        if message.role is MessageRole.USER:
            return {"role": "user", "content": message.content}
        if message.role is MessageRole.ASSISTANT:
            content_blocks: list[dict[str, Any]] = []
            if message.content:
                content_blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": dict(call.arguments),
                    }
                )
            return {
                "role": "assistant",
                "content": content_blocks or [{"type": "text", "text": ""}],
            }
        if message.role is MessageRole.TOOL:
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": message.tool_call_id,
                        "content": message.content,
                    }
                ],
            }
        raise ValueError(f"Unsupported message role for Anthropic: {message.role}")


def coerce_provider_configs(config: Mapping[str, Any]) -> Sequence[dict[str, Any]]:
    providers = config.get("providers")
    if providers is None:
        return [dict(config)]
    if not isinstance(providers, list):
        raise ValueError("providers must be an array of tables")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(providers):
        if not isinstance(item, Mapping):
            raise ValueError(f"providers[{index}] must be a table")
        normalized.append(dict(item))
    if not normalized:
        raise ValueError("providers must not be empty")
    return normalized


def normalize_provider_config(config: Mapping[str, Any]) -> dict[str, Any]:
    provider = AnthropicMessagesProvider(config)
    normalized: dict[str, Any] = {
        "provider_name": provider.name,
        "backend": provider.backend,
        "base_url": provider.base_url,
        "model": provider.model,
        "timeout_seconds": provider.timeout_seconds,
        "health_timeout_seconds": provider.health_timeout_seconds,
        "temperature": provider.temperature,
        "max_tokens": provider.max_tokens,
        "anthropic_version": provider.anthropic_version,
    }
    api_key_env = str(config.get("api_key_env", "")).strip()
    if api_key_env:
        normalized["api_key_env"] = api_key_env
    extra_headers = config.get("headers", {})
    if extra_headers:
        normalized["headers"] = AnthropicMessagesProvider._coerce_headers(extra_headers)
    return normalized
