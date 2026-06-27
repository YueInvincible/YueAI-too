# Yue Core

`Toi Yeu ClaudeCode :D`
Yue Core is the local-first orchestration layer for YueAI. The current scope is
limited to core stability: tool execution, provider contracts, plugin loading,
conversation flow, desktop-session IPC, and audit/logging.

Temporarily deferred systems:

- Voice: TTS, STT, voice cloning, streaming audio.
- Real 3D avatar rendering, VRM loading, and desktop window composition.
- Process monitoring / system observer.

The current milestone adds the core-side contract for the future avatar engine
without taking a renderer dependency yet.

The core uses only the Python standard library. Machine-learning providers
should run in isolated sidecars so CUDA, model, and Python-version
dependencies cannot destabilize the core process.

## Quick start

```powershell
$env:PYTHONPATH="src"
python -m yue_core doctor
python -m yue_core list-tools
python -m yue_core invoke core.echo --arguments '{"text":"hello"}'
python -m yue_core chat "hello"
python -m yue_core serve
```

If the active Windows shell alters embedded JSON quotes, use
`--arguments-file request.json`.

`serve` uses newline-delimited JSON over stdin/stdout. This transport is
intentionally simple for the first vertical slice and can later sit behind a
local named-pipe or WebSocket adapter without changing core contracts.

## Design principles

- Deny by default for capabilities with side effects.
- Tool calls are typed, validated, cancellable, timed out, and audited.
- Plugins are explicitly enabled and loaded from configured roots.
- Runtime startup is transactional: started components stop in reverse order
  when a later component fails.
- UI and providers communicate through events rather than importing each
  other.
- Public contracts live in `yue_core.contracts`; plugins must not import core
  internals.

See [docs/CORE_ARCHITECTURE.md](docs/CORE_ARCHITECTURE.md),
[docs/CONVERSATION_PROTOCOL.md](docs/CONVERSATION_PROTOCOL.md), and
[docs/DESKTOP_PROTOCOL.md](docs/DESKTOP_PROTOCOL.md). The local model adapter
is documented in [docs/LLAMA_CPP_PROVIDER.md](docs/LLAMA_CPP_PROVIDER.md).

Temporary desktop-shell validation:

```powershell
$env:PYTHONPATH="src;."
python -m yue_core desktop-demo --headless-smoke-test
```

The demo shell is documented in [docs/DESKTOP_DEMO.md](docs/DESKTOP_DEMO.md).

`python -m yue_core serve` now forwards both `conversation.*` and `desktop.*`
events over JSONL stdout.

Dedicated desktop app workspace:

```powershell
cd desktop
npm test
node server.js
rustfmt --check src-tauri\src\main.rs src-tauri\src\bridge.rs
cargo check --manifest-path src-tauri\Cargo.toml
cargo test --manifest-path src-tauri\Cargo.toml
```

The desktop shell now consumes native bridge runtime info and drained core
events when Tauri `invoke` is available, while preserving the mock preview path
in a plain browser.

The native shell now also has an app-level Tauri IPC test that exercises the
registered bridge commands through `tauri::test`, in addition to the lower-level
child-process bridge tests.

A real debug-window launch has also been validated against the configured
`devUrl` preview server: the window reaches `readyState: complete`, reports
`bridge: spawned | core: started`, spawns `python -m yue_core serve`, and
shuts down without leaving that core child alive.

The workspace scaffold and current validation boundary are documented in
[desktop/README.md](desktop/README.md).
