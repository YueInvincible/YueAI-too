# Agent Start Here

## Muc dich

File nay de agent sau chon dung diem bat dau, tranh doc lan man va ton token.

Nguyen tac:

- Doc handoff chinh truoc.
- Sau do chi mo note dung domain.
- Khong doc toan bo `docs/notes` neu task moi chi cham 1 vung nho.
- `docs/*.md` o root la reference docs, khong phai onboarding docs.
- Neu task nam trong phan da duoc map ky, doc `runtime_flow_map.md` truoc khi doc code.

## Thu tu doc toi thieu

1. `PROJECT_HANDOFF.md`
2. `docs/notes/agent_roadmap.md`
3. 1 note dung domain
4. `runtime_flow_map.md` neu task lien quan core/provider/desktop shell
5. code files duoc chi dinh trong note

## Budget goi y

- Neu task nho:
  - dung doc qua 3 file note truoc khi mo code.
- Neu task trung binh:
  - toi da 5 file note/reference truoc khi mo code.
- Chi mo `docs/*.md` o root khi can protocol/provider details cu the.

## Neu task la...

### Truoc het

- Neu muon lay ngay thu tu mo file cho phan dang lam, doc `agent_roadmap.md` truoc.
- Neu muon lay thu tu phat trien san pham tong the, doc `app_development_roadmap.md` truoc.
- Neu task lien quan logic tool/permission/audit cho agent:
  - doc `permissions_and_safety.md`
  - doc `runtime_flow_map.md`
  - sau do mo code core.

### 1. Desktop shell UI

Doc truoc:

- `docs/notes/desktop_bridge_status.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `desktop/index.html`
2. `desktop/src/styles.css`
3. `desktop/src/state.js`
4. `desktop/src/protocol.js`
5. `desktop/src/mock.js`
6. `desktop/src/app.js`
7. `desktop/src/runtime.js`

Chu y:

- `runtime.js` la packaged-path runtime thuc te
- `app.js` la module-path logic de doc/sua de hieu hon
- sua desktop feature thi de y ca hai file

### 2. Provider route / prompt editor

Doc truoc:

- `docs/notes/provider_and_prompt_config.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `src/yue_core/app.py`
2. `src/yue_core/transport.py`
3. `desktop/src/protocol.js`
4. `desktop/src/app.js`
5. `desktop/src/runtime.js`

Chu y:

- editor hien tai la runtime-only
- neu task la save file config, se can mo rong boundary nay

### 3. OpenAI / Ollama / LM Studio / llama.cpp runtime

Doc truoc:

- `docs/notes/provider_and_prompt_config.md`
- `docs/notes/model_runtime_direction.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `src/yue_core/openai_compat.py`
2. `src/yue_core/providers.py`
3. `plugins/openai_compatible/plugin.py`
4. `plugins/llama_cpp/plugin.py`
5. `config.example.toml`

### 4. Conversation loop / tool-call loop

Doc truoc:

- `docs/CONVERSATION_PROTOCOL.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `src/yue_core/contracts.py`
2. `src/yue_core/conversation.py`
3. `src/yue_core/app.py`
4. `tests/test_conversation.py`

### 4b. Tooling / permission / audit cho agent

Doc truoc:

- `docs/notes/permissions_and_safety.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `src/yue_core/contracts.py`
2. `src/yue_core/permissions.py`
3. `src/yue_core/tools.py`
4. `src/yue_core/builtin_tools.py`
5. `src/yue_core/conversation.py`
6. `tests/test_permissions.py`
7. `tests/test_tools.py`

### 5. Desktop bridge / JSONL transport / Tauri

Doc truoc:

- `docs/notes/desktop_bridge_status.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `src/yue_core/transport.py`
2. `desktop/src/jsonlBridge.js`
3. `desktop/src/bridgeClient.js`
4. `desktop/src/tauriTransport.js`
5. `desktop/src-tauri/src/bridge.rs`
6. `desktop/src-tauri/src/main.rs`

### 6. Persistence ve TOML cho runtime editor

Doc truoc:

- `docs/notes/provider_and_prompt_config.md`
- `docs/notes/runtime_flow_map.md`

Mo code theo thu tu:

1. `src/yue_core/config.py`
2. `src/yue_core/app.py`
3. `src/yue_core/transport.py`
4. `config.example.toml`

Chu y:

- chua co config manager rieng
- se can quyet dinh source-of-truth va safe write strategy truoc khi code

## Decision tree nhanh

### Neu can UI thay doi nhung khong ro backend o dau

- Doc `runtime_flow_map.md`
- Tim method protocol UI dang goi
- Tim method JSONL transport tuong ung
- Tim service/core method ben trong

### Neu can sua backend nhung khong ro UI co dung no khong

- Doc `runtime_flow_map.md`
- `rg` method name trong `desktop/src`
- check `tests/test_transport.py` va `desktop/tests/protocol.test.js`

## Dung doc nham domain

- Muon sua desktop shell khong can doc memory/voice notes.
- Muon sua provider routing khong can doc desktop packaged-proof chi tiet, tru khi task co dong vao bridge.
- Muon sua lifecycle Tauri khong can doc tung file provider plugin tru khi co thay doi startup core.

## Diem de agent sau khong bi mat thoi gian

- `PROJECT_HANDOFF.md` la muc luc, khong phai operational manual.
- `runtime_flow_map.md` moi la file operational context cho phan da lam ky.
- Neu task nam ngoai phan da map ky, phai doc them code that, khong nen doan.
