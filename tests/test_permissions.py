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
            ToolRequest("file.read", {}),
            ToolSpec("file.read", "", {}, Capability.FILE_READ, RiskLevel.LOW),
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
            ToolRequest("file.write", {}),
            ToolSpec("file.write", "", {}, Capability.FILE_WRITE, RiskLevel.MEDIUM),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_medium_risk_can_be_approved(self):
        engine = PermissionEngine(
            "assist",
            interactive_approval=True,
            approval_provider=AllowApprovalProvider(),
        )
        decision = await engine.evaluate(
            ToolRequest("file.write", {}),
            ToolSpec("file.write", "", {}, Capability.FILE_WRITE, RiskLevel.MEDIUM),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)


if __name__ == "__main__":
    unittest.main()
