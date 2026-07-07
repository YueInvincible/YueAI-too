# Desktop Bridge Status

## Muc dich

- Tom tat desktop bridge / shell / packaged-path da di toi dau.
- Chi ra file can mo truoc khi sua desktop runtime.
- Giu note nay ngan, uu tien facts da verify.

## File quan trong

### Core protocol

- [src/yue_core/desktop.py](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\src\yue_core\desktop.py)
- [src/yue_core\transport.py](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\src\yue_core\transport.py)
- [src/yue_core\contracts.py](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\src\yue_core\contracts.py)

### Frontend shell

- [desktop/index.html](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\index.html)
- [desktop/src/app.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\app.js)
- [desktop/src/runtime.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\runtime.js)
- [desktop/src/state.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\state.js)
- [desktop/src/tauriTransport.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\tauriTransport.js)

### Native shell

- [desktop/src-tauri/src/main.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\main.rs)
- [desktop/src-tauri/src/bridge.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\bridge.rs)
- [desktop/src-tauri/tauri.conf.json](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\tauri.conf.json)

## Da verify

- `python -m yue_core serve` forward duoc ca:
  - `conversation.*`
  - `desktop.*`
  - `approval.*`
  - `tool.*`
- Rust bridge co the:
  - spawn `python -m yue_core serve`
  - gui request/nhan response that
  - nhan forwarded events
  - shutdown sach
  - trong runtime native, bridge gio uu tien config theo thu tu:
    - `YUE_CORE_CONFIG`
    - `config.local.toml`
    - `config.example.toml`
    - fallback default core settings neu khong co file nao
- Frontend shell co the:
  - doc `bridge_runtime_info`
  - poll `bridge_drain_events`
  - apply `desktop.state.changed`
  - render `conversation.delta` trong native mode
- Frontend shell da co approval flow trong console:
  - doc `approval.pending.list`
  - react voi event `approval.pending` / `approval.responded`
  - gui `approval.respond` de approve/deny tu UI
- Frontend shell da co panel tool control/contract:
  - toggle `allow-all-cmd` theo session qua `permissions.allow_all_cmd.get/set`
  - parallel inspect bang `tools.invoke_many`
  - tool contract badges cho `output_kind`, `parallel_safe`, `mutates_state`
  - result list rieng cho tung parallel inspect call
- Frontend shell da co conversation tool activity panel:
  - UX hien tai da duoc gom lai thanh `Run inspector` thay vi tach rieng panel approval va panel tool activity
  - render `conversation.tool.requested`
  - render `tool.started` / `tool.finished`
  - render trang thai cho approval dang cho xu ly tren tool request do
  - map event theo `run_id` / `tool_call_id` / `request_id`
  - approval panel va tool activity panel hien da link truc tiep qua `request_id`
  - bootstrap reconnect gio co them `tool.activity.snapshot` de hydrate lai timeline dang mo
  - `Run inspector` khong con la list phang: item gio duoc group theo `run_id`, phan run-less/pending approval rieng van duoc render standalone
  - moi inspector run group gio co the collapse/expand doc lap, khong dung chung state thu gon voi message log
  - header cua moi inspector run group gio co the jump thang sang run group tuong ung trong message log
  - approval/tool item gio co the jump toi assistant turn hoac tool-result entry lien quan trong message log
  - message log gio co them structured `tool` result entries cho conversation tool calls
  - message log khong con la stream phang: assistant turn + tool results duoc gom theo `run_id`
  - tung run group co the thu gon/mo rong ngay trong message log
  - header moi run da co summary badge/tong ket co ban de doc nhanh outcome
  - ben trong moi run da co them summary row preview noi dung assistant/tool moi nhat
  - summary row moi run da co them action copy local-first:
    - `Copy summary`
    - `Focus inspector`
    - `Copy answer`
    - `Copy tool result`
    - `Copy run JSON`
  - item tool co the hien ro:
    - waiting approval
    - approved, dang cho chay
    - denied by user
    - blocked by profile
