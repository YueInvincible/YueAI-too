# llama.cpp provider

The `llama.cpp` plugin is now a thin wrapper around the shared
OpenAI-compatible adapter. It exists for a simple single-provider llama.cpp
setup, while multi-provider routing now lives in `openai.compat`.

Current project direction:

- keep `llama.cpp` support;
- prioritize `LM Studio` for the main local workflow;
- defer a dedicated `llama.cpp` runtime editor until after core/tooling work.

It still does not download, launch, or manage a model. Model lifecycle will
later belong to the resource manager.

## Configuration

```toml
[plugins]
roots = ["plugins"]
enabled = ["llama.cpp"]

[plugins.options."llama.cpp"]
base_url = "http://127.0.0.1:8080"
model = "local-model"
provider_name = "llama.local"
timeout_seconds = 120.0
temperature = 0.7
max_tokens = 1024

[conversation]
default_provider = "llama.local"
```

The server must expose:

```text
POST /v1/chat/completions
```

with OpenAI-compatible SSE streaming.

If you want one config file to register OpenAI cloud, Ollama, LM Studio, and
llama.cpp at once, prefer [OPENAI_COMPAT_PROVIDER.md](OPENAI_COMPAT_PROVIDER.md).

## Tool names

Core tool names use dots, such as `core.echo`. OpenAI function names are
encoded before sending:

```text
core.echo -> core__echo
```

The provider maps returned names back to their canonical core names before the
permission and execution pipeline sees them.

## Guarantees and limitations

- Text deltas stream directly into conversation events.
- Streaming tool-call fragments are accumulated and parsed strictly as JSON.
- Invalid tool arguments fail the run instead of being guessed.
- Cancellation closes the active HTTP response.
- The current adapter uses the standard library and one background thread per
  active generation.
- It assumes the selected llama.cpp model/template supports tool calling.
- Model download, benchmark, process startup, GPU layer selection, and context
  sizing are not implemented yet.
