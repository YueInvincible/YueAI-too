# Desktop Debug Pitfalls

## Mục đích

- Ghi lại các bài học quan trọng từ lỗi debug/build vừa rồi.
- Agent sau đọc note này trước khi kết luận "bridge không chạy" hay "build lỗi".

## 1. Launch app debug mà không chạy preview server là false negative

- `desktop/src-tauri/tauri.conf.json` đang dùng:
  - `build.devUrl = "http://127.0.0.1:1420"`
- Nếu chỉ:
  - `cargo build`
  - rồi chạy `yue-desktop.exe`
  thì WebView có thể chỉ đứng ở `readyState: loading`.
- Khi đó:
  - DOM chưa complete;
  - `#bridge-line` có thể chưa tồn tại;
  - frontend chưa bootstrap;
  - không có `python -m yue_core serve` child process.
- Kết luận "bridge không hoạt động" trong trạng thái đó là sai.

## 2. Muốn verify debug window thật thì phải chạy đúng cặp tiến trình

- Chạy:
  1. `node desktop/server.js`
  2. `desktop/src-tauri/target/debug/yue-desktop.exe`
- Khi làm đúng, app diagnostic đã báo:
  - `readyState: complete`
  - `hasInvoke: true`
  - `hasIpc: true`
  - `bridgeLine: "bridge: spawned | core: started"`

## 3. Plain HTML shell không tự có đúng invoke surface như code frontend mong đợi

- Chỉ bật `withGlobalTauri` là chưa đủ cho shell HTML hiện tại.
- Đã phải inject custom init script ở:
  - [desktop/src-tauri/src/main.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\src\main.rs)
- Script này dựng:
  - `window.__TAURI_INTERNALS__.invoke`
  - callback registry
  - `window.__TAURI__.core.invoke`
- Nếu ai sửa logic detect invoke ở frontend, phải nhớ ràng buộc này.

## 4. `tauri::test` cần feature riêng

- App-level Tauri IPC tests chỉ compile khi bật:
  - `tauri = { version = "2", features = ["test"] }`
- Nếu quên feature này, import `tauri::test` sẽ fail dù crate có module test nội bộ.

## 5. Shape response ở app-level IPC không giống frontend transport wrapper

- `bridge_request` qua Tauri IPC trả về `BridgeResponse` nguyên gốc:
  - `{"ok": true, "result": ...}`
- Frontend JS wrapper mới unwrap `result`.
- Khi viết Rust app-level invoke tests, đừng assert trực tiếp vào root payload như frontend transport.

## 6. Cách đo trực tiếp khi nghi app không bootstrap

- Dùng env:
  - `YUE_DESKTOP_DIAGNOSTIC=1`
- App sẽ in diagnostic từ WebView qua stdout.
- Chỉ số hữu ích:
  - `readyState`
  - `hasTauri`
  - `hasInternals`
  - `hasInvoke`
  - `hasIpc`
  - `bridgeLine`

## 7. Điều gì được coi là thành công tối thiểu cho debug window

- Preview server chạy.
- Window load xong DOM.
- `bridgeLine` báo `spawned | core: started`.
- Có descendant `"python" -m yue_core serve`.
- Tắt app xong không còn child core.
## 2026-06-26 packaged artifact note

- Do not use `desktop\src-tauri\target\release\yue-desktop.exe` as the final packaged-proof artifact.
- In this repo that executable can show misleading states such as:
  - remote debug URL `about:blank`;
  - diagnostics stuck around `page_load`.
- The reliable non-dev proof path is:
  - `cargo tauri build --bundles nsis --ci --no-sign`
  - silent-install the generated NSIS bundle
  - run the installed `yue-desktop.exe`
- Build-time inlining now matters:
  - [desktop/src-tauri/build.rs](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\build.rs) generates `desktop/dist/index.html`
  - the generated file inlines `src/styles.css` and `src/runtime.js`
  - [desktop/src-tauri/tauri.conf.json](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\desktop\src-tauri\tauri.conf.json) points `frontendDist` at `../dist`
