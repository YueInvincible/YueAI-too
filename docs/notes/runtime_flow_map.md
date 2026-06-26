# Runtime Flow Map

## Muc dich

File nay ghi lai co che hoat dong va moi lien he code cua cac phan da duoc lam ky nhat.
Muc tieu la de agent sau khong phai doc lai tung file moi hieu duong di chinh.

## Pham vi file nay

Tap trung vao:

- core runtime;
- conversation/provider routing;
- tool/permission/audit surface cho agent;
- OpenAI-compatible provider layer;
- JSONL transport;
- desktop shell state/protocol/runtime;
- runtime settings editor;
- provider health flow.

Khong co gang mo ta day du cac domain chua lam ky nhu voice, memory, observer, game mode.

## Bieu do tong quat

```text
Desktop shell UI
  index.html
    -> runtime.js (packaged/non-dev path)
    -> app.js (module path cho desktop/src khi test/doc)
      -> protocol.js
      -> mock.js
      -> state.js
      -> tauriTransport.js
      -> coreSession.js / bridgeClient.js / jsonlBridge.js
        -> JSONL request/response
          -> yue_core.transport.JsonLineServer
            -> YueCore
              -> DesktopSessionManager
              -> ConversationOrchestrator
              -> ModelProviderRegistry
              -> ToolExecutor / ToolRegistry / PermissionEngine
              -> PluginManager
                -> fake.echo / llama.cpp / openai.compat / anthropic.messages
```

## Source of truth theo tung lop

### Desktop UI

- `desktop/index.html`
  - source of truth cho structure cua shell.
  - neu can them panel, dong text, form field, bat dau tu day.

- `desktop/src/styles.css`
  - source of truth cho look/spacing cua shell.

- `desktop/src/state.js`
  - source of truth cho desktop view-state shape.
  - neu UI can render them state moi, phai them vao day truoc.

- `desktop/src/protocol.js`
  - source of truth cho API methods ma frontend duoc goi.
  - neu them method moi trong transport, frontend nen expose method tai day.

- `desktop/src/mock.js`
  - source of truth cho preview/mock mode.
  - moi API moi can co mock tuong ung neu muon preview/test JS khong vo.

- `desktop/src/app.js`
  - module-based desktop bootstrap va render logic.
  - dung de doc nhanh logic hien tai.

- `desktop/src/runtime.js`
  - packaged/non-dev runtime script dang duoc `index.html` nap truc tiep.
  - day la runtime thuc te cua shell trong packaged path.
  - bat buoc giu dong bo logic voi `app.js`.

### Core

- `src/yue_core/app.py`
  - source of truth cho wiring toan bo core.
  - tao va ket noi events, providers, plugins, desktop session, conversation orchestrator.
  - neu can biet service nao duoc register o dau, doc file nay truoc.

- `src/yue_core/conversation.py`
  - source of truth cho conversation loop:
    - luu user message;
    - tao model request;
    - stream delta;
    - tool-call loop;
    - cancel/shutdown;
    - prompt-profile system injection.

- `src/yue_core/config.py`
  - source of truth cho shape config.
  - route va prompt profile deu duoc validate tai day.

- `src/yue_core/transport.py`
  - source of truth cho JSONL method surface.
  - frontend/desktop khong goi truc tiep `YueCore`; no di qua file nay.

- `src/yue_core/openai_compat.py`
  - source of truth cho adapter provider OpenAI-compatible.
  - Ollama, LM Studio, llama.cpp, OpenAI cloud, Google AI, OpenRouter deu quy ve day.

- `src/yue_core/anthropic.py`
  - source of truth cho adapter provider Anthropic Messages API.

- `src/yue_core/providers.py`
  - source of truth cho provider registry va provider health aggregation.

- `src/yue_core/permissions.py`
  - source of truth cho permission profile va actor-aware tool policy.

- `src/yue_core/tools.py`
  - source of truth cho tool registry/executor/audit/event flow.

