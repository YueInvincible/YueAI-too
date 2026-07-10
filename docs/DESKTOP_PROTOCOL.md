# Desktop session protocol

This document defines the first core-side IPC contract for the Yue Desktop
avatar-engine vertical slice.

The current scope is intentionally limited:

- desktop session attachment and detachment;
- shared desktop/avatar state snapshots;
- console open/close/toggle commands;
- avatar presence and expression state;
- event topics for the future renderer shell.

The current protocol does not create a window, load a VRM, or render frames.
Those responsibilities remain in the future desktop engine implementation.

## State model

The core exposes a single shared `DesktopState` with:

- `attached_session_ids`
- `console_open`
- `presence`
- `expression`
- `hotkey`
- `model_path`
- `window_anchor`
- `click_opens_console`

Presence values:

- `idle`
- `listening`
- `thinking`
- `speaking`
- `tool_working`
- `sleeping`

Expression values:

- `neutral`
- `happy`
- `sad`
- `angry`
- `surprised`

## JSONL methods

Requests:

```json
{"id":"1","method":"desktop.state"}
{"id":"2","method":"desktop.attach","params":{"session_id":"desktop-ui","metadata":{"surface":"tauri"}}}
{"id":"3","method":"desktop.command","params":{"command":"avatar.click","source":"tauri"}}
{"id":"4","method":"desktop.command","params":{"command":"presence.set","value":"thinking","source":"core"}}
{"id":"5","method":"desktop.detach","params":{"session_id":"desktop-ui"}}
```

Successful command responses return the updated state:

```json
{
  "id": "3",
  "ok": true,
  "result": {
    "state": {
      "console_open": true,
      "presence": "idle",
      "expression": "neutral"
    }
  }
}
```

## Event topics

The core publishes:

- `desktop.session.attached`
- `desktop.session.detached`
- `desktop.command.handled`
- `desktop.state.changed`

`desktop.state.changed` includes:

- `reason`
- `state`

This lets a renderer subscribe once and stay event-driven rather than polling.

When `python -m yue_core serve` is used, these desktop events are forwarded on
stdout the same way `conversation.*` events are forwarded.

## Agent run recovery

The JSONL surface exposes durable coding-agent runs to desktop clients:

```json
{"id":"run-1","method":"agents.runs.start","params":{"user_request":"Inspect and fix the project","provider_role":"coding_agent"}}
{"id":"run-2","method":"agents.runs.resume","params":{"run_id":"agent-run-id","actor":"desktop-ui"}}
```

After a process restart, stale active records become `interrupted`. Resume is
explicit and conservative: persisted input and tool results are reused, while
a tool call without a durable result blocks recovery instead of risking an
unknown side effect twice. Recovery emits `agent.run.interrupted`,
`agent.run.resumed`, `agent.run.resume.blocked`, or
`agent.run.resume.failed` as applicable.

## Command set

Supported commands:

- `avatar.click`
- `hotkey.toggle_console`
- `console.open`
- `console.close`
- `console.toggle`
- `presence.set`
- `expression.set`
- `avatar.sleep`
- `avatar.wake`

`presence.set` and `expression.set` require a `value`.

## Design constraints

- Renderer and core stay decoupled through JSONL/events.
- The core owns desktop state transitions so click/hotkey behavior remains
  consistent across UI implementations.
- The renderer should be replaceable without changing the conversation/tool
  contracts.
- This is not a security boundary; desktop clients are trusted first-party
  components.
