# Desktop Bridge Status

## Mục tiêu note này

- Tóm tắt phần desktop bridge hiện đã làm tới đâu.
- Chỉ ra file quan trọng để agent sau mở đúng chỗ.

## File quan trọng

- Core protocol:
  - [src/yue_core/desktop.py](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\src\yue_core\desktop.py)
  - [src/yue_core/transport.py](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\src\yue_core\transport.py)
  - [src/yue_core/contracts.py](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\src\yue_core\contracts.py)
- Frontend shell:
  - [desktop/src/app.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\app.js)
  - [desktop/src/state.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\state.js)
  - [desktop/src/tauriTransport.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\tauriTransport.js)
- Native shell:
  - [desktop/src-tauri/src/main.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\main.rs)
  - [desktop/src-tauri/src/bridge.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\bridge.rs)
  - [desktop/src-tauri/tauri.conf.json](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\tauri.conf.json)

## Cái đã verify

- `yue_core serve` forward cả `conversation.*` và `desktop.*`.
- Rust bridge có thể:
  - spawn `python -m yue_core serve`;
  - gửi request thật;
  - nhận response thật;
  - nhận forwarded events;
  - shutdown sạch.
- Frontend shell có thể:
  - đọc `bridge_runtime_info`;
  - poll `bridge_drain_events`;
  - apply `desktop.state.changed`;
  - render `conversation.delta` trong native mode.
- Tauri app-level command surface đã được verify qua `tauri::test`.
- Debug Tauri window thật đã được verify với preview server.

## Điều kiện verify debug window hiện tại

- Debug build đang dùng `build.devUrl` trong `tauri.conf.json`.
- Muốn prove window thật thì phải chạy preview server trước.
- Khi đúng path:
  - DOM `readyState: complete`;
  - bridge line báo `bridge: spawned | core: started`;
  - có child process `"python" -m yue_core serve`;
  - stop app xong không còn child core.

## Gaps còn lại

- Non-dev frontend path chưa được prove.
- Manual interaction proof trong window thật chưa được ghi nhận thành test/harness.
- Repeated launch/soak chưa được prove.
- VRM/render integration chưa bắt đầu thật.
## 2026-06-26 non-dev path attempt

- Confirmed:
  - `npm test` still passes after native bootstrap changes.
  - `cargo test --manifest-path desktop\src-tauri\Cargo.toml` still passes after native diagnostic additions.
  - `cargo build --manifest-path desktop\src-tauri\Cargo.toml --release` succeeds.
  - Launching `desktop\src-tauri\target\release\yue-desktop.exe` without any preview server reaches Tauri `page_load`.
- Not yet confirmed:
  - The bundled non-dev page has not produced a frontend diagnostic payload.
  - The release run did not prove usable `window.__TAURI__.core.invoke` inside the loaded page.
  - The release run did not prove `app.js` bootstrap reached native bridge attach.
- Current evidence:
  - `main.rs` diagnostic stage file advances to `page_load`.
  - The same file does not advance to the JS/native diagnostic payload.
  - A fire-and-forget `on_page_load` probe that tries `window.__TAURI__.core.invoke("bridge_report_diagnostic", ...)` also did not overwrite the stage file.
- Most relevant files to open next:
  - [desktop/src-tauri/src/main.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\main.rs)
  - [desktop/src/app.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\app.js)
  - [desktop/src/tauriTransport.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\tauriTransport.js)
  - [desktop/index.html](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\index.html)
  - [desktop/src-tauri/tauri.conf.json](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\tauri.conf.json)
- Best current suspicion:
  - The packaged page loads, but the native invoke surface is still not usable in the non-dev release page, or the frontend module still does not reach the native-bridge path after page load.
- Re-run commands:
  - `npm test`
  - `cargo test --manifest-path desktop\src-tauri\Cargo.toml`
  - `cargo build --manifest-path desktop\src-tauri\Cargo.toml --release`
  - `$diag = Join-Path (Get-Location) '.test-runtime\release-diagnostic.json'; if (Test-Path -LiteralPath $diag) { Remove-Item -LiteralPath $diag -Force }; $env:YUE_DESKTOP_DIAGNOSTIC_PATH = $diag; $process = Start-Process -FilePath '.\desktop\src-tauri\target\release\yue-desktop.exe' -PassThru; Start-Sleep -Seconds 8; if (Test-Path -LiteralPath $diag) { Get-Content -Raw $diag }; if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $process.Id -Force }`
## 2026-06-26 packaged proof update

- This supersedes the earlier failed attempt that used `desktop\src-tauri\target\release\yue-desktop.exe` as the proof artifact.
- Confirmed now:
  - `npm test` passes.
  - `cargo test --manifest-path desktop\src-tauri\Cargo.toml` passes.
  - `cargo tauri build --bundles nsis --ci --no-sign` passes.
  - Silent-installing `desktop\src-tauri\target\release\bundle\nsis\Yue Desktop_0.1.0_x64-setup.exe` to `.test-runtime\nsis-app` produces a working packaged `yue-desktop.exe`.
  - Running that packaged executable without any preview server writes diagnostic JSON with:
    - `readyState: "complete"`
    - `hasTauri: true`
    - `hasInternals: true`
    - `hasInvoke: true`
    - `hasIpc: true`
    - `bridgeLine: "bridge: spawned | core: started"`
    - `stage: "runtime_bootstrap"`
  - Cleanup was verified:
    - while the packaged app is alive, one child `"python" -m yue_core serve` exists;
    - after the app stops, no such child remains.
- Important:
  - `desktop\src-tauri\target\release\yue-desktop.exe` is not the right artifact for packaged-path proof in this repo.
  - The correct artifact is the NSIS-installed executable produced by `cargo tauri build`.
- Supporting code added for packaged path:
  - [desktop/src/runtime.js](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src\runtime.js)
  - [desktop/index.html](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\index.html)
  - [desktop/src-tauri/build.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\build.rs)
  - [desktop/src-tauri/tauri.conf.json](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\tauri.conf.json)
  - [desktop/src-tauri/src/main.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\main.rs)
  - [desktop/src-tauri/src/bridge.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\bridge.rs)
- Practical result:
  - non-dev frontend path is now proved.
  - next desktop priority should move to lifecycle hardening / repeated launch / soak proof.
