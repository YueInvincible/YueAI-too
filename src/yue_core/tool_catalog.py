from __future__ import annotations

from collections.abc import Sequence

from .contracts import ToolSpec

CODING_AGENT_TOOL_NAMES = frozenset(
    {
        "workspace_list",
        "workspace_read",
        "workspace_search",
        "workspace_grep",
        "workspace_write",
        "workspace_edit",
        "workspace_ops",
        "shell_run",
        "shell_session",
        "git_status",
        "git_diff",
        "todo_update",
        "ask_user_approval",
    }
)


def filter_tool_specs_for_role(
    specs: Sequence[ToolSpec],
    provider_role: str | None,
) -> list[ToolSpec]:
    if provider_role != "coding_agent":
        return list(specs)
    return [
        spec
        for spec in specs
        if spec.plugin_id != "core" or spec.name in CODING_AGENT_TOOL_NAMES
    ]
