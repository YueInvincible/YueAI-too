# Provider And Prompt Config

## Muc dich

Ghi lai huong core moi cho routing provider va prompt/instruction config.

## Trang thai da xac nhan

- Core da ho tro route theo role:
  - `chat`
  - `coding_agent`
- Core da ho tro prompt profile theo role:
  - `personality`
  - `system_instruction`
  - `tool_instruction`
  - `response_instruction`
- Prompt profile duoc inject thanh `system` message tam thoi luc tao `ModelRequest`.
- Da co plugin `openai.compat` de dang ky nhieu provider trong mot config.
- Plugin `llama.cpp` van giu lai, nhung hien tai chi la wrapper mong quanh adapter OpenAI-compatible chung.
- Da verify bang Python test suite:
  - `PYTHONPATH=src; python -m pytest`

## Huong config hien tai

- Chon provider mac dinh bang:
  - `[conversation].default_provider`
- Chon provider theo role bang:
  - `[conversation.routes.chat]`
  - `[conversation.routes.coding_agent]`
- Chon prompt profile theo role bang:
  - `prompt_profile = "default"` hoac ten profile khac
- Khai bao profile bang:
  - `[conversation.prompt_profiles.<name>]`

## Provider da co duong di ro rang

- OpenAI cloud qua `openai.compat`
- Ollama local qua `openai.compat`
- LM Studio local qua `openai.compat`
- llama.cpp local qua `openai.compat` hoac plugin `llama.cpp`
- Custom OpenAI-compatible endpoint qua `openai.compat`

## Tai lieu lien quan

- OpenAI Chat API reference:
  - https://developers.openai.com/api/reference/resources/chat
- OpenAI Responses API reference:
  - https://developers.openai.com/api/reference/resources/responses/methods/create
- Ollama OpenAI compatibility:
  - https://docs.ollama.com/api/openai-compatibility
- LM Studio OpenAI compatibility:
  - https://lmstudio.ai/docs/developer/openai-compat
- LM Studio local server docs:
  - https://lmstudio.ai/docs/developer/core/server
- llama.cpp server README:
  - https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

## Ghi chu ky thuat tu tai lieu

- OpenAI hien co ca Chat API va Responses API; core hien tai dang standardize tren `/v1/chat/completions` de dung chung cho cloud + local OpenAI-compatible backends.
- Ollama doc xac nhan OpenAI compatibility voi `base_url='http://localhost:11434/v1/'` va API key `ollama` co the la placeholder.
- LM Studio doc xac nhan OpenAI-compatible endpoint mac dinh o `http://localhost:1234/v1` va co `POST /v1/responses`; server co the start tu app hoac `lms server start`.
- llama.cpp server doc xac nhan OpenAI-compatible `/v1/models`; `--alias` co the dung de dat model id de config on dinh hon.

## Viec tiep theo hop ly

1. Them provider bootstrap/health checks de UI biet endpoint nao dang song.
2. Them UI/settings editor cho routes + prompt profiles.
3. Can nhac them adapter Responses API rieng neu muon dung sat hon OpenAI cloud feature set.