- `src/yue_core/builtin_tools.py`
  - source of truth cho tool surface built-in cua agent.
  - command-style output (`shell.exec`, `git.*`, `package.install`, `process.kill`) hien duoc runtime scrub ANSI/mau, gom blank line lien tiep, va head-tail truncate truoc khi tra ve agent.
  - `file.read` hien tra them metadata `returned_lines` + `truncated` khi doan doc qua dai.

## Conversation/provider routing flow

### Config layer

`config.py` hien co 3 lop can phan biet:

- `default_provider`
  - fallback provider cho conversation neu route khong override.

- `routes`
  - mapping theo role:
    - `chat`
    - `coding_agent`
  - moi role co:
    - `provider`
    - `prompt_profile`

- `prompt_profiles`
  - mapping ten profile -> 4 truong:
    - `personality`
    - `system_instruction`
    - `tool_instruction`
    - `response_instruction`

### Runtime layer

`YueCore.__init__` trong `app.py`:

- doc `settings.conversation`
- normalize routes
- truyen vao `ConversationOrchestrator`

`ConversationOrchestrator.send(...)`:

- nhan `provider_name` override hoac `provider_role`
- `resolve_provider(...)` quyet dinh provider can dung
- `resolve_prompt_profile(...)` quyet dinh prompt profile can dung
- `_system_instruction(...)` build 1 system message tam thoi
- `_request_messages(...)` chen system message vao request truoc khi goi provider

Quan trong:

- prompt profile hien tai **khong duoc persist vao message history**
- no chi duoc inject vao `ModelRequest` luc generate

### Runtime settings editor layer

`YueCore` hien co:

- `conversation_settings_snapshot()`
- `update_conversation_settings(payload)`
- `openai_compatible_settings_snapshot()`
- `update_openai_compatible_settings(payload)`
- `anthropic_messages_settings_snapshot()`
- `update_anthropic_messages_settings(payload)`

Chuc nang:

- lay snapshot route/prompt hien tai
- validate payload moi
- check provider duoc tham chieu co ton tai trong registry
- check prompt profile duoc route tham chieu co ton tai
- cap nhat:
  - `self.settings.conversation`
  - `self.conversations.default_provider`
  - `self.conversations.routes`
  - `self.conversations.prompt_profiles`
- neu `persist = true`:
  - ghi lai file TOML qua `save_settings(...)`
  - mac dinh dung `settings.config_path` neu co, nguoc lai la `config.local.toml`
- publish event/audit cho update

Gioi han quan trong:

- editor route/prompt da co 2 che do:
  - apply runtime
  - save ve TOML
- editor `openai.compat` da co 2 che do:
  - apply runtime
  - save ve TOML
- editor `anthropic.messages` da co 2 che do:
  - apply runtime
  - save ve TOML
- update `openai.compat` se reload plugin/provider registry tai runtime truoc khi tra ket qua
- update `anthropic.messages` se reload plugin/provider registry tai runtime truoc khi tra ket qua
- UI hien tai cover:
  - conversation route/prompt
  - `openai.compat` provider config co san
  - `anthropic.messages` provider config co san
- UI da ho tro:
  - add/remove provider rows cho `openai.compat`
  - add/remove provider rows cho `anthropic.messages`
  - quick presets cho `openai.compat`
  - quick preset Claude API cho `anthropic.messages`
  - custom header editor cho `openai.compat`
  - custom header editor cho `anthropic.messages`
- chua co editor day du cho:
  - `llama.cpp` single-provider path

## Provider layer flow

### fake.echo

- duoc register trong `app.py`
- dung cho test va default fallback
- co `health()` don gian, luon `ok`

### openai.compat

- plugin `plugins/openai_compatible/plugin.py`
- doc config `providers = [...]`
- moi entry tao 1 `OpenAICompatibleProvider`

`OpenAICompatibleProvider` trong `openai_compat.py`:

- dung `POST /v1/chat/completions` cho streaming chat/tool-call
- dung `GET /v1/models` cho health
- backend chi anh huong:
  - `base_url` mac dinh
  - API-key behavior mac dinh

