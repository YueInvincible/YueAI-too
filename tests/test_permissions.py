import unittest

from yue_core.contracts import (
    Capability,
    PermissionDenialCategory,
    PermissionOutcome,
    RiskLevel,
    ToolRequest,
    ToolSpec,
)
from yue_core.permissions import PermissionEngine, PermissionGrantStore


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
            ToolRequest("shell_run", {}, actor="model"),
            ToolSpec("shell_run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
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

    async def test_observe_allows_ask_user_approval_alias(self):
        engine = PermissionEngine("observe")
        decision = await engine.evaluate(
            ToolRequest("ask_user_approval", {}),
            ToolSpec("ask_user_approval", "", {}, Capability.CORE_READ, RiskLevel.LOW),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)

    async def test_allow_all_cmd_grant_allows_model_shell_in_assist(self):
        grants = PermissionGrantStore()
        grants.set_allow_all_cmd("conversation-1", True, updated_by="ui")
        engine = PermissionEngine(
            "assist",
            interactive_approval=False,
            grant_store=grants,
        )
        decision = await engine.evaluate(
            ToolRequest("shell_run", {}, actor="model", session_id="conversation-1"),
            ToolSpec("shell_run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)

    async def test_allow_all_cmd_grant_does_not_bypass_observe_profile(self):
        grants = PermissionGrantStore()
        grants.set_allow_all_cmd("conversation-1", True, updated_by="ui")
        engine = PermissionEngine(
            "observe",
            interactive_approval=False,
            grant_store=grants,
        )
        decision = await engine.evaluate(
            ToolRequest("shell.run", {}, actor="model", session_id="conversation-1"),
            ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    def test_allow_all_cmd_grant_policy_denies_model_actor(self):
        engine = PermissionEngine("assist", interactive_approval=False)
        decision = engine.evaluate_allow_all_cmd_grant(actor="model", allowed=True)
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    def test_allow_all_cmd_grant_policy_denies_observe_profile(self):
        engine = PermissionEngine("observe", interactive_approval=False)
        decision = engine.evaluate_allow_all_cmd_grant(actor="desktop-ui", allowed=True)
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_capability_grant_allows_model_shell_for_matching_resource(self):
        grants = PermissionGrantStore()
        grants.set_capability_grant(
            "conversation-1",
            Capability.SHELL_EXECUTE,
            resource="C:/workspace",
            updated_by="ui",
        )
        engine = PermissionEngine(
            "assist",
            interactive_approval=False,
            grant_store=grants,
        )
        decision = await engine.evaluate(
            ToolRequest(
                "shell.run",
                {"cwd": "C:/workspace"},
                actor="model",
                session_id="conversation-1",
            ),
            ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.ALLOW)
        self.assertEqual(decision.rule_id, "session-capability-grant")

    async def test_capability_grant_does_not_bypass_observe_profile(self):
        grants = PermissionGrantStore()
        grants.set_capability_grant(
            "conversation-1",
            Capability.SHELL_EXECUTE,
            resource="*",
            updated_by="ui",
        )
        engine = PermissionEngine(
            "observe",
            interactive_approval=False,
            grant_store=grants,
        )
        decision = await engine.evaluate(
            ToolRequest("shell.run", {}, actor="model", session_id="conversation-1"),
            ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    def test_capability_grant_policy_denies_model_actor(self):
        engine = PermissionEngine("assist", interactive_approval=False)
        decision = engine.evaluate_capability_grant(
            actor="model",
            capability=Capability.SHELL_EXECUTE,
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    def test_capability_grant_policy_denies_capability_outside_profile(self):
        engine = PermissionEngine("assist", interactive_approval=False)
        decision = engine.evaluate_capability_grant(
            actor="desktop-ui",
            capability=Capability.PROCESS_CONTROL,
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_capability_grant_requires_matching_resource(self):
        grants = PermissionGrantStore()
        grants.set_capability_grant(
            "conversation-1",
            Capability.SHELL_EXECUTE,
            resource="C:/safe",
            updated_by="ui",
        )
        engine = PermissionEngine(
            "assist",
            interactive_approval=False,
            grant_store=grants,
        )
        decision = await engine.evaluate(
            ToolRequest(
                "shell.run",
                {"cwd": "C:/other"},
                actor="model",
                session_id="conversation-1",
            ),
            ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_once_capability_grant_is_consumed_after_allow(self):
        grants = PermissionGrantStore()
        grants.set_capability_grant(
            "conversation-1",
            Capability.SHELL_EXECUTE,
            resource="*",
            lifetime="once",
            updated_by="ui",
        )
        engine = PermissionEngine(
            "assist",
            interactive_approval=False,
            grant_store=grants,
        )
        request = ToolRequest("shell.run", {}, actor="model", session_id="conversation-1")
        spec = ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH)
        first = await engine.evaluate(request, spec)
        second = await engine.evaluate(request, spec)
        self.assertEqual(first.outcome, PermissionOutcome.ALLOW)
        self.assertEqual(second.outcome, PermissionOutcome.DENY)
        self.assertEqual(grants.get("conversation-1").capability_grants, ())

    async def test_run_lifetime_capability_grant_requires_matching_run(self):
        grants = PermissionGrantStore()
        grants.set_capability_grant(
            "conversation-1",
            Capability.SHELL_EXECUTE,
            resource="*",
            lifetime="run",
            scope_id="run-1",
            updated_by="ui",
        )
        engine = PermissionEngine(
            "assist",
            interactive_approval=False,
            grant_store=grants,
        )
        spec = ToolSpec("shell.run", "", {}, Capability.SHELL_EXECUTE, RiskLevel.HIGH)
        denied = await engine.evaluate(
            ToolRequest(
                "shell.run",
                {},
                actor="model",
                session_id="conversation-1",
                metadata={"run_id": "run-2"},
            ),
            spec,
        )
        allowed = await engine.evaluate(
            ToolRequest(
                "shell.run",
                {},
                actor="model",
                session_id="conversation-1",
                metadata={"run_id": "run-1"},
            ),
            spec,
        )
        self.assertEqual(denied.outcome, PermissionOutcome.DENY)
        self.assertEqual(denied.denial_category, PermissionDenialCategory.MISSING_SCOPE)
        self.assertEqual(denied.resource_scope["kind"], "shell.cwd")
        self.assertEqual(denied.resource_scope["value"], "*")
        self.assertEqual(allowed.outcome, PermissionOutcome.ALLOW)

    def test_revoke_capability_grant_removes_matching_scope(self):
        grants = PermissionGrantStore()
        grants.set_capability_grant(
            "conversation-1",
            Capability.SHELL_EXECUTE,
            resource="C:/safe",
            updated_by="ui",
        )
        updated = grants.revoke_capability_grant(
            "conversation-1",
            capability=Capability.SHELL_EXECUTE,
            resource="C:/safe",
        )
        self.assertEqual(updated.capability_grants, ())

    def test_run_lifetime_grant_policy_requires_scope_id(self):
        engine = PermissionEngine("assist", interactive_approval=False)
        decision = engine.evaluate_capability_grant(
            actor="desktop-ui",
            capability=Capability.SHELL_EXECUTE,
            lifetime="run",
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)

    async def test_profile_denial_has_policy_category_and_resource_scope(self):
        engine = PermissionEngine("observe")
        decision = await engine.evaluate(
            ToolRequest("file.write", {"path": "notes.txt"}),
            ToolSpec("file.write", "", {}, Capability.FILE_WRITE, RiskLevel.MEDIUM),
        )
        self.assertEqual(decision.outcome, PermissionOutcome.DENY)
        self.assertEqual(decision.denial_category, PermissionDenialCategory.POLICY)
        self.assertEqual(decision.resource_scope["kind"], "filesystem.path")
        self.assertEqual(decision.resource_scope["value"], "notes.txt")


if __name__ == "__main__":
    unittest.main()