- Provider health va runtime settings editor da render trong shell.
- Provider config editor da co cho:
  - `openai.compat`
  - `anthropic.messages`
- `openai.compat` va `anthropic.messages` editor da co:
  - add/remove provider rows
  - quick presets
  - custom header editor
- Chat shell hien tai da duoc doi sang chat-first:
  - `Ops` va `Config` mo dang drawer;
  - `Ops` gom `Run inspector`, shell grant, parallel inspect, provider health, va tool contract;
  - khung chat da giu frame co dinh, da bo che do `Focus chat`;
  - tung drawer da co nut dong rieng.
- Active provider area gio co them readiness UX cho local/runtime path:
  - health strip hien reachability, selected model, va endpoint dang probe;
  - nut `Refresh runtime` re-probe ngay tai cho thay vi chi refresh model list;
  - local runtime hint text ro hon khi endpoint khong reachable.
- `desktop/index.html` hien dang load `runtime.js` truc tiep.
- `app.js` hien phu hop hon cho test/doc va de theo doi logic module, nhung khong phai live entrypoint cua shell dang render.
- `protocol.js` + `state.js` gio da duoc cap nhat de khop active-provider surface moi:
  - methods `settings.providers.active.get/catalog/update`
  - view-state `activeDrawer`, `activeProviderSettings`, `activeProviderDraft`, `activeProviderCatalog`, `activeProviderStatus`
  - regression test cho case apply active provider xong van giu config moi va catalog dung theo provider vua chon

## Packaged/non-dev path

Da confirm:

- `cargo tauri build --bundles nsis --ci --no-sign` pass.
- NSIS-installed executable la artifact dung de prove packaged path.
- Release binary truc tiep `target\release\yue-desktop.exe` van khong duoc xem la proof dung.

Chua verify lai sau dot startup/config moi:

- NSIS-installed app hien moi tra diagnostic `{"stage":"scheduled"}` trong lan re-check gan nhat, chua quay lai muc:
  - `readyState: "complete"`
  - `hasInvoke: true`
  - `hasIpc: true`
  - `bridgeLine: "bridge: spawned | core: started"`
  - `stage: "runtime_bootstrap"`
- cleanup proof packaged path chua duoc re-xac nhan lai sau dot nay.

## Dieu con can lam

- repeated launch / soak proof
- lifecycle hardening khi bridge loi hoac app dong bat thuong
- test/harness ro hon cho packaged interaction proof, thay vi chi diagnostic bootstrap
- tim nguyen nhan packaged diagnostic dung o `scheduled` trong lan re-check moi nhat
- giam drift giua `desktop/src/app.js` va `desktop/src/runtime.js`; runtime path hien dang di truoc
- noi approval/tool-result UX sat hon voi conversation stream thuc te
- neu tiep tuc UI:
  - uu tien run-level action co nghia hon nhu retry/export/replay;
  - tranh polish panel nho neu chua quay lai verify latest `Run inspector` changes

## Luu y verify

- Dot code moi nhat cho `Run inspector`:
  - group theo `run_id`
  - collapse/expand doc lap
  - `Open run` toi message log
  duoc merge sau lan verify desktop gan nhat theo yeu cau user tiep tuc code.
- Lan verify desktop gan nhat truoc dot UI moi nhat:
  - `node --check desktop/src/app.js`
  - `node --check desktop/src/runtime.js`
  - `node --check desktop/src/state.js`
  - `node --test desktop/tests/protocol.test.js`
- Re-check ngay 2026-07-07 cho active-provider protocol/state:
  - `node --check desktop/src/protocol.js`
  - `node --check desktop/src/state.js`
  - `node --test desktop/tests/protocol.test.js`

## Dung doc note nay khi nao

- Sua desktop shell runtime
- Sua Tauri bridge
- Sua packaged/non-dev startup path

Khong can doc note nay neu task chi cham:

- provider routing core
- tool/permission surface
- prompt profile / conversation logic thuan core
