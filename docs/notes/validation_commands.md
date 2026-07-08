# Validation Commands

## Core Python

```powershell
$env:PYTHONPATH = "src;."
$env:PYTHONDONTWRITEBYTECODE = "1"
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Alternative:

```powershell
$env:PYTHONPATH = "src"
python -m pytest
```

Expected:

- 82 tests collected.
- neu bo qua `PYTHONPATH`, `unittest` se khong import duoc `yue_core`.

## Desktop JS

```powershell
cd desktop
npm test
```

Expected:

- 15 tests pass.

Targeted command da duoc dung gan day cho desktop shell/protocol:

```powershell
node --test desktop/tests/protocol.test.js
node --check desktop/src/app.js
node --check desktop/src/runtime.js
```

Expected:

- 15 tests pass.
- syntax check pass cho `app.js` va `runtime.js`.

Targeted Python subset da duoc dung gan day cho runtime/tool flow:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_transport.py tests/test_conversation.py tests/test_tools.py
```

Expected:

- 48 tests pass.

CLI export proof:

```powershell
$env:PYTHONPATH = "src"
python -m yue_core export-agent-starter-pack --provider-role coding_agent
python -m yue_core export-agent-starter-pack --provider-role coding_agent --format json
python -m yue_core export-agent-starter-pack --provider-role coding_agent --output .test-runtime\coding-agent-starter-pack.md
```

Expected:

- text mode in ra markdown starter pack co `Starter prompt` va `Codex-style tool manifest`;
- json mode in ra payload co `starter_prompt`, `system_prompt`, `codex_manifest`;
- `--output` ghi file UTF-8 dung voi noi dung starter pack.

## Native Rust

```powershell
cd desktop
rustfmt --check src-tauri\src\main.rs src-tauri\src\bridge.rs
cargo check --manifest-path src-tauri\Cargo.toml
cargo test --manifest-path src-tauri\Cargo.toml
```

Expected:

- formatting pass;
- `cargo check` pass;
- 4 Rust tests pass.

## Real debug-window proof

Only valid for current debug setup because `tauri.conf.json` uses `devUrl`.

```powershell
cd desktop
node server.js
```

In another process:

```powershell
$env:YUE_DESKTOP_DIAGNOSTIC = "1"
desktop\src-tauri\target\debug\yue-desktop.exe
```

Expected signals:

- preview server prints `http://127.0.0.1:1420`;
- app diagnostic includes:
  - `readyState: complete`
  - `hasInvoke: true`
  - `bridgeLine: "bridge: spawned | core: started"`
- process tree includes:
  - `"python" -m yue_core serve`
- stopping app leaves no core child process alive.
## Packaged non-dev proof

Use the packaged artifact, not `target\release\yue-desktop.exe`.

```powershell
cd desktop
cargo tauri build --bundles nsis --ci --no-sign
```

Install the generated NSIS bundle:

```powershell
$target = Join-Path (Get-Location) ".test-runtime\nsis-app"
if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
Start-Process -FilePath ".\src-tauri\target\release\bundle\nsis\Yue Desktop_0.1.0_x64-setup.exe" -ArgumentList "/S", "/D=$target" -Wait
```

Run the installed app with diagnostic output:

```powershell
$diag = Join-Path (Get-Location) ".test-runtime\nsis-diagnostic.json"
if (Test-Path -LiteralPath $diag) { Remove-Item -LiteralPath $diag -Force }
$env:YUE_DESKTOP_DIAGNOSTIC_PATH = $diag
$process = Start-Process -FilePath ".\.test-runtime\nsis-app\yue-desktop.exe" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 8
Get-Content -Raw $diag
if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $process.Id -Force }
```

Expected:

- diagnostic JSONL should contain a later line with:
  - `readyState: "complete"`
  - `hasInvoke: true`
  - `hasIpc: true`
  - `bridgeLine: "bridge: spawned | core: started"`
  - `stage: "runtime_bootstrap"`

Latest re-check on 2026-07-07:

- `cargo tauri build --bundles nsis --ci --no-sign` van pass.
- NSIS-installed app da ghi duoc JSONL startup timeline day du, ket thuc bang `runtime_bootstrap`.
- Ban ghi thanh cong co:
  - `readyState: "complete"`
  - `hasInvoke: true`
  - `hasIpc: true`
  - `bridgeLine: "bridge: spawned | core: started"`
- Nghia la packaged non-dev proof hien da duoc re-verify xanh.

Cleanup proof:

```powershell
$exe = ".\.test-runtime\nsis-app\yue-desktop.exe"
$process = Start-Process -FilePath $exe -PassThru
Start-Sleep -Seconds 5
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.ParentProcessId -eq $process.Id -and $_.CommandLine -match "yue_core .*serve" }
Stop-Process -Id $process.Id -Force
Start-Sleep -Seconds 2
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "yue_core .*serve" }
```

Latest re-check on 2026-07-07:

- Child process before shutdown:
  - `"python" -m yue_core --config C:\Users\Yue\Downloads\YueAI-main\YueAI-main\config.example.toml serve`
- After terminating `yue-desktop.exe`, khong con `python.exe` nao match `yue_core .*serve`.
- Khong bat `YUE_DESKTOP_DIAGNOSTIC_PATH` cho cleanup proof, vi diagnostic mode se tu dong `shutdownCore()` sau khi ghi `runtime_bootstrap`.
