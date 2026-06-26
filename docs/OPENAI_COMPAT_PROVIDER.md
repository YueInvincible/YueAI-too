# OpenAI-compatible provider

The `openai.compat` plugin registers one or more model providers that expose an
OpenAI-compatible streaming chat endpoint.

Current implementation target:

```text
POST /v1/chat/completions
```

with SSE token streaming and OpenAI-style tool calls.

## Why this exists

- One adapter for cloud and local backends.
- One config surface for normal chat and coding-agent routing.
- Works with providers that already expose an OpenAI-compatible API.
- This is also the main runtime editor surface in the desktop shell for:
  - OpenAI
  - Google AI
  - OpenRouter
  - Ollama
  - LM Studio
  - llama.cpp-compatible endpoints

## Supported backends in config

- `openai`
- `google`
- `openrouter`
- `ollama`
- `lmstudio`
- `llama.cpp`
- `custom`

`backend` only affects defaults such as `base_url` and API-key handling. The
wire format is still the same OpenAI-compatible chat endpoint.

The desktop runtime editor currently supports:

- add/remove provider rows
- quick presets
- custom headers
- apply runtime
- save back to TOML

## Configuration

```toml
[plugins]
roots = ["plugins"]
enabled = ["openai.compat"]

[plugins.options."openai.compat"]
providers = [
  { provider_name = "openai.coder", backend = "openai", model = "gpt-4.1-mini", api_key_env = "OPENAI_API_KEY" },
  { provider_name = "google.chat", backend = "google", model = "gemini-3.5-flash", api_key_env = "GEMINI_API_KEY" },
  { provider_name = "openrouter.claude", backend = "openrouter", model = "anthropic/claude-3.5-sonnet", api_key_env = "OPENROUTER_API_KEY" },
  { provider_name = "ollama.chat", backend = "ollama", base_url = "http://127.0.0.1:11434/v1", model = "qwen2.5:7b-instruct" },
  { provider_name = "lmstudio.chat", backend = "lmstudio", base_url = "http://127.0.0.1:1234/v1", model = "openai/gpt-oss-20b" },
  { provider_name = "llama.coder", backend = "llama.cpp", base_url = "http://127.0.0.1:8080", model = "Qwen2.5-Coder-7B-Instruct-GGUF" },
]

[conversation]
default_provider = "ollama.chat"

[conversation.routes.chat]
provider = "ollama.chat"
prompt_profile = "default"

[conversation.routes.coding_agent]
provider = "openai.coder"
prompt_profile = "coding_agent"
```

## Prompt profiles

Conversation routing is paired with prompt profiles:

```toml
[conversation.prompt_profiles.default]
personality = "Local-first assistant."
system_instruction = "Prefer the configured local provider for normal chat."
tool_instruction = "Use tools only when useful."
response_instruction = "Keep answers concise."

[conversation.prompt_profiles.coding_agent]
personality = "Senior coding agent."
system_instruction = "Implement code changes safely and verify them."
tool_instruction = "Inspect the repo and run tests before finishing."
response_instruction = "State assumptions and remaining risks."
```

These instructions are injected as a transient `system` message at request
time. They are not persisted into conversation history.

## Defaults

- `openai` defaults to `https://api.openai.com/v1` and reads `OPENAI_API_KEY`
  when `api_key` / `api_key_env` is not set.
- `google` defaults to `https://generativelanguage.googleapis.com/v1beta/openai`
  and reads `GEMINI_API_KEY` first, then `GOOGLE_API_KEY`.
- `openrouter` defaults to `https://openrouter.ai/api/v1` and reads
  `OPENROUTER_API_KEY`.
- `ollama` defaults to `http://127.0.0.1:11434/v1` and uses `ollama` as the
  placeholder API key if none is supplied.
- `lmstudio` defaults to `http://127.0.0.1:1234/v1`.
- `llama.cpp` defaults to `http://127.0.0.1:8080`.

Current local-first direction:

- `LM Studio` is the preferred local path for normal agent use.
- `llama.cpp` remains supported but its dedicated editor path is deferred.

## Limitations

- The adapter currently standardizes on `/v1/chat/completions`, not the newer
  Responses API.
- It does not start or supervise model servers.
- It assumes the target model/runtime supports tool calling in OpenAI format.
