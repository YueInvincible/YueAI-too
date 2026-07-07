# Agent Roadmap

## Muc dich

File nay la route map thuc te cho agent sau: bat dau tu dau, mo file nao truoc, va phan nao la boundary hien tai cua codebase.

## Noi dung can nho ngay

- `PROJECT_HANDOFF.md` chi la muc luc ngan.
- `runtime_flow_map.md` la file context chinh cho phan da co wiring ro.
- `provider_and_prompt_config.md` la file chinh cho route provider, prompt profile, va editor lien quan.
- `desktop_bridge_status.md` la file chinh cho bridge / non-dev / packaged proof.
- `app_development_roadmap.md` la file chinh cho thu tu phat trien san pham tong the.
- Uu tien hien tai: core + tooling cho agent truoc; local host OpenAI-compatible server tai `127.0.0.1:8080` la local provider path uu tien; `LM Studio` la path phu.
- Surface tool uu tien cho `coding_agent` da chot theo alias underscore de prompt va runtime noi cung mot ngon ngu: `workspace_list`, `workspace_read`, `workspace_search`, `workspace_grep`, `workspace_write`, `workspace_edit`, `workspace_ops`, `shell_run`, `shell_session`, `git_status`, `git_diff`, `todo_update`, `ask_user_approval`.
- `docs/*.md` o root la reference docs. Khong mo mac dinh tru khi note trong `docs/notes/` dan ro.

## Thu tu mo file khuyen nghi

1. `PROJECT_HANDOFF.md`
2. `docs/notes/agent_start_here.md`
3. `docs/notes/runtime_flow_map.md`
4. `docs/notes/app_development_roadmap.md`
5. `docs/notes/provider_and_prompt_config.md`
6. `docs/notes/desktop_bridge_status.md` khi task lien quan desktop shell / bridge / runtime path
7. `docs/notes/validation_commands.md` khi can verify

## Phan code cua "vung em" hien tai

Vung nay la lop noi giua desktop UI, protocol, transport, va core settings/provider routing.

### Desktop shell

- `desktop/index.html`
  - khai bao structure UI.
  - dat cac panel, form, datalist, va button cho console / settings / provider status.
  - neu can them field moi, bat dau tu day.

- `desktop/src/styles.css`
  - quyet dinh layout, spacing, va visual state.
  - moi panel moi can class/style phu hop trong file nay.

- `desktop/src/state.js`
  - source of truth cho view-state.
  - moi field UI moi phai duoc them vao day truoc de render an toan.
  - tool control UX moi cung di qua day:
    - `allowAllCmd*`
    - `parallelInspect*`
    - `toolsCatalog`
    - `toolActivity*`

- `desktop/src/protocol.js`
  - source of truth cho method surface frontend duoc goi.
  - neu them method moi o core transport thi frontend nen expose o day truoc.

- `desktop/src/mock.js`
  - preview/mock transport.
  - moi method protocol moi nen co mock tuong ung de test UI khong vo.

- `desktop/src/app.js`
  - module-path bootstrap va render logic.
  - day la file de doc nhanh khi muon hieu flow UI.

- `desktop/src/runtime.js`
  - packaged-path runtime thuc te.
  - phai giu dong bo voi `app.js`.
  - neu sua flow UI, gan nhu chac chan phai sua ca hai file.

### Core / transport / config

- `src/yue_core/config.py`
  - source of truth cho schema config.
  - validate default provider, routes, prompt profiles, desktop settings, va plugin config.

- `src/yue_core/app.py`
  - wiring core.
  - tao registry, providers, permissions, desktop session, va conversation orchestrator.
  - neu can biet state nao duoc cap nhat o dau, doc file nay truoc.

- `src/yue_core/transport.py`
  - JSONL method surface ma desktop / shell goi vao.
  - UI khong goi truc tiep `YueCore`; no di qua file nay.

- `src/yue_core/providers.py`
  - registry va provider health aggregation.

- `src/yue_core/openai_compat.py`
  - adapter chung cho OpenAI-compatible backends.
  - Ollama, LM Studio, llama.cpp, OpenAI cloud deu chay qua lop nay.

- `src/yue_core/cli.py`
  - entrypoint cho doctor, serve, providers-health, chat, invoke.
  - dung de verify nhanh config va provider routing tren terminal.

## Moi lien he code can hieu

### UI den core

`desktop/index.html`
-> `desktop/src/runtime.js` hoac `desktop/src/app.js`
-> `desktop/src/protocol.js`
-> `src/yue_core/transport.py`
-> `src/yue_core/app.py`
-> `src/yue_core/config.py` / `src/yue_core/providers.py` / `src/yue_core/openai_compat.py`

### Mock path

`desktop/src/mock.js`
phai mirror method names va payload shape cua `protocol.js`.

### Settings / routing path

- `config.py` quyet dinh du lieu hop le la gi.
- `app.py` nhan snapshot va apply vao runtime core.
- `transport.py` la cua vao tu UI.
- `protocol.js` va `mock.js` giu frontend khong lech API.

### Provider health path

- `providers.health` tu transport -> registry -> tung provider.
- UI chi hieu `ok`, `backend`, `model`, `error`, `model_available`.
- neu doi shape health payload, phai doi ca frontend render.

## Neu bat dau tu task moi thi nen lam gi

### Neu task lien quan UI/runtime editor

1. Doc `provider_and_prompt_config.md`.
2. Doc `runtime_flow_map.md`.
3. Mo `desktop/index.html`.
4. Mo `desktop/src/state.js`.
5. Mo `desktop/src/protocol.js`.
6. Mo `desktop/src/mock.js`.
7. Mo `desktop/src/app.js`.
8. Mo `desktop/src/runtime.js`.

Neu task tiep theo la tool UX/approval UX:

1. Doc `permissions_and_safety.md`.
2. Doc `runtime_flow_map.md`.
3. Mo `desktop/src/state.js`.
4. Mo `desktop/src/app.js`.
5. Mo `desktop/src/runtime.js`.
6. Neu can doi contract/event thi mo them `src/yue_core/transport.py`, `src/yue_core/tools.py`, `src/yue_core/conversation.py`.

### Neu task lien quan persistence config

1. Doc `provider_and_prompt_config.md`.
2. Doc `runtime_flow_map.md`.
3. Mo `src/yue_core/config.py`.
4. Mo `src/yue_core/app.py`.
5. Mo `src/yue_core/transport.py`.
6. Mo `config.example.toml`.

### Neu task lien quan bridge / non-dev path

1. Doc `desktop_bridge_status.md`.
2. Doc `runtime_flow_map.md`.
3. Mo `desktop/src-tauri/src/main.rs`.
4. Mo `desktop/src-tauri/src/bridge.rs`.
5. Mo `desktop/src/runtime.js`.

## Khong nen doc lan man

- Khong mo `desktop/src-tauri/target/` khi khong can.
- Khong doc cac note voice/memory nếu task khong cham toi no.
- Khong doc toan bo `conversation.py` neu task chi chua cham routing/settings/bridge.

## Mau lifestyle cho agent sau

- Doc note truoc, code sau.
- Chi mo file lien quan truc tiep.
- Neu thay method hay shape payload doi, cap nhat ca frontend, transport, mock, va test co lien quan.
- Neu task co the thay doi config hoac docs, luon update note lien quan sau khi verify xong.
