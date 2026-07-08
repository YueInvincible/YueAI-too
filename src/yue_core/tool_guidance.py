from __future__ import annotations

from collections.abc import Sequence

from .contracts import ToolSpec

_CODING_AGENT_WORKFLOW = (
    "Start with read-only inspection. Read or search narrowly before editing.",
    "Use parallel reads only for independent inspection calls that are marked parallel-safe.",
    "Keep edits and shell actions sequential. Re-read affected files after non-trivial changes.",
    "Use approval before proposing or attempting risky actions outside the normal edit flow.",
    "Verify with the smallest command or diff that proves the change.",
)

_TOOL_RULES: dict[str, dict[str, object]] = {
    "workspace_list": {
        "summary": "List files or folders to map the local area before opening files.",
        "when_to_use": "Use first when you know the area but not exact filenames.",
        "avoid_when": "Do not use for content search inside files.",
    },
    "workspace_read": {
        "summary": "Read file content with optional line bounds.",
        "when_to_use": "Use for exact inspection after locating the target file.",
        "avoid_when": "Do not read huge files blindly; narrow by path or line range first.",
    },
    "workspace_search": {
        "summary": "Search workspace paths or simple content matches across the repo.",
        "when_to_use": "Use when you need likely file candidates quickly.",
        "avoid_when": "Do not use when regex-style matching is required; use workspace_grep.",
    },
    "workspace_grep": {
        "summary": "Run targeted regex-style search across workspace files.",
        "when_to_use": "Use to find symbols, patterns, or repeated code before editing.",
        "avoid_when": "Do not use when you already know the exact file and lines to read.",
    },
    "workspace_write": {
        "summary": "Create, append, or overwrite a workspace file intentionally.",
        "when_to_use": "Use for new files or full-file writes when exact replacement is clearer than patching blocks.",
        "avoid_when": "Do not use for small in-place changes; prefer workspace_edit.",
    },
    "workspace_edit": {
        "summary": "Replace an exact block in one workspace file.",
        "when_to_use": "Use for surgical edits with known search text.",
        "avoid_when": "Do not use until you have read the target file and confirmed the exact block.",
    },
    "workspace_ops": {
        "summary": "Copy, move, mkdir, or send files to trash inside the workspace.",
        "when_to_use": "Use for explicit file operations that support the planned change.",
        "avoid_when": "Do not use as a shortcut for editing file contents.",
    },
    "shell_run": {
        "summary": "Run a one-shot shell command with timeout and sanitized output.",
        "when_to_use": "Use for verification, build/test commands, or targeted repo inspection not covered by workspace tools.",
        "avoid_when": "Do not use before cheaper file reads/searches. Avoid destructive commands unless explicitly requested.",
    },
    "shell_session": {
        "summary": "Manage a long-lived shell process for background tasks.",
        "when_to_use": "Use only when the task needs a persistent server, watcher, or repeated reads from one process.",
        "avoid_when": "Do not use for one-off commands; prefer shell_run.",
    },
    "git_status": {
        "summary": "Inspect current working tree changes.",
        "when_to_use": "Use before and after edits to understand scope and verify touched files.",
        "avoid_when": "Do not use as a substitute for reading the actual diffs.",
    },
    "git_diff": {
        "summary": "Inspect diff output for validation.",
        "when_to_use": "Use after edits to confirm the exact patch and catch regressions.",
        "avoid_when": "Do not use before making changes unless you need current context from existing diffs.",
    },
    "todo_update": {
        "summary": "Maintain a short task checklist for the current session.",
        "when_to_use": "Use for multi-step work where progress tracking helps tool discipline.",
        "avoid_when": "Do not spam it for trivial single-step tasks.",
    },
    "ask_user_approval": {
        "summary": "Request explicit user approval for a risky or irreversible action.",
        "when_to_use": "Use before dangerous shell/process/file actions when approval is the right next step.",
        "avoid_when": "Do not use for normal reads, searches, or ordinary workspace edits already allowed by policy.",
    },
}


def build_tool_guide(
    specs: Sequence[ToolSpec],
    *,
    provider_role: str | None = None,
) -> dict[str, object]:
    tools: list[dict[str, object]] = []
    for spec in specs:
        rule = _TOOL_RULES.get(spec.name)
        if rule is None:
            continue
        tools.append(
            {
                "name": spec.name,
                "summary": rule["summary"],
                "when_to_use": rule["when_to_use"],
                "avoid_when": rule["avoid_when"],
                "output_kind": spec.output_kind.value,
                "parallel_safe": bool(spec.metadata.get("parallel_safe", False)),
                "mutates_state": bool(spec.metadata.get("mutates_state", False)),
                "risk": spec.risk.value,
            }
        )
    return {
        "provider_role": provider_role,
        "workflow": list(_CODING_AGENT_WORKFLOW),
        "tools": tools,
    }


def render_tool_guide_text(
    specs: Sequence[ToolSpec],
    *,
    provider_role: str | None = None,
) -> str:
    guide = build_tool_guide(specs, provider_role=provider_role)
    tools = guide["tools"]
    if not tools:
        return ""
    lines = ["Coding agent tool guide:"]
    for step in guide["workflow"]:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("Preferred tools:")
    for item in tools:
        lines.append(
            f"- {item['name']}: {item['summary']} Use when: {item['when_to_use']} Avoid when: {item['avoid_when']}"
        )
    return "\n".join(lines)
