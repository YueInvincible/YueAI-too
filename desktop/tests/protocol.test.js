import test from "node:test";
import assert from "node:assert/strict";

import { CoreProtocolClient, createMessage } from "../src/protocol.js";
import {
  appendMessage,
  applyBridgeRuntime,
  applyCoreEvent,
  applyDesktopSnapshot,
  defaultDesktopViewState,
  setConversationId,
} from "../src/state.js";
import { createMockTransport } from "../src/mock.js";
import {
  TauriEventPump,
  createTauriBridgeCommands,
  createPreferredTransport,
  createTauriTransport,
  detectTauriInvoke,
} from "../src/tauriTransport.js";
import {
  JsonlMessageRouter,
  createRequestEnvelope,
  parseJsonlMessage,
} from "../src/jsonlBridge.js";
import { JsonlBridgeTransport } from "../src/bridgeClient.js";
import { CoreSessionClient } from "../src/coreSession.js";

test("protocol client dispatches desktop methods through transport", async () => {
  const calls = [];
  const client = new CoreProtocolClient({
    async request(payload) {
      calls.push(payload);
      return { ok: true };
    },
  });

  await client.desktopAttach("desktop-ui", { surface: "test" });
  await client.desktopCommand("console.toggle", undefined, "desktop-ui");
  await client.desktopDetach("desktop-ui");

  assert.deepEqual(
    calls.map((item) => item.method),
    ["desktop.attach", "desktop.command", "desktop.detach"],
  );
  assert.equal(calls[1].params.command, "console.toggle");
});

test("mock transport supports the current desktop shell flow", async () => {
  const client = new CoreProtocolClient(createMockTransport());
  const initial = await client.desktopState();
  assert.equal(initial.console_open, false);

  const attached = await client.desktopAttach("desktop-ui");
  assert.deepEqual(attached.state.attached_session_ids, ["desktop-ui"]);

  const toggled = await client.desktopCommand("avatar.click");
  assert.equal(toggled.state.console_open, true);

  const conversation = await client.createConversation();
  const reply = await client.sendConversationMessage(conversation.id, "hello");
  assert.equal(reply.message.text, "Echo: hello");
});

test("desktop view-state helpers preserve immutable updates", () => {
  const initial = defaultDesktopViewState();
  const snapped = applyDesktopSnapshot(initial, {
    attached_session_ids: ["desktop-ui"],
    console_open: true,
    presence: "thinking",
    expression: "happy",
    hotkey: "Ctrl+Shift+Y",
    model_path: null,
    window_anchor: "bottom-right",
  });
  const withConversation = setConversationId(snapped, "conversation-1");
  const withMessages = appendMessage(withConversation, createMessage("assistant", "hello"));

  assert.equal(initial.consoleOpen, false);
  assert.equal(snapped.consoleOpen, true);
  assert.equal(withConversation.conversationId, "conversation-1");
  assert.equal(withMessages.messages.length, 1);
});

test("bridge runtime and event helpers apply native state transitions", () => {
  const initial = defaultDesktopViewState();
  const withRuntime = applyBridgeRuntime(initial, {
    mode: "stdio-jsonl",
    core_transport: "spawned",
    process_started: true,
    pending_requests: 2,
    queued_events: 1,
    note: "native bridge active",
    last_error: null,
  });
  const withDesktopEvent = applyCoreEvent(withRuntime, {
    topic: "desktop.state.changed",
    payload: {
      state: {
        attached_session_ids: ["desktop-ui"],
        console_open: true,
        presence: "thinking",
        expression: "happy",
        hotkey: "Ctrl+Shift+Y",
        model_path: null,
        window_anchor: "bottom-right",
      },
    },
  });
  const withDelta = applyCoreEvent(withDesktopEvent, {
    topic: "conversation.delta",
    payload: { text: "Echo: " },
  });
  const completed = applyCoreEvent(withDelta, {
    topic: "conversation.run.completed",
    payload: { message: { content: "Echo: hello" } },
  });

  assert.equal(withRuntime.bridgeTransport, "spawned");
  assert.equal(withRuntime.bridgeProcessStarted, true);
  assert.equal(withDesktopEvent.consoleOpen, true);
  assert.equal(withDesktopEvent.presence, "thinking");
  assert.equal(completed.messages.at(-1).text, "Echo: hello");
  assert.equal(completed.activeAssistantMessageId, null);
});

test("tauri transport maps bridge responses into protocol results", async () => {
  const calls = [];
  const transport = createTauriTransport({
    async invoke(command, payload) {
      calls.push({ command, payload });
      return {
        ok: true,
        result: { attached_session_ids: [], console_open: false },
      };
    },
  });

  const result = await transport.request({
    method: "desktop.state",
    params: {},
    timeoutMs: 1234,
  });

  assert.equal(calls[0].command, "bridge_request");
  assert.equal(calls[0].payload.payload.method, "desktop.state");
  assert.equal(calls[0].payload.payload.timeout_ms, 1234);
  assert.equal(result.console_open, false);
});

