from __future__ import annotations

import json
from collections.abc import Sequence

from .contracts import ToolSpec

TOOL_GUIDE_FORMATS: tuple[str, ...] = ("text", "json")

_CODING_AGENT_WORKFLOW = (
    "Start with read-only inspection. Read or search narrowly before editing.",
    "Use parallel reads only for independent inspection calls that are marked parallel-safe.",
    "Keep edits and shell actions sequential. Re-read affected files after non-trivial changes.",
    "Use approval before proposing or attempting risky actions outside the normal edit flow.",
    "Verify with the smallest command or diff that proves the change.",
)

_EXECUTION_RULES = {
    "inspect_before_edit": "Read or search the narrowest useful context before any file mutation.",
    "parallel_read_policy": "Parallel tool batches are only for independent read-only calls explicitly marked parallel-safe.",
    "mutation_policy": "Workspace edits, file ops, shell commands, and other state changes stay sequential.",
    "approval_policy": "Ask the user before destructive, irreversible, or high-blast-radius actions outside the normal edit flow.",
    "verification_policy": "End with the smallest real diff, test, or command that proves the requested outcome.",
}

_DECISION_RULES = (
    {
        "name": "inspect_first",
        "rule": "Inspect current code and docs before planning edits.",
        "why": "Reduces avoidable assumptions and keeps patches aligned with the local codebase.",
    },
    {
        "name": "prefer_narrow_reads",
        "rule": "Prefer focused reads, grep, and path search over broad file dumps.",
        "why": "Keeps context precise and avoids wasting tool budget on low-signal output.",
    },
    {
        "name": "sequential_mutations",
        "rule": "Do not overlap writes, shell actions, or file operations.",
        "why": "Makes failures easier to attribute and avoids compounding state changes.",
    },
    {
        "name": "approval_for_blast_radius",
        "rule": "Escalate to user approval when intent is unclear or the action could be destructive.",
        "why": "Preserves safety boundaries even when the runtime policy would technically allow the call.",
    },
    {
        "name": "prove_the_change",
        "rule": "Validate with the smallest command, diff, or targeted re-read that proves the result.",
        "why": "Keeps verification grounded in real evidence instead of assertion.",
    },
)

_RECIPES = (
    {
        "name": "inspect-and-patch",
        "goal": "Change existing code in a known area with minimal risk.",
        "tool_sequence": ["workspace_search", "workspace_read", "workspace_edit", "git_diff"],
        "steps": [
            "Locate the likely file or symbol with workspace_search or workspace_grep.",
            "Read the exact block you intend to change with workspace_read.",
            "Apply the smallest in-place mutation with workspace_edit.",
            "Review the resulting patch with git_diff before concluding.",
        ],
    },
    {
        "name": "parallel-inspection",
        "goal": "Compare multiple files or modules before deciding on one edit path.",
        "tool_sequence": ["workspace_read", "workspace_read", "workspace_grep"],
        "steps": [
            "Batch only read-only calls that are independent and marked parallel-safe.",
            "Compare the returned snippets or grep matches to decide where the real change belongs.",
            "Switch back to sequential execution before any write, shell, or file operation.",
        ],
    },
    {
        "name": "verify-with-real-proof",
        "goal": "Confirm the requested behavior changed and no obvious regression was introduced.",
        "tool_sequence": ["workspace_read", "shell_run", "git_diff"],
        "steps": [
            "Re-read the edited region if the change is subtle or generated through a broad replacement.",
            "Run the narrowest relevant verification command with shell_run when a real check exists.",
            "Use git_diff to confirm the final patch matches the intended scope.",
        ],
    },
    {
        "name": "approval-before-risk",
        "goal": "Handle destructive or ambiguous actions without silently widening scope.",
        "tool_sequence": ["workspace_read", "ask_user_approval", "workspace_ops"],
        "steps": [
            "Inspect enough context to explain the action and its blast radius clearly.",
            "Request approval before destructive file ops, risky shell commands, or unclear intent changes.",
            "Proceed only after approval, then verify the resulting state.",
        ],
    },
)

