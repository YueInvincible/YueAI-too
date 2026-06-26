import unittest

from yue_core.contracts import (
    Capability,
    PermissionOutcome,
    RiskLevel,
    ToolRequest,
    ToolSpec,
)
from yue_core.permissions import PermissionEngine


class AllowApprovalProvider:
    async def request_approval(self, request, spec, reason):
        return True


class PermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_observe_allows_low_risk_read(self):
        engine = PermissionEngine("observe")
        decision = await engine.evaluate(
            ToolRequest("workspace.read", {}),
            ToolSpec("workspace.read", "", {}, Capability.FILE_READ, RiskLevel.LOW),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)

    async def test_observe_denies_write(self):
        engine = PermissionEngine("observe")
        decision = await engine.evaluate(
            ToolRequest("file.write", {}),
            ToolSpec("file.write", "", {}, Capability.FILE_WRITE, RiskLevel.MEDIUM),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_medium_risk_denied_without_approval_channel(self):
        engine = PermissionEngine("assist", interactive_approval=False)
        decision = await engine.evaluate(
            ToolRequest("shell.exec", {}),
            ToolSpec("shell.exec", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_assist_allows_edit_tools_without_interactive_approval(self):
        engine = PermissionEngine("assist", interactive_approval=False)
        decision = await engine.evaluate(
            ToolRequest("workspace.write", {}),
            ToolSpec("workspace.write", "", {}, Capability.FILE_WRITE, RiskLevel.MEDIUM),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)

    async def test_assist_denies_shell_run_for_model(self):
        engine = PermissionEngine("assist", interactive_approval=True)
        decision = await engine.evaluate(
            ToolRequest("shell.run", {}, actor="model"),
            ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_assist_denies_shell_session_for_model(self):
        engine = PermissionEngine("assist", interactive_approval=True)
        decision = await engine.evaluate(
            ToolRequest("shell.session", {}, actor="model"),
            ToolSpec("shell.session", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_assist_denies_dangerous_model_actions_even_with_approval_enabled(self):
        engine = PermissionEngine(
            "assist",
            interactive_approval=True,
            approval_provider=AllowApprovalProvider(),
        )
        decision = await engine.evaluate(
            ToolRequest("shell.exec", {}, actor="model"),
            ToolSpec("shell.exec", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_medium_risk_can_be_approved(self):
        engine = PermissionEngine(
            "assist",
            interactive_approval=True,
            approval_provider=AllowApprovalProvider(),
        )
        decision = await engine.evaluate(
            ToolRequest("shell.exec", {}, actor="ui"),
            ToolSpec("shell.exec", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)

    async def test_admin_allows_high_risk_without_interactive_approval(self):
        engine = PermissionEngine("admin", interactive_approval=False)
        decision = await engine.evaluate(
            ToolRequest("shell.exec", {}),
            ToolSpec("shell.exec", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)

    async def test_explicit_approval_uses_provider(self):
        engine = PermissionEngine(
            "assist",
            interactive_approval=True,
            approval_provider=AllowApprovalProvider(),
        )
        decision = await engine.request_explicit_approval(
            "Allow shell action",
            "high",
            actor="model",
            session_id="conversation-1",
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)


if __name__ == "__main__":
    unittest.main()
