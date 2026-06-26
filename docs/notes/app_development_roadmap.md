# App Development Roadmap

## Muc tieu

Ghi thu tu phat trien app theo dung uu tien hien tai:

1. core truoc;
2. tooling cho agent va permission/audit surface tiep theo;
3. backend/protocol/provider/config phuc vu core va agent;
4. UI sau cung khi backend da on;
5. chat phai on va verify duoc truoc khi sang 3D engine;
6. sau 3D engine moi den voice.

## Quy tac dat status

- `(done)` = da verify bang lenh/test that va khong con nut co chinh.
- `(almost done, check again + <docsfile>)` = da gan xong nhung con can verify lai, hoac con 1-2 chot nho.
- `(deferred)` = co y tuong/huong, nhung chua phai giai doan hien tai.

## Phase 1: Core chat engine `(almost done, check again + runtime_flow_map.md)`

### Muc tieu con lai

- giu conversation loop, tool loop, cancel/shutdown, va prompt injection on dinh;
- giu config/route/prompt profile ro rang;
- giu permission boundary va audit trail ro rang.

### Sub-roadmap

- `docs/notes/runtime_flow_map.md`
- `docs/notes/provider_and_prompt_config.md`
- `docs/notes/permissions_and_safety.md`

### File chinh

- `src/yue_core/contracts.py`
- `src/yue_core/conversation.py`
- `src/yue_core/app.py`
- `src/yue_core/transport.py`
- `tests/test_conversation.py`
- `tests/test_transport.py`

## Phase 2: Agent tooling surface `(almost done, check again + agent_roadmap.md)`

### Muc tieu con lai

- chot tool surface cho agent/coding workflow;
- giu transport/contract ro rang cho tool calls, permission checks, va audit;
- uu tien nhung nang luc giup agent lam viec on dinh truoc khi mo rong them UX provider.

### Sub-roadmap

- `docs/notes/agent_roadmap.md`
- `docs/notes/runtime_flow_map.md`
- `docs/notes/permissions_and_safety.md`

### File chinh

- `src/yue_core/tools.py`
- `src/yue_core/permissions.py`
- `src/yue_core/audit.py`
- `src/yue_core/contracts.py`
- `src/yue_core/transport.py`
- `tests/test_tools.py`
- `tests/test_permissions.py`

## Phase 3: Backend/provider stack `(almost done, check again + provider_and_prompt_config.md)`

### Muc tieu con lai

- provider routing theo `chat` va `coding_agent`;
- OpenAI-compatible layer cho OpenAI/Google/OpenRouter/Ollama/LM Studio/llama.cpp/custom;
- direct Claude path qua Anthropic Messages API;
- provider health va runtime settings editor;
- `LM Studio` la local path uu tien cao nhat trong giai doan nay;
- mo rong editor `llama.cpp` de sau, khong phai blocker cho core.

### Sub-roadmap

- `docs/notes/provider_and_prompt_config.md`
- `docs/notes/model_runtime_direction.md`
- `docs/notes/hardware_constraints.md`
- `docs/notes/validation_commands.md`

### File chinh

- `src/yue_core/config.py`
- `src/yue_core/providers.py`
- `src/yue_core/openai_compat.py`
- `src/yue_core/cli.py`
- `plugins/openai_compatible/plugin.py`
- `plugins/llama_cpp/plugin.py`
- `config.example.toml`

## Phase 4: Desktop shell / UI `(almost done, check again + desktop_bridge_status.md)`

### Muc tieu con lai

- desktop shell phai render duoc provider health va runtime settings;
- packaged path va debug path phai dong bo;
- UI phai doc dung snapshot/state tu core.

### Sub-roadmap

- `docs/notes/desktop_bridge_status.md`
- `docs/notes/runtime_flow_map.md`
- `docs/notes/validation_commands.md`

### File chinh

- `desktop/index.html`
- `desktop/src/styles.css`
- `desktop/src/state.js`
- `desktop/src/protocol.js`
- `desktop/src/mock.js`
- `desktop/src/app.js`
- `desktop/src/runtime.js`

## Phase 5: Chat stabilization gate `(almost done, check again + validation_commands.md)`

### Muc tieu con lai

- chat phai chay on dinh tren core + backend + UI;
- kiem tra lai test, packaged path, va cleanup behavior;
- chi khi phase nay on dinh moi chot huong 3D engine.

### Sub-roadmap

- `docs/notes/validation_commands.md`
- `docs/notes/desktop_bridge_status.md`

### Done khi

- JS tests pass;
- Python tests pass;
- Rust tests pass;
- chat send/stream/tool-call loop can verify that.

## Phase 6: 3D engine / model load `(deferred until chat is stable)`

### Muc tieu

- load model 3D;
- render avatar engine;
- dong bo state cua avatar voi chat/observer.

### Sub-roadmap

- `docs/notes/product_direction.md`
- `docs/notes/memory_and_observer_roadmap.md`

### File chinh

- `desktop/src-tauri/src/main.rs`
- `desktop/src-tauri/src/bridge.rs`
- `desktop/src/runtime.js`
- `desktop/src/app.js`

## Phase 7: Voice `(deferred)`

### Muc tieu

- STT;
- TTS;
- interruption/cancel;
- stream audio pipeline.

### Sub-roadmap

- `docs/notes/voice_deferred_scope.md`

## Thu tu de agent sau biet bat dau o dau

1. Core chat engine.
2. Agent tooling surface.
3. Backend/provider stack.
4. Desktop shell/UI.
5. Chat stabilization gate.
6. 3D engine/model load.
7. Voice.
