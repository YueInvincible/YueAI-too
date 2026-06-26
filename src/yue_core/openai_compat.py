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
    if normalized == "openai":
        return "https://api.openai.com/v1"
    if normalized == "ollama":
        return "http://127.0.0.1:11434/v1"
    if normalized == "lmstudio":
        return "http://127.0.0.1:1234/v1"
    if normalized == "llama.cpp":
        return "http://127.0.0.1:8080"
    return "http://127.0.0.1:8080"


class OpenAICompatibleProvider:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.name = str(
            config.get("provider_name")
            or config.get("name")
            or config.get("provider")
            or ""
        ).strip()
        self.backend = str(config.get("backend", "custom")).strip().lower()
        self.base_url = str(
            config.get("base_url") or default_base_url(self.backend)
        ).rstrip("/")
        self.model = str(config.get("model", "")).strip()
        self.api_key = self._resolve_api_key(config)
        self.timeout_seconds = float(config.get("timeout_seconds", 120.0))
        self.temperature = float(config.get("temperature", 0.7))
        self.max_tokens = int(config.get("max_tokens", 1024))
        self.extra_headers = self._coerce_headers(config.get("headers", {}))
        if not self.name:
            raise ValueError("provider_name must not be empty")
        if not self.model:
            raise ValueError(f"{self.name} model must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError(f"{self.name} timeout_seconds must be positive")
        if self.max_tokens <= 0:
            raise ValueError(f"{self.name} max_tokens must be positive")

    async def generate(self, request: ModelRequest, context: ModelContext):
        payload = {
            "model": self.model,
            "messages": [self._message_payload(message) for message in request.messages],
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        tool_name_map: dict[str, str] = {}
        tools = []
        for spec in request.tools:
            safe_name = spec.name.replace(".", "__")
            if safe_name in tool_name_map and tool_name_map[safe_name] != spec.name:
                raise RuntimeError(f"Tool-name collision after encoding: {spec.name}")
            tool_name_map[safe_name] = spec.name
            tools.append(self._tool_payload(spec, safe_name))
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

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

                choice = (item.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    yield ModelEvent(ModelEventType.TEXT_DELTA, text=str(content))

                for fragment in delta.get("tool_calls") or []:
                    index = int(fragment.get("index", 0))
                    aggregate = tool_fragments.setdefault(
                        index,
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if fragment.get("id"):
                        aggregate["id"] = str(fragment["id"])
                    function = fragment.get("function") or {}
                    if function.get("name"):
                        aggregate["name"] += str(function["name"])
                    if function.get("arguments"):
                        aggregate["arguments"] += str(function["arguments"])

                finish_reason = choice.get("finish_reason")
                if finish_reason is not None:
                    break

            for index in sorted(tool_fragments):
                fragment = tool_fragments[index]
                if not fragment["name"]:
                    raise RuntimeError(
                        f"{self.name} emitted a tool call without a name"
                    )
                try:
                    arguments = json.loads(fragment["arguments"] or "{}")
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
                        name=tool_name_map.get(fragment["name"], fragment["name"]),
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

    def _stream_worker(
        self,
        payload: dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue,
        stop_event: threading.Event,
        response_holder: list[Any],
    ) -> None:
        request = urllib.request.Request(
            self._chat_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_holder.append(response)
                for raw_line in response:
                    if stop_event.is_set():
                        break
                    line = raw_line.decode("utf-8").strip()
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    self._queue(loop, queue, ("data", json.loads(data)))
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

    def _chat_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            **self.extra_headers,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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
        if self.backend == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        if self.backend == "ollama":
            return "ollama"
        return ""

    @staticmethod
    def _coerce_headers(value: Any) -> dict[str, str]:
        if not isinstance(value, Mapping):
            raise ValueError("headers must be a table")
        return {str(key): str(item) for key, item in value.items()}

    @staticmethod
    def _message_payload(message: ChatMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": message.role.value,
            "content": message.content,
        }
        if message.role is MessageRole.ASSISTANT and message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(
                            call.arguments,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    },
                }
                for call in message.tool_calls
            ]
        if message.role is MessageRole.TOOL:
            payload["tool_call_id"] = message.tool_call_id
            if message.tool_name:
                payload["name"] = message.tool_name
        return payload

    @staticmethod
    def _tool_payload(spec, safe_name: str) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": safe_name,
                "description": spec.description,
                "parameters": dict(spec.input_schema),
            },
        }


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
