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
  - active-provider runtime state gio co them:
    - `activeDrawer`
    - `activeProviderSettings`
    - `activeProviderDraft`
    - `activeProviderDraftDirty`
    - `activeProviderCatalog`
    - `activeProviderStatus`
  - panel tool control hien dung state rieng cho:
    - session shell grant (`allowAllCmd*`);
    - parallel inspect status/results;
    - tool catalog metadata.
    - conversation tool activity timeline.

- `desktop/src/protocol.js`
  - source of truth cho API methods ma frontend duoc goi.
  - neu them method moi trong transport, frontend nen expose method tai day.
  - active-provider surface gio da co:
    - `getActiveProviderSettings()`
    - `getActiveProviderCatalog(...)`
    - `updateActiveProviderSettings(...)`
    - `saveActiveProviderSettings(...)`
  - tool guidance surface gio da co:
    - `getToolsGuide(...)`

- `desktop/src/mock.js`
  - source of truth cho preview/mock mode.
  - moi API moi can co mock tuong ung neu muon preview/test JS khong vo.

- `desktop/src/app.js`
  - module-based desktop bootstrap va render logic.
  - dung de doc nhanh logic hien tai.
  - luu y: `index.html` hien khong nap file nay truc tiep; no chu yeu dung cho test/doc va de doi chieu logic module.
  - hien dang render:
    - `Run inspector` gom approval + conversation tool activity;
    - message log group theo `run_id`;
    - session `allow-all-cmd`;
    - tool contract badges/notes;
    - tool playbook runtime-generated cho `coding_agent`;
    - runtime prompt preview co the copy duoc cho `coding_agent`;
    - codex-style manifest rut gon co the copy tu `agent bundle`;
    - starter pack copy-ready cho agent client khac;
    - parallel inspect ket qua theo tung call.
  - can nho: runtime shell moi nhat dang di truoc o `runtime.js`; neu sua desktop behavior, phai check drift.

- `desktop/src/runtime.js`
  - packaged/non-dev runtime script dang duoc `index.html` nap truc tiep.
  - day la runtime thuc te cua shell trong packaged path.
  - shell chat-first moi nhat nam o day:
    - `Ops` va `Config` drawer;
    - provider health/tool contract da duoc dua vao `Ops`;
    - tool playbook runtime-generated cung da duoc dua vao `Ops`;
    - runtime prompt preview va copy action cung da duoc dua vao `Ops`;
    - `agent bundle` va `codex manifest` copy action cung da duoc dua vao `Ops`;
    - `agent starter pack` preview + copy action cung da duoc dua vao `Ops`;
    - khung chat frame co dinh, khong con che do `Focus chat`.
    - active provider co them runtime readiness strip + nut `Refresh runtime`.
  - bat buoc giu dong bo logic voi `app.js` hoac ghi ro cho note neu runtime path di truoc.
  - startup diagnostics gio co them:
    - `runtime_bootstrap_start`
    - `runtime_bootstrap_error`
    - `runtime_setup_error`
    - `runtime_window_error`
    - `runtime_unhandled_rejection`

- `desktop/src-tauri/src/main.rs`
  - ngoai bridge wiring, file nay con giu diagnostic harness cho debug packaged bootstrap.
  - harness gio retry probe callback nhieu lan va ghi stage chi tiet hon (`probe_dispatching`, `probe_dispatched`, `probe_timeout`) de phan biet packaged app dang ket o dau.
  - diagnostic output gio append theo JSONL, khong con ghi de event truoc.

- `desktop/src-tauri/src/bridge.rs`
  - bridge native spawn `python -m yue_core serve` cho desktop shell.
  - runtime startup gio uu tien config theo thu tu:
    - `YUE_CORE_CONFIG`
    - `config.local.toml`
    - `config.example.toml`
    - roi moi fallback ve default core settings.

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
  - `conversation.tool.requested` hien da carry them `request_id` de desktop co the map approval/tool lifecycle ngay ca truoc khi `tool.started`.
  - `coding_agent` request gio duoc cat gon tool catalog ngay tai runtime: uu tien surface alias on dinh `workspace_read` / `workspace_edit` / `shell_run` / `shell_session` / `git_diff` / `todo_update` / `ask_user_approval` thay vi dua ca lop tool cu.
  - system instruction cho `coding_agent` gio noi them 1 tool guide runtime-generated tu chinh catalog da filter nay, de prompt va transport cung dung 1 source-of-truth cho tool usage.

- `src/yue_core/config.py`
  - source of truth cho shape config.
  - route va prompt profile deu duoc validate tai day.
  - CLI/core van giu default an toan neu khong truyen `--config`; desktop native bridge la noi dang tu chon config repo truoc.

