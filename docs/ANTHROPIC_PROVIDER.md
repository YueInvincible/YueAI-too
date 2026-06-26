# Anthropic Messages provider

The `anthropic.messages` plugin registers one or more Claude providers using
Anthropic's Messages API.

Current implementation target:

```text
POST /v1/messages
GET /v1/models
```

with SSE streaming and Anthropic tool-use blocks mapped into Yue Core tool calls.

## Configuration

```toml
[plugins]
roots = ["plugins"]
enabled = ["anthropic.messages"]

[plugins.options."anthropic.messages"]
providers = [
  { provider_name = "claude.coder", backend = "anthropic", model = "claude-sonnet-4-20250514", api_key_env = "ANTHROPIC_API_KEY" },
]
```

## Notes

- Anthropic uses a top-level `system` field instead of OpenAI-style system
  messages. Yue Core converts transient prompt profiles into that field.
- Tool results are translated into Anthropic `tool_result` user content blocks.
- The provider requires an API key. By default it reads `ANTHROPIC_API_KEY`.
- The desktop runtime editor currently supports:
  - add/remove provider rows
  - quick Claude preset
  - custom headers
  - apply runtime
  - save back to TOML
