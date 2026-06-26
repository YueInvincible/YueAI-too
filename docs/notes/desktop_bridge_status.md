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
- Rust bridge co the:
  - spawn `python -m yue_core serve`
  - gui request/nhan response that
  - nhan forwarded events
  - shutdown sach
- Frontend shell co the:
  - doc `bridge_runtime_info`
  - poll `bridge_drain_events`
  - apply `desktop.state.changed`
  - render `conversation.delta` trong native mode
- Provider health va runtime settings editor da render trong shell.
- Provider config editor da co cho:
  - `openai.compat`
  - `anthropic.messages`
- `openai.compat` va `anthropic.messages` editor da co:
  - add/remove provider rows
  - quick presets
  - custom header editor

## Packaged/non-dev path

Da confirm:

- `cargo tauri build --bundles nsis --ci --no-sign` pass.
- NSIS-installed executable la artifact dung de prove packaged path.
- Chay artifact da install khong can preview server van co diagnostic:
  - `readyState: "complete"`
  - `hasInvoke: true`
  - `hasIpc: true`
  - `bridgeLine: "bridge: spawned | core: started"`
  - `stage: "runtime_bootstrap"`
- Cleanup da verify:
  - khi app dang song, co child `"python" -m yue_core serve`
  - khi app dung, child core bien mat

## Dieu con can lam

- repeated launch / soak proof
- lifecycle hardening khi bridge loi hoac app dong bat thuong
- test/harness ro hon cho packaged interaction proof, thay vi chi diagnostic bootstrap

## Dung doc note nay khi nao

- Sua desktop shell runtime
- Sua Tauri bridge
- Sua packaged/non-dev startup path

Khong can doc note nay neu task chi cham:

- provider routing core
- tool/permission surface
- prompt profile / conversation logic thuan core