- `src/yue_core/transport.py`
  - source of truth cho JSONL method surface.
  - frontend/desktop khong goi truc tiep `YueCore`; no di qua file nay.
  - tool/permission methods moi da co:
    - `tools.list`
    - `tools.guide`
    - `agents.bundle`
    - `agents.starter_pack`
    - `agents.runs.start`
    - `agents.runs.get`
    - `agents.runs.list`
    - `agents.runs.checklist.update`
    - `agents.runs.verification.update`
  - `tools.invoke_many`
  - `audit.recent`
  - `permissions.allow_all_cmd.get`
    - `permissions.allow_all_cmd.set`
  - event forwarding hien forward:
    - `conversation.*`
    - `desktop.*`
    - `approval.*`
    - `tool.*`
    - `permission.*`
  - `tools.list` gio tra ca `model_description` ngoai `description` de agent client nhan du hint ve scrub/parallel/risk contract.
  - `tools.guide` tra them 1 playbook co cau truc cho agent client, tap trung vao workflow inspect/edit/verify va rule "khi nao dung / khi nao tranh" cho tool surface uu tien.
  - `tools.guide` gio con kem them:
    - `execution_rules`
    - `decision_rules`
    - `recipes`
    - `follow_up` / `preferred_inputs` / `examples` theo tung tool
  - CLI gio co `export-tool-guide` de xuat playbook runtime nay ra text hoac JSON cho client agent khac.
  - `agents.bundle` gom route/provider role, active provider snapshot, runtime prompt preview, tool playbook, va filtered tool catalog thanh 1 payload copy/export duoc cho agent client khac.
  - `agents.bundle` gio con kem `codex_manifest`: ban rut gon de feed sang agent client theo style Codex, gom system prompt, workflow, approval/parallellism rules, va tool rules da filter.
  - `codex_manifest` gio con nhung lop machine-readable hon cho integration:
    - `execution_rules`
    - `decision_rules`
    - `recipes`
    - tool-level `summary`, `follow_up`, `preferred_inputs`, `examples`
  - `agents.starter_pack` build tren cung source-of-truth do, nhung tra them payload copy-ready cho nguoi/agent client: starter prompt, integration checklist, va 1 blob markdown de paste thang.
  - `agents.runs.start` tao durable agent-run record rieng, sau do chay
    conversation loop voi `provider_role = coding_agent` mac dinh va dung
    agent run id lam `conversation.run_id` de tool activity/run inspector co
    the map chung mot timeline.
  - `agents.runs.get` va `agents.runs.list` doc lai durable run records tu
    `core.agent_runs`.
  - `agents.runs.checklist.update` ghi structured checklist `id/text/status/note`.
  - `agents.runs.verification.update` ghi verification `status/summary` rieng
    voi run status.
  - Agent run records gio luu:
    - `persona_snapshot`
    - `provider_snapshot`
    - `tool_references`
    - `approval_references`
  - Core subscribe tool/conversation/approval events de upsert references theo
    `run_id`; approval bridge forward them `run_id`, `conversation_id`,
    `tool_call_id` tu `ToolRequest.metadata`.
  - Desktop protocol/mock/runtime clients da co wrapper cho `agents.runs.*`,
    nhung UI panel rieng cho agent runs chua duoc render.
  - CLI gio co `export-agent-starter-pack` de xuat payload nay truc tiep tu terminal ma khong can mo desktop shell.
  - CLI format hien co gom ca full pack va focused slices: `manifest-json`, `system-prompt`, `starter-prompt`, `checklist`.
  - starter pack markdown gio co them muc `Common tool recipes` de human/operator copy nhanh workflow dung tool.
  - `tools.list` cung nhan `provider_role` tuy chon de lay dung tool catalog da duoc policy filter cho `coding_agent`; role nay hien uu tien alias underscore, con ten dotted legacy van duoc giu cho transport/UI flow cu.

- `src/yue_core/openai_compat.py`
  - source of truth cho adapter provider OpenAI-compatible.
  - Ollama, LM Studio, llama.cpp, OpenAI cloud, Google AI, OpenRouter deu quy ve day.

- `src/yue_core/anthropic.py`
  - source of truth cho adapter provider Anthropic Messages API.

- `src/yue_core/providers.py`
  - source of truth cho provider registry va provider health aggregation.

- `src/yue_core/permissions.py`
  - source of truth cho permission profile va actor-aware tool policy.
  - session grant `allow-all-cmd` gio duoc gate ngay tai permission layer: `observe` khong bat duoc, `model` khong tu set duoc.