Backends dang quy ve adapter chung:

- `openai`
- `google`
- `openrouter`
- `ollama`
- `lmstudio`
- `llama.cpp`
- `custom`

### anthropic.messages

- plugin `plugins/anthropic_messages/plugin.py`
- doc config `providers = [...]`
- moi entry tao 1 `AnthropicMessagesProvider`

`AnthropicMessagesProvider` trong `anthropic.py`:

- dung `POST /v1/messages` cho streaming chat/tool-call
- dung `GET /v1/models` cho health
- map:
  - transient system prompt -> top-level `system`
  - Yue tool call -> Anthropic `tool_use`
  - Yue tool result -> Anthropic `tool_result`

### llama.cpp plugin

- `plugins/llama_cpp/plugin.py`
- hien tai chi la wrapper mong de giu tuong thich config/plugin cu
- logic HTTP thuc te nam o `openai_compat.py`

## Provider health flow

### Core

- frontend goi `providers.health`
- `transport.py` route sang `await core.providers.health()`
- `providers.py` gather `health()` cua tung provider
- neu provider throw exception:
  - registry tra item `ok = False`
  - khong lam sap ca request

### OpenAI-compatible provider

`health()`:

- goi `GET /v1/models`
- neu thanh cong:
  - `ok = True`
  - `reachable = True`
  - neu model duoc chon xuat hien trong list:
    - `model_available = True`
- neu request loi:
  - `ok = False`
  - `reachable = False`
  - co `error`

### Desktop UI

`app.js` / `runtime.js` bootstrap:

- `client.listProviders()`
- `client.providersHealth()`
- state luu:
  - `availableProviders`
  - `providerHealth`
  - `providerHealthSummary`

UI hien:

- dong summary tren avatar card
- list chi tiet trong console panel

## JSONL transport flow

### Tu frontend sang core

Frontend methods trong `protocol.js`:

- `desktopState`
- `desktopAttach`
- `desktopDetach`
- `desktopCommand`
- `createConversation`
- `sendConversationMessage`
- `listProviders`
- `providersHealth`
- `getConversationSettings`
- `updateConversationSettings`
- `getOpenAICompatibleSettings`
- `updateOpenAICompatibleSettings`
- `getAnthropicMessagesSettings`
- `updateAnthropicMessagesSettings`

Core JSONL methods cung da expose tool surface:

- `tools.list`
- `tools.invoke`
- `tools.cancel`

Moi method:

- goi `transport.request(...)`
- transport serializes envelope JSONL
- `JsonLineServer.handle_line(...)` xu ly method

### Tu core sang frontend

Core publish `CoreEvent`
-> `JsonLineServer.serve()` forward event envelopes
-> `jsonlBridge.js` router nhan event
-> `app.js` / `runtime.js` call `applyCoreEvent(...)`

Topics desktop shell dang de y:

- `desktop.state.changed`
- `conversation.delta`
- `conversation.run.completed`
- `conversation.run.failed`
- `conversation.run.cancelled`

## Desktop shell bootstrap flow

### Preview/mock mode

- `index.html` nap `runtime.js`
- neu khong co Tauri invoke:
  - dung `createMockTransport()`
- shell van:
  - attach desktop session
  - doc provider health
  - doc conversation settings
  - render editor va provider panel

### Native/packaged mode

- `runtime.js` co gang detect Tauri invoke
- neu co:
  - dung `createTauriTransport(...)`
  - co them `bridge_runtime_info`
  - poll `bridge_drain_events`
- shell attach vao desktop session, roi render state

## Moi lien he giua app.js va runtime.js

Day la diem agent sau de nham nhat.

- `app.js`
  - module source de doc va sua cho ro rang.

- `runtime.js`
  - self-invoking bundled-style runtime script dang duoc HTML dung truc tiep.

Hau qua:

