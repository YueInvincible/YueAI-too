# Yue Core architecture

## Boundary

Yue Core owns orchestration and policy. Current scope is intentionally small.
It does not own:

- the Tauri/VRM user interface;
- Voice runtime concerns such as TTS, STT, voice cloning, or streaming audio;
- platform-specific screen and process monitoring;
- continuous vision or avatar rendering loops.

Those systems integrate through providers, plugins, tools, events, and local
transports.

## Public compatibility surface

Plugin authors may import only from `yue_core.contracts`.

The public surface currently contains:

- `CoreEvent`;
- `ToolSpec`, `ToolRequest`, `ToolResult`, and `ToolContext`;
- `Capability`, `RiskLevel`, and status enums;
- `Tool`, `Plugin`, and `PluginContext` protocols;
- optional `Service` lifecycle protocol;
- `CORE_API_VERSION`.

Everything else is internal and may change within a minor core release.

Core API uses semantic compatibility:

- major version: breaking plugin contract;
- minor version: additive contract changes;
- patch version: implementation fixes.

Current core package version: `0.2.0`. Current plugin API: `1.1`.

## Tool execution

```text
request
  -> registry lookup
  -> argument schema validation
  -> permission evaluation / approval
  -> tool.started event
  -> timeout + cancellation boundary
  -> audit result
  -> tool.finished event
```

Tool names must be globally namespaced. Plugin tools should begin with their
plugin ID.

The supported JSON Schema subset is intentionally small:

- `type`;
- `properties`;
- `required`;
- `additionalProperties`;
- `items`;
- `enum`;
- `minLength` and `maxLength`.

Do not put business validation entirely in schemas. Validate paths, ownership,
resource limits, and system state inside the tool as well.

## Permissions

Tools declare one capability and one risk level. The permission engine applies:

1. explicit rules;
2. active permission profile;
3. risk threshold;
4. interactive approval where configured;
5. deny by default when approval is unavailable.

Plugins cannot grant themselves permissions.

## Events

Topics are dot-separated:

- `core.started`;
- `tool.started`;
- `tool.finished`;
- `plugin.ready`;
- `conversation.delta`.

Subscribers may use exact topics, `namespace.*`, or `*`.

Events are notifications, not durable commands. State-changing requests should
use tools or a future command bus with explicit acknowledgement.

## Plugins

Each plugin is a directory containing:

```text
plugin.json
plugin.py
```

Plugins are loaded only when their ID appears in `plugins.enabled`. Entrypoints
must stay inside their plugin directory. A plugin receives a restricted
`PluginContext` and cannot access the registry internals.

Plugins may register namespaced services such as `llm.default` or
`memory.primary`. Tools receive the read-only service mapping through
`ToolContext`. Services are removed automatically when their owning plugin
stops.

Future work:

- signed/trusted plugin metadata;
- dependency declaration;
- plugin isolation in subprocesses;
- hot reload for development;
- capability declarations in manifests.

Untrusted plugins must eventually run out of process. The current in-process
loader is for trusted first-party plugins.

## Transports

The first transport is newline-delimited JSON over stdio:

```json
{"id":"1","method":"tools.list"}
{"id":"2","method":"tools.invoke","params":{"name":"core.echo","arguments":{"text":"hello"}}}
```

Transport adapters must not contain orchestration logic. Named pipes or local
WebSockets can replace stdio later without changing tools or plugins.

## ML sidecars

Use separate processes/environments for:

- llama.cpp;
- Ollama;
- LM Studio local server;
- any custom OpenAI-compatible local runtime;
- embeddings.

Voice, avatar rendering, and process monitoring remain deferred until the core
slice is stable.

This is mandatory because the installed system Python is 3.14 while many ML
libraries require Python 3.10 or 3.11. The core itself remains dependency-light
and stable.

Model providers register through the provider registry. Conversation history
is accessed only through `ConversationStore`; SQLite is the default durable
implementation and the in-memory implementation remains available for tests.
The current provider strategy is a shared OpenAI-compatible adapter for cloud
and local runtimes, with conversation routes separating normal chat and coding
agent workloads.