- `src/yue_core/tools.py`
  - source of truth cho tool registry/executor/audit/event flow.
  - `ToolExecutor` hien co them lop post-process cho command-style tool result de runtime scrub lai `stdout/stderr/status/diff` truoc khi dua vao event/transport/agent.
  - runtime scrub nay gio dua theo `ToolSpec.output_kind` thay vi hardcode theo ten tool.
  - `execute_many(..., parallel=True)` chi cho batch tool read-only khi tat ca tool specs co `metadata.parallel_safe = true` va `metadata.mutates_state = false`.
  - `tool.started` / `tool.finished` event payload da carry them correlation fields tu `ToolRequest.metadata` nhu:
    - `run_id`
    - `conversation_id`
    - `tool_call_id`

- `src/yue_core/builtin_tools.py`
  - source of truth cho tool surface built-in cua agent.
  - command-style output (`shell.exec`, `shell.run`, `shell.session`, `git.*`, `package.install`, `process.kill`) hien duoc runtime scrub ANSI/mau, gom blank line lien tiep, va head-tail truncate truoc khi tra ve agent.
  - `file.read` / `workspace.read` gio cung di qua runtime scrub cho `content`: strip ANSI, collapse blank lines lien tiep, giu metadata `returned_lines` + `truncated`.
  - `file.search` / `workspace.grep` gio scrub tung `match.line` va danh dau `line_truncated` neu can.

- `src/yue_core/contracts.py`
  - `ToolSpec` hien co them `output_kind` + `metadata` de khai bao kieu output va execution hints nhu `parallel_safe`, `mutates_state`.

- `src/yue_core/approval_bridge.py`
  - source of truth cho pending approval queue ma desktop/runtime co the list va resolve.

- `src/yue_core/shell_sessions.py`
  - source of truth cho long-lived shell session manager dung boi `shell.session`.
  - shell argv hien duoc build o che do no-profile/no-rc de giam banner, custom prompt, va ANSI rac truoc khi output duoc scrub.

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
- 1 assistant turn co the phat ra nhieu `tool_calls`; runtime se thuc thi lan luot tung tool call va append tung `tool` message vao history.

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
  - session toggle `allow-all-cmd`
  - parallel inspect bang `tools.invoke_many`
  - tool contract panel hien `output_kind`, `parallel_safe`, `mutates_state`
  - result preview rieng cho tung `workspace.read` call trong parallel inspect
  - `Run inspector` noi `conversation.tool.requested` + `tool.started` + `approval.pending` + `tool.finished` + `conversation.tool.completed`
  - `Run inspector` gio group tool/approval item theo `run_id` thay vi chi render list phang
  - `Run inspector` co them collapse/expand theo run va state nay tach rieng voi message log run groups
  - moi inspector run group co them action mo run dich trong message log
  - message log gio append them structured tool-result entry khi `tool.finished` co correlation cua conversation run
  - message log gio group assistant turn + tool results theo `run_id`; user turn vua gui se duoc backfill `run_id` khi response ve
  - moi run group trong message log gio co the collapse/expand; jump tu inspector se tu mo run dich neu can
  - run group header gio co summary badge/co dem co ban: outcome, user/assistant/tool count, issue count
  - moi run group gio co them summary row trong noi dung: preview assistant turn cuoi va latest tool outcome/error
  - run summary row gio co them action local-first:
    - `Copy summary`
    - `Focus inspector`
    - `Copy answer`
    - `Copy tool result`
    - `Copy run JSON`
  - approval/tool item co the focus va jump toi assistant turn hoac tool-result lien quan trong message log
  - phan biet ro hon:
    - `waiting_approval`
    - `approved_pending_run`
    - `denied_by_user`
    - `denied_by_profile`
  - Permission center trong Ops co:
    - scoped grant list/revoke;
    - recent risky actions/audit preview tu `audit.recent`;
    - refresh rieng cho grant list va audit preview.
  - Run inspector va Permission center audit preview hien permission denial
    metadata theo contract core:
    `denial_category`, `resource_scope`, `rule_id`, `outcome`, `reason`.
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
- `requestApproval`
- `listPendingApprovals`
- `respondApproval`
- `getToolActivitySnapshot`
- `getRecentAudit`
- `listTools`
- frontend module hien chua can wrapper rieng cho `tools.guide`, nhung JSONL method nay da co san neu desktop/agent client muon render tool playbook runtime-generated.
- desktop shell gio da goi `tools.guide` luc bootstrap cho role `coding_agent` va render playbook nay trong `Ops`.
- desktop shell gio cung goi `conversations.prompt_preview` cho role `coding_agent`, de user copy duoc system instruction runtime that thay vi doan tu editor.
- desktop shell gio cung goi `agents.bundle` cho role `coding_agent`, de copy/export duoc 1 snapshot agent surface day du hon.
- desktop shell gio cung cho copy rieng `codex manifest` trich tu `agents.bundle`, de paste nhanh vao agent client hoac tool wrapper ma khong can gui ca payload lon.
- desktop shell gio cung goi `agents.starter_pack` cho role `coding_agent`, de hien 1 preview text co san prompt + checklist + manifest cho integration nhanh.
- `invokeMany`
- `getAllowAllCmd`
- `setAllowAllCmd`
- `createConversation`
- `sendConversationMessage`
- `listProviders`
- `providersHealth`
- `getConversationSettings`
- `updateConversationSettings`
- `saveConversationSettings`
- `getOpenAICompatibleSettings`
- `updateOpenAICompatibleSettings`
- `saveOpenAICompatibleSettings`
- `getAnthropicMessagesSettings`
- `updateAnthropicMessagesSettings`
- `saveAnthropicMessagesSettings`

