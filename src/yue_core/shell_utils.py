from __future__ import annotations

import os
import shutil


def build_shell_argv(command: str) -> list[str]:
    if os.name == "nt":
        executable = (
            shutil.which("powershell.exe")
            or shutil.which("pwsh.exe")
            or "powershell.exe"
        )
        return [
            executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]

    bash = shutil.which("bash")
    if bash:
        return [bash, "--noprofile", "--norc", "-lc", command]
    return ["/bin/sh", "-c", command]