- neu sua feature desktop shell ma chi sua `app.js`, packaged path co the khong doi
- neu sua chi `runtime.js`, test module path co the lech hanh vi

Thuc te hien tai:

- can coi 2 file nay la hai implementation can giu dong bo
- neu sau nay refactor, day la ung vien so 1 can hop nhat

## Neu agent sau sua phan nao thi nen doc gi

### Sua tooling / permission / audit

Doc:

- `src/yue_core/contracts.py`
- `src/yue_core/permissions.py`
- `src/yue_core/tools.py`
- `src/yue_core/builtin_tools.py`
- `src/yue_core/conversation.py`
- `tests/test_permissions.py`
- `tests/test_tools.py`

### Sua provider route/prompt editor UI

Doc:

- `desktop/index.html`
- `desktop/src/styles.css`
- `desktop/src/state.js`
- `desktop/src/protocol.js`
- `desktop/src/mock.js`
- `desktop/src/app.js`
- `desktop/src/runtime.js`
- `src/yue_core/transport.py`
- `src/yue_core/app.py`

### Sua provider runtime / them backend moi

Doc:

- `src/yue_core/openai_compat.py`
- `src/yue_core/anthropic.py`
- `src/yue_core/providers.py`
- `plugins/openai_compatible/plugin.py`
- `plugins/anthropic_messages/plugin.py`
- `plugins/llama_cpp/plugin.py`
- `config.example.toml`
- `docs/OPENAI_COMPAT_PROVIDER.md`
- `docs/ANTHROPIC_PROVIDER.md`

### Sua conversation loop / tool loop

Doc:

- `src/yue_core/conversation.py`
- `src/yue_core/contracts.py`
- `src/yue_core/app.py`
- `tests/test_conversation.py`

### Sua desktop bridge/protocol

Doc:

- `src/yue_core/transport.py`
- `desktop/src/jsonlBridge.js`
- `desktop/src/bridgeClient.js`
- `desktop/src/tauriTransport.js`
- `desktop/src-tauri/src/bridge.rs`

## Phan con thieu ma agent sau can nho

- Core da co tool surface built-in cho agent:
  - `file.read`
  - `file.list`
  - `file.search`
  - `file.write`
  - `file.edit`
  - `file.move`
  - `file.delete`
  - `shell.exec`
  - `process.list`
  - `process.kill`
  - `git.status`
  - `git.diff`
  - `package.install`
- Core da co them lop tool name gan hon voi target agent surface:
  - `workspace.list`
  - `workspace.read`
  - `workspace.search`
  - `workspace.grep`
  - `workspace.write`
  - `workspace.edit`
  - `workspace.ops`
  - `approval.request`
  - `shell.run`
  - `shell.session`
  - `todo.update`
- Permission hien tai da biet profile va actor:
  - `observe`
  - `assist`
  - `admin`
  - `model` vs `user/ui`
- Tool result trong conversation loop da co payload:
  - `request_id`
  - `tool_name`
  - `ok`
  - `status`
  - `output`
  - `error`
- Tool output hygiene da co mot lop co ban o built-in tools:
  - strip ANSI escape codes;
  - collapse blank lines lien tiep cho command-style output;
  - truncate head-tail voi canh bao neu output qua dai.
- Tool/event observability da ro hon:
  - `approval.request` publish `approval.requested` + `approval.resolved`;
  - `shell.session` publish `shell.session.started` / `read` / `listed` / `stopped`;
  - cac action tren cung ghi audit record rieng ngoai `tool.request` / `tool.result`.
- Tool surface van chua khop 100% target roadmap:
  - van song song duy tri ca tool cu `file.*` / `shell.exec` de giu tuong thich test va transport hien tai.
  - ten tool approval hien tai la `approval.request`, chua phai exact string `ask_user_approval` trong roadmap prompt.
- Chua co editor cho plugin provider config chi tiet:
  - `llama.cpp` single-provider path
- Chua co config manager/source-of-truth rieng cho persistence.
- Chua co migration story neu runtime editor sau nay save file that.
