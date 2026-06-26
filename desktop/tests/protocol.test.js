import test from "node:test";
import assert from "node:assert/strict";

import { CoreProtocolClient, createMessage } from "../src/protocol.js";
import {
  applyApprovalResponse,
  applyApprovalStatus,
  appendMessage,
  applyAnthropicConfigStatus,
  applyAnthropicMessagesSettings,
  applyBridgeRuntime,
  applyConversationSettings,
  applyCoreEvent,
  applyDesktopSnapshot,
  applyOpenAICompatibleSettings,
  applyPendingApprovals,
  applyProviderConfigStatus,
  applyProviderHealth,
  applyProviderNames,
  applySettingsStatus,
  defaultDesktopViewState,
  selectAnthropicConfig,
  selectProviderConfig,
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
  await client.listPendingApprovals();
  await client.respondApproval("approval-1", true);
  await client.desktopDetach("desktop-ui");

  assert.deepEqual(
    calls.map((item) => item.method),
    [
      "desktop.attach",
      "desktop.command",
      "approval.pending.list",
      "approval.respond",
      "desktop.detach",
    ],
  );
  assert.equal(calls[1].params.command, "console.toggle");
  assert.equal(calls[3].params.approval_id, "approval-1");
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
  const health = await client.providersHealth();
  assert.equal(health[0].provider, "fake.echo");
  const settings = await client.getConversationSettings();
  assert.equal(settings.routes.chat.provider, "fake.echo");
  const updated = await client.updateConversationSettings({
    ...settings,
    prompt_profiles: {
      ...settings.prompt_profiles,
      default: {
        ...settings.prompt_profiles.default,
        personality: "Changed",
      },
    },
  });
  assert.equal(updated.prompt_profiles.default.personality, "Changed");
  const saved = await client.saveConversationSettings({
    ...updated,
    prompt_profiles: {
      ...updated.prompt_profiles,
      coding_agent: {
        ...updated.prompt_profiles.coding_agent,
        system_instruction: "Persisted",
      },
    },
  });
  assert.equal(saved.prompt_profiles.coding_agent.system_instruction, "Persisted");
  const providerSettings = await client.getOpenAICompatibleSettings();
  assert.equal(providerSettings.providers[0].provider_name, "ollama.chat");
  const updatedProviderSettings = await client.updateOpenAICompatibleSettings({
    providers: [
      {
        ...providerSettings.providers[0],
        model: "qwen2.5-coder",
        headers: {
          Authorization: "Bearer test",
        },
      },
    ],
  });
  assert.equal(updatedProviderSettings.providers[0].model, "qwen2.5-coder");
  assert.equal(updatedProviderSettings.providers[0].headers.Authorization, "Bearer test");
  const savedProviderSettings = await client.saveOpenAICompatibleSettings({
    providers: [
      ...updatedProviderSettings.providers,
      {
        provider_name: "custom.provider.2",
        backend: "custom",
        base_url: "http://127.0.0.1:8080/v1",
        model: "replace-me",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.7,
        max_tokens: 1024,
        headers: {
          "X-Test": "custom",
        },
      },
    ],
  });
  assert.equal(savedProviderSettings.providers.length, 2);
  assert.equal(savedProviderSettings.providers[1].headers["X-Test"], "custom");
  const anthropicSettings = await client.getAnthropicMessagesSettings();
  assert.equal(anthropicSettings.providers[0].provider_name, "claude.coder");
  const updatedAnthropicSettings = await client.updateAnthropicMessagesSettings({
    providers: [
      {
        ...anthropicSettings.providers[0],
        model: "claude-3-7-sonnet-latest",
        headers: {
          "X-Workspace": "yue",
        },
      },
    ],
  });
  assert.equal(updatedAnthropicSettings.providers[0].model, "claude-3-7-sonnet-latest");
  assert.equal(updatedAnthropicSettings.providers[0].headers["X-Workspace"], "yue");
  const savedAnthropicSettings = await client.saveAnthropicMessagesSettings({
    providers: [
      ...updatedAnthropicSettings.providers,
      {
        provider_name: "claude.provider.2",
        backend: "anthropic",
        base_url: "https://api.anthropic.com",
        model: "claude-sonnet-4-20250514",
        api_key_env: "ANTHROPIC_API_KEY",
        anthropic_version: "2023-06-01",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.2,
        max_tokens: 2048,
        headers: {
          "X-Test": "anthropic",
        },
      },
    ],
  });
  assert.equal(savedAnthropicSettings.providers.length, 2);
  assert.equal(savedAnthropicSettings.providers[1].headers["X-Test"], "anthropic");
  const pendingApprovals = await client.listPendingApprovals();
  assert.equal(pendingApprovals.length, 1);
  assert.equal(pendingApprovals[0].tool_name, "shell.run");
  const approvalResponse = await client.respondApproval(
    pendingApprovals[0].approval_id,
    true,
  );
  assert.equal(approvalResponse.approved, true);
  assert.equal((await client.listPendingApprovals()).length, 0);
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
  const withHealth = applyProviderHealth(withMessages, [{ provider: "fake.echo", ok: true }]);
  const withProviders = applyProviderNames(withHealth, ["fake.echo"]);
  const withSettings = applyConversationSettings(withProviders, {
    default_provider: "fake.echo",
    routes: {
      chat: { provider: "fake.echo", prompt_profile: "default" },
      coding_agent: { provider: "fake.echo", prompt_profile: "coding_agent" },
    },
    prompt_profiles: {
      default: { personality: "Short" },
      coding_agent: { personality: "Coder" },
    },
  });
  const withStatus = applySettingsStatus(withSettings, "Runtime settings applied");
  const withOpenAICompat = applyOpenAICompatibleSettings(withStatus, {
    providers: [{ provider_name: "ollama.chat", model: "qwen2.5" }],
  });
  const withSelectedProvider = selectProviderConfig(withOpenAICompat, "ollama.chat");
  const withProviderStatus = applyProviderConfigStatus(
    withSelectedProvider,
    "Provider config applied",
  );
  const withAnthropicSettings = applyAnthropicMessagesSettings(withProviderStatus, {
    providers: [{ provider_name: "claude.coder", model: "claude-sonnet-4-20250514" }],
  });
  const withSelectedAnthropic = selectAnthropicConfig(withAnthropicSettings, "claude.coder");
  const withAnthropicStatus = applyAnthropicConfigStatus(
    withSelectedAnthropic,
    "Anthropic config applied",
  );
  const withApprovals = applyPendingApprovals(withAnthropicStatus, [
    {
      approval_id: "approval-1",
      tool_name: "shell.run",
      reason: "needs approval",
      arguments: { command: "git push" },
    },
    {
      approval_id: "approval-1",
      tool_name: "shell.run",
      reason: "needs approval",
      arguments: { command: "git push" },
    },
  ]);
  const withResolvedApproval = applyApprovalResponse(withApprovals, "approval-1");
  const withApprovalStatus = applyApprovalStatus(withResolvedApproval, "Approval denied");

  assert.equal(initial.consoleOpen, false);
  assert.equal(snapped.consoleOpen, true);
  assert.equal(withConversation.conversationId, "conversation-1");
  assert.equal(withMessages.messages.length, 1);
  assert.equal(withHealth.providerHealthSummary, "providers: 1/1 healthy");
  assert.equal(withProviders.availableProviders[0], "fake.echo");
  assert.equal(withSettings.conversationSettings.default_provider, "fake.echo");
  assert.equal(withStatus.settingsStatus, "Runtime settings applied");
  assert.equal(withOpenAICompat.openaiCompatibleSettings.providers[0].model, "qwen2.5");
  assert.equal(withSelectedProvider.selectedProviderConfigName, "ollama.chat");
  assert.equal(withProviderStatus.providerConfigStatus, "Provider config applied");
  assert.equal(withAnthropicSettings.anthropicMessagesSettings.providers[0].model, "claude-sonnet-4-20250514");
  assert.equal(withSelectedAnthropic.selectedAnthropicConfigName, "claude.coder");
  assert.equal(withAnthropicStatus.anthropicConfigStatus, "Anthropic config applied");
  assert.equal(withApprovals.pendingApprovals.length, 1);
  assert.equal(withApprovals.approvalStatus, "1 approval pending");
  assert.equal(withResolvedApproval.pendingApprovals.length, 0);
  assert.equal(withApprovalStatus.approvalStatus, "Approval denied");
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
  const withPendingApproval = applyCoreEvent(completed, {
    topic: "approval.pending",
    payload: {
      approval_id: "approval-1",
      tool_name: "shell.run",
      reason: "Command requires explicit approval",
      arguments: { command: "git push" },
    },
  });
  const resolved = applyCoreEvent(withPendingApproval, {
    topic: "approval.responded",
    payload: {
      approval_id: "approval-1",
      approved: true,
    },
  });

  assert.equal(withRuntime.bridgeTransport, "spawned");
  assert.equal(withRuntime.bridgeProcessStarted, true);
  assert.equal(withDesktopEvent.consoleOpen, true);
  assert.equal(withDesktopEvent.presence, "thinking");
  assert.equal(completed.messages.at(-1).text, "Echo: hello");
  assert.equal(completed.activeAssistantMessageId, null);
  assert.equal(withPendingApproval.pendingApprovals.length, 1);
  assert.equal(resolved.pendingApprovals.length, 0);
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
        result:
          request.method === "approval.pending.list"
            ? [
                {
                  approval_id: "approval-1",
                  tool_name: "shell.run",
                  reason: "needs approval",
                  arguments: { command: "git push" },
                },
              ]
            : request.method === "approval.respond"
              ? {
                  approval_id: request.params.approval_id,
                  approved: request.params.approved,
                }
            : request.method === "providers.health"
            ? [{ provider: "fake.echo", ok: true }]
            : request.method === "settings.conversation.get"
              ? {
                  default_provider: "fake.echo",
                  routes: {
                    chat: { provider: "fake.echo", prompt_profile: "default" },
                    coding_agent: {
                      provider: "fake.echo",
                      prompt_profile: "coding_agent",
                    },
                  },
                  prompt_profiles: {
                    default: { personality: "Local-first assistant." },
                    coding_agent: { personality: "Senior coding agent." },
                  },
                }
              : request.method === "settings.conversation.update"
                ? request.params
              : request.method === "settings.providers.openai_compat.get"
                ? {
                    providers: [
                      {
                        provider_name: "ollama.chat",
                        backend: "ollama",
                        base_url: "http://127.0.0.1:11434/v1",
                        model: "qwen2.5",
                        timeout_seconds: 120,
                        health_timeout_seconds: 5,
                        temperature: 0.6,
                        max_tokens: 1024,
                      },
                    ],
                  }
                : request.method === "settings.providers.openai_compat.update"
                  ? request.params
                : request.method === "settings.providers.anthropic_messages.get"
                  ? {
                      providers: [
                        {
                          provider_name: "claude.coder",
                          backend: "anthropic",
                          base_url: "https://api.anthropic.com",
                          model: "claude-sonnet-4-20250514",
                          timeout_seconds: 120,
                          health_timeout_seconds: 5,
                          temperature: 0.2,
                          max_tokens: 2048,
                          anthropic_version: "2023-06-01",
                        },
                      ],
                    }
                  : request.method === "settings.providers.anthropic_messages.update"
                    ? request.params
            : { state: { attached_session_ids: ["desktop-ui"], console_open: true } },
      }));
    },
  });

  await session.attach({ surface: "test" });
  await session.desktopCommand("console.toggle");
  await session.listPendingApprovals();
  await session.respondApproval("approval-1", false);
  await session.providersHealth();
  await session.getConversationSettings();
  await session.updateConversationSettings({
    default_provider: "fake.echo",
    routes: {
      chat: { provider: "fake.echo", prompt_profile: "default" },
      coding_agent: { provider: "fake.echo", prompt_profile: "coding_agent" },
    },
    prompt_profiles: {
      default: { personality: "Changed" },
      coding_agent: { personality: "Coder" },
    },
  });
  await session.getOpenAICompatibleSettings();
  await session.updateOpenAICompatibleSettings({
    providers: [
      {
        provider_name: "ollama.chat",
        backend: "ollama",
        base_url: "http://127.0.0.1:11434/v1",
        model: "qwen2.5-coder",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.4,
        max_tokens: 2048,
      },
    ],
  });
  await session.getAnthropicMessagesSettings();
  await session.updateAnthropicMessagesSettings({
    providers: [
      {
        provider_name: "claude.coder",
        backend: "anthropic",
        base_url: "https://api.anthropic.com",
        model: "claude-3-7-sonnet-latest",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.2,
        max_tokens: 2048,
        anthropic_version: "2023-06-01",
      },
    ],
  });

  assert.equal(lines[0].params.session_id, "desktop-ui");
  assert.equal(lines[1].params.source, "desktop-ui");
  assert.equal(lines[2].method, "approval.pending.list");
  assert.equal(lines[3].method, "approval.respond");
  assert.equal(lines[4].method, "providers.health");
  assert.equal(lines[5].method, "settings.conversation.get");
  assert.equal(lines[6].method, "settings.conversation.update");
  assert.equal(lines[7].method, "settings.providers.openai_compat.get");
  assert.equal(lines[8].method, "settings.providers.openai_compat.update");
  assert.equal(lines[9].method, "settings.providers.anthropic_messages.get");
  assert.equal(lines[10].method, "settings.providers.anthropic_messages.update");
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