test("preferred transport chooses tauri invoke when available", async () => {
  const transport = createPreferredTransport(
    {
      __TAURI__: {
        core: {
          async invoke() {
            return { ok: true, result: { value: "tauri" } };
          },
        },
      },
    },
    createMockTransport(),
  );

  const result = await transport.request({ method: "probe", params: {} });
  assert.equal(result.value, "tauri");
});

test("detectTauriInvoke returns null when tauri globals are absent", () => {
  assert.equal(detectTauriInvoke({}), null);
});

test("tauri bridge commands call dedicated native commands", async () => {
  const calls = [];
  const commands = createTauriBridgeCommands({
    async invoke(name) {
      calls.push(name);
      if (name === "bridge_drain_events") {
        return { events: [{ topic: "desktop.state.changed" }] };
      }
      return { ok: true };
    },
  });

  const info = await commands.runtimeInfo();
  const events = await commands.drainEvents();
  const shutdown = await commands.shutdownCore();

  assert.deepEqual(calls, [
    "bridge_runtime_info",
    "bridge_drain_events",
    "bridge_shutdown_core",
  ]);
  assert.equal(info.ok, true);
  assert.equal(events[0].topic, "desktop.state.changed");
  assert.equal(shutdown.ok, true);
});

test("jsonl parser strips UTF-8 BOM and ignores blank lines", () => {
  assert.equal(parseJsonlMessage("   "), null);
  assert.deepEqual(
    parseJsonlMessage('\uFEFF{"id":"1","ok":true,"result":{"value":1}}'),
    { id: "1", ok: true, result: { value: 1 } },
  );
});

test("jsonl router resolves responses and forwards events", async () => {
  const router = new JsonlMessageRouter();
  const seenEvents = [];
  router.onEvent((event) => seenEvents.push(event.topic));
  const envelope = createRequestEnvelope("desktop.state");
  const pending = router.createPendingRequest(envelope);

  router.handleLine('{"event":{"topic":"desktop.state.changed","payload":{}}}');
  router.handleLine(JSON.stringify({ id: envelope.id, ok: true, result: { console_open: false } }));

  const result = await pending;
  assert.deepEqual(seenEvents, ["desktop.state.changed"]);
  assert.equal(result.console_open, false);
});

test("jsonl router rejects failed responses", async () => {
  const router = new JsonlMessageRouter();
  const envelope = createRequestEnvelope("desktop.command");
  const pending = router.createPendingRequest(envelope);

  router.handleLine(JSON.stringify({ id: envelope.id, ok: false, error: "denied" }));

  await assert.rejects(pending, /denied/);
});

test("jsonl bridge transport writes serialized request lines", async () => {
  const lines = [];
  const router = new JsonlMessageRouter();
  const transport = new JsonlBridgeTransport({
    router,
    async sendLine(line) {
      lines.push(line);
      const parsed = JSON.parse(line);
      router.handleLine(JSON.stringify({ id: parsed.id, ok: true, result: { value: 42 } }));
    },
  });

  const result = await transport.request({ method: "core.health", params: {} });
  assert.equal(lines.length, 1);
  assert.equal(JSON.parse(lines[0]).method, "core.health");
  assert.equal(result.value, 42);
});

test("core session client preserves session id across desktop requests", async () => {
  const lines = [];
  const session = new CoreSessionClient({
    sessionId: "desktop-ui",
    async sendLine(line) {
      lines.push(JSON.parse(line));
      const request = JSON.parse(line);
      if (request.method === "desktop.attach") {
        session.handleLine(JSON.stringify({
          id: request.id,
          ok: true,
          result: {
            session_id: "desktop-ui",
            state: { attached_session_ids: ["desktop-ui"], console_open: false },
          },
        }));
        return;
      }
      session.handleLine(JSON.stringify({
        id: request.id,
        ok: true,
        result: { state: { attached_session_ids: ["desktop-ui"], console_open: true } },
      }));
    },
  });

  await session.attach({ surface: "test" });
  await session.desktopCommand("console.toggle");

  assert.equal(lines[0].params.session_id, "desktop-ui");
  assert.equal(lines[1].params.source, "desktop-ui");
});

test("core session client forwards events to subscribers", async () => {
  const seen = [];
  const session = new CoreSessionClient({
    async sendLine() {
      return undefined;
    },
  });
  session.onEvent((event) => seen.push(event.topic));
  session.handleLine('{"event":{"topic":"conversation.delta","payload":{"text":"hi"}}}');
  session.handleLine('{"event":{"topic":"desktop.state.changed","payload":{}}}');
  assert.deepEqual(seen, ["conversation.delta", "desktop.state.changed"]);
});

test("tauri event pump drains and forwards events", async () => {
  const seen = [];
  const pump = new TauriEventPump({
    commands: {
      async drainEvents() {
        pump.stop();
        return [
          { topic: "desktop.state.changed" },
          { topic: "conversation.delta" },
        ];
      },
    },
    onEvent(event) {
      seen.push(event.topic);
    },
    intervalMs: 5,
  });

  pump.start();
  await new Promise((resolve) => setTimeout(resolve, 15));
  assert.deepEqual(seen, ["desktop.state.changed", "conversation.delta"]);
});