_TOOL_RULES: dict[str, dict[str, object]] = {
    "workspace_list": {
        "summary": "List files or folders to map the local area before opening files.",
        "when_to_use": "Use first when you know the area but not exact filenames.",
        "avoid_when": "Do not use for content search inside files.",
        "follow_up": "After listing candidates, switch to workspace_read or workspace_search for exact context.",
        "preferred_inputs": ["path"],
        "examples": (
            {"intent": "List a subtree before opening files", "arguments": {"path": "src"}},
        ),
    },
    "workspace_read": {
        "summary": "Read file content with optional line bounds.",
        "when_to_use": "Use for exact inspection after locating the target file.",
        "avoid_when": "Do not read huge files blindly; narrow by path or line range first.",
        "follow_up": "Use workspace_edit or git_diff only after confirming the exact block to change.",
        "preferred_inputs": ["path", "start_line", "end_line"],
        "examples": (
            {
                "intent": "Read a narrow region around a likely edit",
                "arguments": {"path": "src/yue_core/tool_guidance.py", "start_line": 1, "end_line": 80},
            },
        ),
    },
    "workspace_search": {
        "summary": "Search workspace paths or simple content matches across the repo.",
        "when_to_use": "Use when you need likely file candidates quickly.",
        "avoid_when": "Do not use when regex-style matching is required; use workspace_grep.",
        "follow_up": "Open the most relevant hits with workspace_read instead of guessing.",
        "preferred_inputs": ["query", "path"],
        "examples": (
            {"intent": "Find likely files by feature name", "arguments": {"query": "starter_pack", "path": "src"}},
        ),
    },
    "workspace_grep": {
        "summary": "Run targeted regex-style search across workspace files.",
        "when_to_use": "Use to find symbols, patterns, or repeated code before editing.",
        "avoid_when": "Do not use when you already know the exact file and lines to read.",
        "follow_up": "Use the grep hits to drive narrow workspace_read calls.",
        "preferred_inputs": ["pattern", "path"],
        "examples": (
            {"intent": "Find all runtime consumers of a method", "arguments": {"pattern": "tools\\.guide", "path": "src"}},
        ),
    },
    "workspace_write": {
        "summary": "Create, append, or overwrite a workspace file intentionally.",
        "when_to_use": "Use for new files or full-file writes when exact replacement is clearer than patching blocks.",
        "avoid_when": "Do not use for small in-place changes; prefer workspace_edit.",
        "follow_up": "Re-read the written file or inspect git_diff if the write replaced meaningful content.",
        "preferred_inputs": ["path", "content"],
        "examples": (
            {"intent": "Write a new guidance doc", "arguments": {"path": "docs/tool_guide.md", "content": "# Tool guide"}},
        ),
    },
    "workspace_edit": {
        "summary": "Replace an exact block in one workspace file.",
        "when_to_use": "Use for surgical edits with known search text.",
        "avoid_when": "Do not use until you have read the target file and confirmed the exact block.",
        "follow_up": "Re-read the edited region or inspect git_diff before continuing.",
        "preferred_inputs": ["path", "old_text", "new_text"],
        "examples": (
            {
                "intent": "Swap one exact string block after inspection",
                "arguments": {"path": "src/yue_core/cli.py", "old_text": "old", "new_text": "new"},
            },
        ),
    },
    "workspace_ops": {
        "summary": "Copy, move, mkdir, or send files to trash inside the workspace.",
        "when_to_use": "Use for explicit file operations that support the planned change.",
        "avoid_when": "Do not use as a shortcut for editing file contents.",
        "follow_up": "Confirm the destination state with workspace_list or workspace_read after the operation.",
        "preferred_inputs": ["op", "src", "dst"],
        "examples": (
            {"intent": "Create a docs directory before writing a file", "arguments": {"op": "mkdir", "path": "docs/notes"}},
        ),
    },
    "shell_run": {
        "summary": "Run a one-shot shell command with timeout and sanitized output.",
        "when_to_use": "Use for verification, build/test commands, or targeted repo inspection not covered by workspace tools.",
        "avoid_when": "Do not use before cheaper file reads/searches. Avoid destructive commands unless explicitly requested.",
        "follow_up": "Capture only the smallest command that proves the change, then summarize its real result.",
        "preferred_inputs": ["command", "cwd", "timeout_seconds"],
        "examples": (
            {"intent": "Run targeted transport tests", "arguments": {"command": "python -m pytest tests/test_transport.py"}},
        ),
    },
    "shell_session": {
        "summary": "Manage a long-lived shell process for background tasks.",
        "when_to_use": "Use only when the task needs a persistent server, watcher, or repeated reads from one process.",
        "avoid_when": "Do not use for one-off commands; prefer shell_run.",
        "follow_up": "Stop the session when the persistent task is no longer needed.",
        "preferred_inputs": ["command", "cwd"],
        "examples": (
            {"intent": "Start a local preview server you need to poll repeatedly", "arguments": {"command": "npm run dev"}},
        ),
    },
    "git_status": {
        "summary": "Inspect current working tree changes.",
        "when_to_use": "Use before and after edits to understand scope and verify touched files.",
        "avoid_when": "Do not use as a substitute for reading the actual diffs.",
        "follow_up": "Use git_diff after status confirms the relevant files changed.",
        "preferred_inputs": [],
        "examples": (
            {"intent": "Check whether only expected files changed", "arguments": {}},
        ),
    },
    "git_diff": {
        "summary": "Inspect diff output for validation.",
        "when_to_use": "Use after edits to confirm the exact patch and catch regressions.",
        "avoid_when": "Do not use before making changes unless you need current context from existing diffs.",
        "follow_up": "If the diff is broader than expected, re-open the touched file before continuing.",
        "preferred_inputs": ["path"],
        "examples": (
            {"intent": "Review the patch for one touched module", "arguments": {"path": "src/yue_core/app.py"}},
        ),
    },
    "todo_update": {
        "summary": "Maintain a short task checklist for the current session.",
        "when_to_use": "Use for multi-step work where progress tracking helps tool discipline.",
        "avoid_when": "Do not spam it for trivial single-step tasks.",
        "follow_up": "Mark only meaningful transitions so the checklist stays readable.",
        "preferred_inputs": ["items"],
        "examples": (
            {"intent": "Track a three-step implementation", "arguments": {"items": ["inspect", "edit", "verify"]}},
        ),
    },
    "ask_user_approval": {
        "summary": "Request explicit user approval for a risky or irreversible action.",
        "when_to_use": "Use before dangerous shell/process/file actions when approval is the right next step.",
        "avoid_when": "Do not use for normal reads, searches, or ordinary workspace edits already allowed by policy.",
        "follow_up": "Once approved, keep the action scoped to what was described in the request.",
        "preferred_inputs": ["reason", "risk_level"],
        "examples": (
            {"intent": "Ask before deleting generated artifacts", "arguments": {"reason": "Delete stale build outputs", "risk_level": "high"}},
        ),
    },
}


