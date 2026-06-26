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