Core JSONL methods cung da expose tool surface:

- `tools.list`
- `tools.guide`
- `tools.invoke`
- `tools.invoke_many`
- `tools.cancel`
- `tool.activity.snapshot`
- `audit.recent`

Moi method:

- goi `transport.request(...)`
- transport serializes envelope JSONL
- `JsonLineServer.handle_line(...)` xu ly method
- `tools.list` hien tra them `output_kind` + `metadata` de UI/agent client co the doc runtime hints.
- `tools.guide` tra them `workflow[]`, `tools[]`, va `text` de client co the hien huong dan dung tool cung source-of-truth voi runtime prompt.
- `agents.bundle` giu 2 muc export:
  - payload day du cho debug/snapshot;
  - `codex_manifest` rut gon cho huong dan tool/runtime rule theo style Codex.
- `agents.starter_pack` la muc export thu 3, toi uu cho copy/paste:
  - `starter_prompt`
  - `system_prompt`
  - `tool_manifest_json`
  - `integration_checklist[]`
  - `text` markdown
- `tools.invoke_many` cho phep batch tool calls; neu `parallel = true` thi chi chay song song cho tool co `parallel_safe = true` va `mutates_state = false`.

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
- `approval.pending`
- `approval.responded`
- `permission.grant.updated`

Reconnect bootstrap cho tool activity:

- frontend goi them `tool.activity.snapshot`
- core tra `items[]` + `status` tu `ToolActivityStore`
- store nay subscribe:
  - `conversation.*`
  - `approval.*`
  - `tool.*`

Config/runtime startup hien tai:

- `config.example.toml` da duoc canh lai theo huong core workflow local-first:
  - `permissions.profile = "assist"`
  - `interactive_approval = true`
  - `conversation.default_provider = "localhost.chat"`
  - route `chat` + `coding_agent` mac dinh -> `localhost.chat`

## Luu y trang thai hien tai

- `Run inspector` va message log hien da co nhieu helper state/render moi hon ban note cu:
  - `collapsedInspectorRunIds`
  - `groupRunInspectorItems(...)`
  - `findLatestToolActivityForRun(...)`
  - run-level actions `Open run`, `Focus inspector`, `Copy summary`, `Copy answer`, `Copy tool result`, `Copy run JSON`
- Dot UI moi nhat quanh collapse/open-run duoc code xong sau lan verify desktop gan nhat; agent sau neu tiep tuc desktop nen verify lai truoc khi mo rong tiep.

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
  - `ask_user_approval`
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
  - `agents.runs.start` publish `agent.run.created` / `agent.run.started` /
    `agent.run.completed` / `agent.run.failed` / `agent.run.cancelled`;
  - checklist/verification updates publish `agent.run.checklist.updated` va
    `agent.run.verification.updated`;
  - cac action tren cung ghi audit record rieng ngoai `tool.request` / `tool.result`.
- Tool surface van chua khop 100% target roadmap:
  - van song song duy tri ca tool cu `file.*` / `shell.exec` de giu tuong thich test va transport hien tai.
  - approval flow hien co ca `approval.request` va alias `ask_user_approval`; transport/UI van dang dung method `approval.request`.
- Chua co editor cho plugin provider config chi tiet:
  - `llama.cpp` single-provider path
- Chua co config manager/source-of-truth rieng cho persistence.
- Chua co migration story neu runtime editor sau nay save file that.
