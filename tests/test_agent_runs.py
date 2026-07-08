import io
import json
import unittest

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings
from yue_core.contracts import (
    CoreEvent,
    MessageRole,
    ModelEvent,
    ModelEventType,
    ModelToolCall,
)
from yue_core.transport import JsonLineServer


class ToolCallingProvider:
    name = "test.tool_calling"

    async def generate(self, request, context):
        has_tool_result = any(message.role is MessageRole.TOOL for message in request.messages)
        if not has_tool_result:
            yield ModelEvent(
                ModelEventType.TOOL_CALL,
                tool_call=ModelToolCall(
                    name="core.echo",
                    arguments={"text": "tool-reference"},
                    id="tool-call-1",
                ),
            )
            yield ModelEvent(ModelEventType.FINISH, finish_reason="tool_calls")
            return
        yield ModelEvent(ModelEventType.TEXT_DELTA, text="Tool reference complete")
        yield ModelEvent(ModelEventType.FINISH, finish_reason="stop")

    async def health(self):
        return {"ok": True, "provider": self.name}


class AgentRunTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_run_completes_and_persists(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            result = await core.start_agent_run(
                "Inspect the workspace",
                run_id="agent-run-1",
                plan=["inspect", "answer"],
                metadata={"surface": "test"},
            )
            await core.stop()

            reloaded = YueCore(settings)
            run = await reloaded.agent_runs.get("agent-run-1")

        self.assertEqual(result["run"]["status"], "completed")
        self.assertEqual(result["run"]["provider_role"], "coding_agent")
        self.assertEqual(result["run"]["plan"], ["inspect", "answer"])
        self.assertEqual(result["run"]["persona_snapshot"]["id"], "coding_agent")
        self.assertEqual(result["run"]["provider_snapshot"]["provider"], "fake.echo")
        self.assertEqual(result["run"]["metadata"]["surface"], "test")
        self.assertEqual(result["message"]["content"], "Echo: Inspect the workspace")
        self.assertIsNotNone(run)
        self.assertEqual(run.status.value, "completed")
        self.assertEqual(run.response_message_id, result["message"]["id"])

    async def test_agent_run_transport_start_get_list(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                started = await server.handle_line(
                    json.dumps(
                        {
                            "id": "start",
                            "method": "agents.runs.start",
                            "params": {
                                "user_request": "Run a coding task",
                                "run_id": "transport-agent-run",
                                "plan": ["inspect"],
                                "metadata": {"surface": "desktop"},
                            },
                        }
                    )
                )
                fetched = await server.handle_line(
                    json.dumps(
                        {
                            "id": "get",
                            "method": "agents.runs.get",
                            "params": {"run_id": "transport-agent-run"},
                        }
                    )
                )
                listed = await server.handle_line(
                    json.dumps(
                        {
                            "id": "list",
                            "method": "agents.runs.list",
                            "params": {"limit": 10},
                        }
                    )
                )

        self.assertTrue(started["ok"])
        self.assertEqual(started["result"]["run"]["status"], "completed")
        self.assertEqual(started["result"]["run"]["metadata"]["surface"], "desktop")
        self.assertTrue(fetched["ok"])
        self.assertEqual(fetched["result"]["id"], "transport-agent-run")
        self.assertEqual(fetched["result"]["status"], "completed")
        self.assertTrue(listed["ok"])
        self.assertEqual(listed["result"][0]["id"], "transport-agent-run")

    async def test_agent_run_checklist_and_verification_updates_persist(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            server = JsonLineServer(core)
            async with core:
                started = await server.handle_line(
                    json.dumps(
                        {
                            "id": "start",
                            "method": "agents.runs.start",
                            "params": {
                                "user_request": "Run a verified task",
                                "run_id": "verified-agent-run",
                                "plan": ["inspect", "verify"],
                            },
                        }
                    )
                )
                checklist = await server.handle_line(
                    json.dumps(
                        {
                            "id": "checklist",
                            "method": "agents.runs.checklist.update",
                            "params": {
                                "run_id": "verified-agent-run",
                                "checklist": [
                                    {
                                        "id": "inspect",
                                        "text": "Inspect current files",
                                        "status": "completed",
                                        "note": "Read relevant files",
                                    },
                                    {
                                        "id": "verify",
                                        "text": "Run regression tests",
                                        "status": "in_progress",
                                    },
                                ],
                            },
                        }
                    )
                )
                verification = await server.handle_line(
                    json.dumps(
                        {
                            "id": "verification",
                            "method": "agents.runs.verification.update",
                            "params": {
                                "run_id": "verified-agent-run",
                                "status": "passed",
                                "summary": "Targeted tests passed",
                            },
                        }
                    )
                )
            reloaded = YueCore(settings)
            run = await reloaded.agent_runs.get("verified-agent-run")

        self.assertTrue(started["ok"])
        self.assertEqual(
            started["result"]["run"]["checklist"][0]["text"],
            "inspect",
        )
        self.assertTrue(checklist["ok"])
        self.assertEqual(checklist["result"]["checklist"][0]["status"], "completed")
        self.assertEqual(checklist["result"]["checklist"][1]["status"], "in_progress")
        self.assertTrue(verification["ok"])
        self.assertEqual(verification["result"]["verification"]["status"], "passed")
        self.assertEqual(
            verification["result"]["verification"]["summary"],
            "Targeted tests passed",
        )
        self.assertIsNotNone(run)
        self.assertEqual(run.checklist[0].id, "inspect")
        self.assertEqual(run.checklist[0].status.value, "completed")
        self.assertEqual(run.verification_status.value, "passed")

    async def test_transport_serve_forwards_agent_events(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            stdin = io.StringIO(
                json.dumps(
                    {
                        "id": "start",
                        "method": "agents.runs.start",
                        "params": {
                            "user_request": "hello",
                            "run_id": "event-agent-run",
                        },
                    }
                )
                + "\n"
            )
            stdout = io.StringIO()
            core = YueCore(settings)
            server = JsonLineServer(core, stdin=stdin, stdout=stdout)
            await server.serve()

        messages = [
            json.loads(line)
            for line in stdout.getvalue().splitlines()
            if line.strip()
        ]
        event_topics = [
            message["event"]["topic"]
            for message in messages
            if "event" in message
        ]
        self.assertIn("agent.run.created", event_topics)
        self.assertIn("agent.run.started", event_topics)
        self.assertIn("agent.run.completed", event_topics)
        self.assertTrue(any(message.get("id") == "start" for message in messages))

    async def test_agent_run_records_tool_references_from_events(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            core.providers.register(ToolCallingProvider(), owner="test")
            core.conversations.routes["coding_agent"] = {
                "provider": "test.tool_calling",
                "prompt_profile": "coding_agent",
            }
            result = await core.start_agent_run(
                "Use a tool",
                run_id="tool-reference-run",
            )
            run = await core.agent_runs.get("tool-reference-run")
            await core.stop()

        self.assertEqual(result["run"]["status"], "completed")
        self.assertIsNotNone(run)
        self.assertGreaterEqual(len(run.tool_references), 1)
        reference = run.tool_references[0]
        self.assertEqual(reference["tool"], "core.echo")
        self.assertEqual(reference["status"], "succeeded")
        self.assertEqual(
            reference["output"]["text"],
            "tool-reference",
        )

    async def test_agent_run_records_approval_references_from_events(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            await core.start()
            await core.start_agent_run(
                "Track approval",
                run_id="approval-reference-run",
            )
            await core.events.publish(
                CoreEvent(
                    "approval.pending",
                    {
                        "run_id": "approval-reference-run",
                        "approval_id": "approval-1",
                        "request_id": "request-1",
                        "tool_call_id": "tool-call-1",
                        "tool_name": "shell.run",
                        "reason": "Needs approval",
                        "risk_level": "high",
                    },
                )
            )
            await core.events.publish(
                CoreEvent(
                    "approval.responded",
                    {
                        "run_id": "approval-reference-run",
                        "approval_id": "approval-1",
                        "request_id": "request-1",
                        "tool_call_id": "tool-call-1",
                        "tool_name": "shell.run",
                        "approved": True,
                        "reason": "Needs approval",
                        "risk_level": "high",
                    },
                )
            )
            run = await core.agent_runs.get("approval-reference-run")
            await core.stop()

        self.assertIsNotNone(run)
        self.assertEqual(len(run.approval_references), 1)
        approval = run.approval_references[0]
        self.assertEqual(approval["stage"], "responded")
        self.assertEqual(approval["approval_id"], "approval-1")
        self.assertEqual(approval["tool"], "shell.run")
        self.assertTrue(approval["approved"])


if __name__ == "__main__":
    unittest.main()
