# Yue Desktop Workspace

This directory is the first dedicated workspace for the real desktop app.

Current scope:

- a protocol-aware frontend shell scaffold;
- an isolated `desktop/` workspace boundary;
- a mock transport preview that preserves the current core desktop semantics;
- a native bridge path that can consume real core events when Tauri `invoke` is available.

Validated now:

- protocol client requests;
- immutable desktop view-state helpers;
- mock transport preview flow;
- local preview server for the HTML shell.
- Tauri-aware transport selection in the frontend shell;
- Rust bridge command surface formatting via `rustfmt --check`.
- JSONL request/response/event router for a real core bridge;
- session-level client semantics for desktop attach/detach and event handling.
- Tauri command wrappers for runtime info, event draining, and shutdown.
- Frontend event pump polling semantics for forwarded native bridge events.
- Frontend shell wiring for:
  - `bridge_runtime_info`;
  - `bridge_drain_events`;
  - real `desktop.state.changed` application;
  - streamed `conversation.delta` rendering in native mode.
- Tauri app-level IPC lifecycle proof via `tauri::test`:
  - invokes `bridge_runtime_info`;
  - invokes `bridge_request` for desktop and conversation flows;
  - invokes `bridge_drain_events`;
  - invokes `bridge_shutdown_core`;
  - confirms runtime returns to `not_started` after shutdown.
- Real debug-window proof against the configured `devUrl`:
  - local preview server serves `http://127.0.0.1:1420`;
  - launched Tauri window reaches DOM `readyState: complete`;
  - bridge status line reports `bridge: spawned | core: started`;
  - the app spawns `python -m yue_core serve` as a live descendant;
  - stopping the app leaves no stray core child process behind.
- `cargo check --manifest-path src-tauri/Cargo.toml` passes for the native shell.
- Rust child-process bridge round-trip tests against `python -m yue_core serve` for:
  - desktop attach/state events;
  - conversation send/delta/completion events.
- Rust bridge sequential multi-request behavior on one live child process.

Not yet validated:

- `npm install` / real Tauri frontend dependency graph;
- longer-running soak or reconnect behavior of the Rust bridge;
- packaged non-dev frontend execution without the preview server;
- transparent window behavior on Windows in the real app shell;
- VRM loading and renderer integration.

## Local checks

```powershell
cd desktop
npm test
node server.js
rustfmt --check src-tauri\src\main.rs src-tauri\src\bridge.rs
cargo check --manifest-path src-tauri\Cargo.toml
cargo test --manifest-path src-tauri\Cargo.toml
```

Debug window proof currently depends on the local preview server because the
debug build uses `build.devUrl`.

## Design constraints

- Preserve `desktop.attach`, `desktop.detach`, and `desktop.command` semantics.
- Keep conversation transport assumptions compatible with the core JSONL protocol.
- Do not bypass the current core-side desktop state machine from the UI.

## Bridge layers

- `src/protocol.js`: method-level client for the current core protocol.
- `src/tauriTransport.js`: transport selection and Tauri `invoke` wrapper.
- `src/jsonlBridge.js`: JSONL request/response/event router.
- `src/bridgeClient.js`: transport built on newline-delimited JSON messages.
- `src/coreSession.js`: session-level desktop client on top of the JSONL bridge.
- `src/tauriTransport.js`: also contains native bridge command wrappers and
  a polling event pump for `bridge_drain_events`.

The Rust side now compiles and has runtime proof for both desktop and
conversation JSONL flows against a real child process, plus an app-level Tauri
IPC proof through `tauri::test`. The remaining gap is the real launched window
runtime beyond the current debug-window validation, not the bridge protocol
itself.
