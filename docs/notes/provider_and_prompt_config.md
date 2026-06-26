# Provider And Prompt Config

## Muc dich

Ghi lai huong core moi cho routing provider va prompt/instruction config.

## Uu tien hien tai

- Uu tien cao nhat la hoan thanh core chat/runtime/tooling cho agent.
- Trong cac local provider, `LM Studio` la path uu tien cao nhat de support va verify.
- `llama.cpp` van duoc giu trong roadmap, nhung editor rieng cua no de sau va khong duoc chan cac viec core/tooling.

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
- Da co plugin `anthropic.messages` de dang ky Claude provider qua Anthropic Messages API.
- Plugin `llama.cpp` van giu lai, nhung hien tai chi la wrapper mong quanh adapter OpenAI-compatible chung.
- Da co provider health-check aggregation qua:
  - CLI: `python -m yue_core providers-health`
  - transport method: `providers.health`
- OpenAI-compatible provider health hien tai goi `GET /v1/models` de kiem tra endpoint song va model id co xuat hien hay khong.
- Da co runtime settings API cho conversation config:
  - `settings.conversation.get`
  - `settings.conversation.update`
- Desktop shell da co editor cho:
  - `default_provider`
  - route `chat`
  - route `coding_agent`
  - prompt profile `default`
  - prompt profile `coding_agent`
- Editor hien tai da ho tro:
  - apply vao runtime process
  - save route/prompt config nguoc lai file TOML
- Desktop shell da co editor cho `openai.compat` provider config:
  - `backend`
  - `base_url`
  - `model`
  - `api_key_env`
  - `timeout_seconds`
  - `health_timeout_seconds`
  - `temperature`
  - `max_tokens`
- Desktop shell da ho tro add/remove provider rows cho `openai.compat`.
- Update `openai.compat` o runtime se reload plugin/provider registry ngay luc apply.
- Desktop shell da co editor cho `anthropic.messages` provider config:
  - `backend`
  - `base_url`
  - `model`
  - `api_key_env`
  - `anthropic_version`
  - `timeout_seconds`
  - `health_timeout_seconds`
  - `temperature`
  - `max_tokens`
- Desktop shell da ho tro add/remove provider rows cho `anthropic.messages`.
- Desktop shell da co quick presets va custom header editor cho `openai.compat` + `anthropic.messages`.
- Update `anthropic.messages` o runtime se reload plugin/provider registry ngay luc apply.
- Persistence hien tai cover:
  - `conversation` route/prompt config
  - `openai.compat` provider config co san
  - `anthropic.messages` provider config co san
- Chua co editor save cho:
  - `llama.cpp` single-provider path
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
- Google AI / Gemini qua `openai.compat` voi OpenAI compatibility endpoint
- OpenRouter qua `openai.compat`
- Ollama local qua `openai.compat`
- LM Studio local qua `openai.compat`
- llama.cpp local qua `openai.compat` hoac plugin `llama.cpp`
- Custom OpenAI-compatible endpoint qua `openai.compat`
- Claude / Anthropic direct qua `anthropic.messages`

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

1. Chot va verify local path `LM Studio` cho workflow chinh cua agent.
2. Chot source-of-truth va migration story neu sau nay editor save them nhieu bang config khac.
3. Can nhac them adapter Responses API rieng neu muon dung sat hon OpenAI cloud feature set.
4. Them editor cho `llama.cpp` single-provider path, hoac hop nhat ve cung surface, nhung de sau phase core/tooling.
5. Xem `app_development_roadmap.md` de gan cac viec nay vao phase backend/provider tong the.
