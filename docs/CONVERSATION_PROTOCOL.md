# Conversation and model-provider protocol

## Provider contract

Model providers implement `ModelProvider` from `yue_core.contracts`.

```python
class Provider:
    name = "vendor.model"

    async def generate(self, request, context):
        yield ModelEvent(ModelEventType.TEXT_DELTA, text="Hello")
        yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")
```

A provider may emit:

- `TEXT_DELTA`: assistant text fragment;
- `TOOL_CALL`: a complete structured call with unique ID;
- `FINISH`: optional provider finish metadata.

Providers must:

- preserve message order;
- use unique tool-call IDs within a generation;
- check `context.cancelled()` during long operations;
- never execute tools directly;
- never bypass `ToolExecutor`;
- avoid including hidden reasoning in user-visible deltas.

Providers register through `PluginContext.register_model_provider()`. The core
ships `fake.echo` only for deterministic testing.

## Orchestration loop

```text
append user message
  -> provider stream
  -> publish text deltas
  -> append assistant message
  -> if tool calls:
       execute through permissions/tools
       append bounded tool result messages
       call provider again
  -> otherwise complete
```

Runs are serialized per conversation. Different conversations may run in
parallel. Each run has a caller-supplied or generated `run_id` and can be
cancelled immediately.

Tool output sent back to a model is bounded by
`conversation.max_tool_output_chars`. The iteration count is bounded by
`conversation.max_tool_iterations`.

## JSONL methods

Requests:

```json
{"id":"1","method":"providers.list"}
{"id":"2","method":"conversations.create","params":{"title":"Chat"}}
{"id":"3","method":"conversations.send","params":{"conversation_id":"...","content":"Hello","run_id":"run-1"}}
{"id":"4","method":"conversations.cancel","params":{"run_id":"run-1"}}
{"id":"5","method":"conversations.messages","params":{"conversation_id":"..."}}
{"id":"6","method":"conversations.list","params":{"limit":50}}
```

While `serve` is running, conversation events are emitted independently:

```json
{"event":{"topic":"conversation.delta","payload":{"run_id":"run-1","text":"Hel"}}}
```

The transport processes requests concurrently, allowing a cancel request to
interrupt an active send request.

## Current persistence

The current store is in memory. The contract intentionally hides storage
details so SQLite can replace it without changing providers, UI, or
orchestration.