def _render_tool_guide_text_from_payload(guide: dict[str, object]) -> str:
    tools = guide.get("tools", [])
    if not tools:
        return ""
    lines = ["Coding agent tool guide:"]
    for step in guide.get("workflow", []):
        lines.append(f"- {step}")
    execution_rules = guide.get("execution_rules")
    if isinstance(execution_rules, dict) and execution_rules:
        lines.append("")
        lines.append("Execution rules:")
        for value in execution_rules.values():
            lines.append(f"- {value}")
    recipes = guide.get("recipes")
    if isinstance(recipes, list) and recipes:
        lines.append("")
        lines.append("Common recipes:")
        for recipe in recipes:
            if not isinstance(recipe, dict):
                continue
            name = recipe.get("name", "recipe")
            goal = recipe.get("goal", "")
            tool_sequence = ", ".join(recipe.get("tool_sequence", []))
            lines.append(f"- {name}: {goal} Tools: {tool_sequence}")
    lines.append("")
    lines.append("Preferred tools:")
    for item in tools:
        if not isinstance(item, dict):
            continue
        follow_up = item.get("follow_up")
        lines.append(
            f"- {item['name']}: {item['summary']} Use when: {item['when_to_use']} Avoid when: {item['avoid_when']}"
            + (f" Follow up: {follow_up}" if follow_up else "")
        )
    return "\n".join(lines)


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
                "follow_up": rule["follow_up"],
                "preferred_inputs": list(rule["preferred_inputs"]),
                "examples": [dict(item) for item in rule["examples"]],
            }
        )
    guide = {
        "provider_role": provider_role,
        "workflow": list(_CODING_AGENT_WORKFLOW),
        "execution_rules": dict(_EXECUTION_RULES),
        "decision_rules": [dict(item) for item in _DECISION_RULES],
        "recipes": [dict(item) for item in _RECIPES],
        "tools": tools,
    }
    guide["text"] = _render_tool_guide_text_from_payload(guide)
    return guide


def render_tool_guide_output(payload: dict[str, object], format_name: str) -> str:
    if format_name == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if format_name == "text":
        return str(payload.get("text", ""))
    raise ValueError(f"Unsupported tool guide format: {format_name}")


def render_tool_guide_text(
    specs: Sequence[ToolSpec],
    *,
    provider_role: str | None = None,
) -> str:
    guide = build_tool_guide(specs, provider_role=provider_role)
    return str(guide.get("text", ""))
