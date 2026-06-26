# Desktop demo shell

This is a temporary validation shell for the Yue Desktop milestone.

It is intentionally not the final renderer architecture. It exists to prove:

- desktop-session lifecycle;
- console toggle behavior;
- corner-window placement;
- chat loop integration with Yue Core;
- clean startup and shutdown in a real desktop process.

Current implementation:

- Python standard library only;
- `tkinter` window shell;
- in-process Yue Core runtime;
- shared `DesktopDemoController` so the shell logic is testable without GUI.

This demo does not satisfy the final renderer goals:

- no Tauri shell;
- no Three.js scene;
- no VRM loading;
- no real transparent compositor;
- no global hotkey binding;
- no avatar animation beyond placeholder state text.

## Run

```powershell
$env:PYTHONPATH="src;."
python -m yue_core desktop-demo
```

Headless smoke test:

```powershell
$env:PYTHONPATH="src;."
python -m yue_core desktop-demo --headless-smoke-test
```

## Intended use

Use this as a stepping stone while building the actual desktop app workspace.
Do not treat it as the final avatar engine or final UI stack.
