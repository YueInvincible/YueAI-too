# App Development Roadmap

## Muc tieu

Ghi thu tu phat trien app theo dung uu tien hien tai.

Source-of-truth moi cho huong "desktop omni-agent" la
`docs/notes/omni_agent_checklist.md`. File nay chi giu phase tong va trang
thai hien co.

Thu tu uu tien da chot ngay 2026-07-08:

1. core agent runtime;
2. desktop UI;
3. permission/tools;
4. memory;
5. plugin/persona ecosystem;
6. 3D avatar/model loading;
7. release hardening.

## Quy tac dat status

- `(done)` = da verify bang lenh/test that va khong con nut co chinh.
- `(almost done, check again + <docsfile>)` = da gan xong nhung con can verify lai, hoac con 1-2 chot nho.
- `(deferred)` = co y tuong/huong, nhung chua phai giai doan hien tai.

## Phase 1: Core agent runtime `(in progress, check + omni_agent_checklist.md)`

### Muc tieu con lai

- Tach agent run state khoi generic chat.
- Durable run record + explicit restart-safe resume da co cho plan, tool calls,
  approvals va verification; UI resume/recovery control van con thieu.
- Giu conversation loop, tool loop, cancel/shutdown, va prompt injection on dinh.
- Giu config/route/prompt profile ro rang.
- Giu permission boundary va audit trail ro rang.
- CLI chat that qua `localhost.chat` da verify duoc; phan con lai la agent-runtime hardening va lifecycle xung quanh desktop/package.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
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

## Phase 2: Desktop shell / UI `(in progress, check + desktop_bridge_status.md)`

### Muc tieu con lai

- Desktop shell phai la control surface cho agent runs, permission, plugins,
  personas, memory, provider, va diagnostics.
- Giu packaged path va debug path dong bo.
- Giam drift giua `desktop/src/app.js` va `desktop/src/runtime.js` truoc khi them UI lon.
- Preview/headless desktop controller da chat that qua `localhost.chat`; viec
  con lai la Tauri packaged path, lifecycle server local, va UI chat/agent
  end-to-end.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
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

## Phase 3: Permission/tools foundation `(in progress, check + omni_agent_checklist.md)`

### Muc tieu con lai

- Mo rong permission tu profile/tool-name sang capability/resource/scope.
- Them approval lifetime: once, run, conversation, session, always-for-scope.
- Giu built-in tools it nhung tot; de plugin/community mo rong tool surface.
- Them tool health, preflight, dry-run, audit, va output-bound contracts.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
- `docs/notes/permissions_and_safety.md`
- `docs/notes/runtime_flow_map.md`

### File chinh

- `src/yue_core/contracts.py`
- `src/yue_core/permissions.py`
- `src/yue_core/tools.py`
- `src/yue_core/builtin_tools.py`
- `src/yue_core/audit.py`
- `src/yue_core/transport.py`
- `tests/test_permissions.py`
- `tests/test_tools.py`

## Phase 4: Memory / observer `(not implemented, design first)`

### Muc tieu con lai

- Working, episodic, semantic/profile memory.
- Privacy, retention, retrieval, source attribution, va user controls.
- Observer nhieu tang: app/window metadata, screenshot/OCR on demand, vision on demand.
- Khong lam always-on vision khi permission/privacy UI chua ro.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
- `docs/notes/memory_and_observer_roadmap.md`
- `docs/notes/permissions_and_safety.md`

### File chinh

- Chua co module memory/observer rieng. Phai thiet ke schema/store truoc khi code.

## Phase 5: Plugin/persona ecosystem `(local plugin loader exists, installer missing)`

### Muc tieu con lai

- Plugin install from GitHub URL, `owner/repo`, curated name, or local folder.
- Manifest declares capability/resource needs and trust level.
- Install disabled by default; enable only after user approval.
- Move untrusted/community plugins out of process.
- Persona package schema for shareable character/personality configs.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
- `docs/PLUGIN_DEVELOPMENT.md`

### File chinh

- `src/yue_core/plugins.py`
- `src/yue_core/contracts.py`
- `src/yue_core/config.py`
- `docs/PLUGIN_DEVELOPMENT.md`
- `tests/test_plugins.py`

## Phase 6: 3D engine / model load `(deferred until core/plugin/memory are stable)`

### Muc tieu

- Load model 3D lightweight.
- Investigate VRM / VTube-like workflow compatibility before implementation.
- Support custom loader adapter interface if practical.
- Dong bo avatar state voi chat/tool/observer events.
- Renderer optional; Yue must still run without avatar.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
- `docs/notes/product_direction.md`
- `docs/notes/memory_and_observer_roadmap.md`

### File chinh

- `desktop/src-tauri/src/main.rs`
- `desktop/src-tauri/src/bridge.rs`
- `desktop/src/runtime.js`
- `desktop/src/app.js`

## Phase 7: Release hardening `(deferred until phases 1-5 are stable)`

### Muc tieu

- Packaged desktop proof.
- Installer proof.
- Core child lifecycle recovery.
- Config/database migration.
- Privacy/security proof.
- Export/import config, personas, plugin list, and memory.

### Sub-roadmap

- `docs/notes/omni_agent_checklist.md`
- `docs/notes/validation_commands.md`
- `docs/notes/desktop_bridge_status.md`

## Thu tu de agent sau biet bat dau o dau

1. Core agent runtime.
2. Desktop shell/UI.
3. Permission/tools foundation.
4. Memory/observer.
5. Plugin/persona ecosystem.
6. 3D engine/model load.
7. Release hardening.
