import test from "node:test";
import assert from "node:assert/strict";

import { CoreProtocolClient, createMessage } from "../src/protocol.js";
import {
  applyApprovalResponse,
  applyApprovalStatus,
  applyAgentBundle,
  applyAgentBundleStatus,
  applyAllowAllCmdGrant,
  applyAllowAllCmdStatus,
  appendMessage,
  applyAnthropicConfigStatus,
  applyAnthropicMessagesSettings,
  applyActiveDrawer,
  applyActiveProviderCatalog,
  applyActiveProviderDraft,
  applyActiveProviderSettings,
  applyActiveProviderStatus,
  applyBridgeRuntime,
  applyConversationSettings,
  applyInspectorSelection,
  applyCoreEvent,
  applyDesktopSnapshot,
  applyOpenAICompatibleSettings,
  applyPendingApprovals,
  applyParallelInspectStatus,
  applyParallelInspectResults,
  applyPromptPreview,
  applyPromptPreviewStatus,
  applyProviderConfigStatus,
  applyProviderHealth,
  applyProviderNames,
  applySettingsStatus,
  buildRunCopyArtifacts,
  applyToolActivitySnapshot,
  applyToolActivityStatus,
  applyToolCatalogStatus,
  applyToolsCatalog,
  applyToolGuide,
  applyToolGuideStatus,
  createActiveProviderDraft,
  defaultDesktopViewState,
  findLatestToolActivityForRun,
  groupRunInspectorItems,
  linkLatestUserMessageToRun,
  expandRunGroup,
  summarizeDesktopText,
  summarizeRunGroup,
  selectAnthropicConfig,
  selectProviderConfig,
  setConversationId,
  toggleRunGroupCollapsed,
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
  await client.getToolActivitySnapshot();
  await client.listTools();
  await client.listTools({ providerRole: "coding_agent" });
  await client.getToolsGuide({ providerRole: "coding_agent" });
  await client.getConversationPromptPreview({ providerRole: "coding_agent" });
  await client.getAgentBundle({ providerRole: "coding_agent" });
  await client.invokeMany(
    [{ name: "workspace.read", arguments: { path: "README.md" } }],
    { parallel: true, actor: "desktop-ui", sessionId: "desktop-ui" },
  );
  await client.getAllowAllCmd("desktop-ui");
  await client.setAllowAllCmd("desktop-ui", true);
  await client.getActiveProviderSettings();
  await client.getActiveProviderCatalog({ provider: { kind: "llama.cpp" } });
  await client.updateActiveProviderSettings({ provider: { kind: "llama.cpp", provider_name: "localhost.chat", model: "Qwen3-4B-Q5_K_M.gguf" } });
  await client.saveActiveProviderSettings({ provider: { kind: "llama.cpp", provider_name: "localhost.chat", model: "Qwen3-4B-Q5_K_M.gguf" } });
  await client.desktopDetach("desktop-ui");

  assert.deepEqual(
    calls.map((item) => item.method),
    [
      "desktop.attach",
      "desktop.command",
      "approval.pending.list",
      "approval.respond",
      "tool.activity.snapshot",
      "tools.list",
      "tools.list",
      "tools.guide",
      "conversations.prompt_preview",
      "agents.bundle",
      "tools.invoke_many",
      "permissions.allow_all_cmd.get",
      "permissions.allow_all_cmd.set",
      "settings.providers.active.get",
      "settings.providers.active.catalog",
      "settings.providers.active.update",
      "settings.providers.active.update",
      "desktop.detach",
    ],
  );
  assert.equal(calls[1].params.command, "console.toggle");
  assert.equal(calls[3].params.approval_id, "approval-1");
  assert.equal(calls[6].params.provider_role, "coding_agent");
  assert.equal(calls[7].params.provider_role, "coding_agent");
  assert.equal(calls[8].params.provider_role, "coding_agent");
  assert.equal(calls[9].params.provider_role, "coding_agent");
  assert.equal(calls[10].params.parallel, true);
  assert.equal(calls[12].params.allowed, true);
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
  assert.equal(health[0].provider, "localhost.chat");
  const settings = await client.getConversationSettings();
  assert.equal(settings.routes.chat.provider, "localhost.chat");
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
  assert.equal(providerSettings.providers[0].provider_name, "localhost.chat");
  const updatedProviderSettings = await client.updateOpenAICompatibleSettings({
    providers: [
      {
        ...providerSettings.providers[0],
        model: "Qwen3-4B-Q5_K_M.gguf",
        headers: {
          Authorization: "Bearer test",
        },
      },
    ],
  });
  assert.equal(updatedProviderSettings.providers[0].model, "Qwen3-4B-Q5_K_M.gguf");
  assert.equal(updatedProviderSettings.providers[0].headers.Authorization, "Bearer test");
  const savedProviderSettings = await client.saveOpenAICompatibleSettings({
    providers: [
      ...updatedProviderSettings.providers,
      {
        provider_name: "custom.provider.2",
        backend: "custom",
        base_url: "http://127.0.0.1:8080/v1",
        model: "Qwen3-4B-Q5_K_M.gguf",
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
  const tools = await client.listTools();
  assert.equal(tools[0].metadata.parallel_safe, true);
  const toolGuide = await client.getToolsGuide({ providerRole: "coding_agent" });
  assert.equal(toolGuide.provider_role, "coding_agent");
  assert.equal(toolGuide.tools[0].name, "workspace_read");
  const promptPreview = await client.getConversationPromptPreview({ providerRole: "coding_agent" });
  assert.equal(promptPreview.provider_role, "coding_agent");
  assert.match(promptPreview.system_instruction, /Coding agent tool guide/);
  const agentBundle = await client.getAgentBundle({ providerRole: "coding_agent" });
  assert.equal(agentBundle.provider_role, "coding_agent");
  assert.equal(agentBundle.route.prompt_profile, "coding_agent");
  assert.equal(Array.isArray(agentBundle.tools), true);
  assert.equal(agentBundle.codex_manifest.provider_role, "coding_agent");
  assert.equal(Array.isArray(agentBundle.codex_manifest.tools), true);
  const invoked = await client.invokeMany(
    [{ name: "workspace.read", arguments: { path: "src/demo.js", start_line: 1, end_line: 5 } }],
    { parallel: true, actor: "desktop-ui", sessionId: "desktop-preview" },
  );
  assert.equal(invoked.parallel, true);
  assert.equal(invoked.results[0].output.path, "src/demo.js");
  const initialGrant = await client.getAllowAllCmd("desktop-preview");
  assert.equal(initialGrant.allow_all_cmd, false);
  const updatedGrant = await client.setAllowAllCmd("desktop-preview", true);
  assert.equal(updatedGrant.allow_all_cmd, true);
  assert.equal((await client.getAllowAllCmd("desktop-preview")).allow_all_cmd, true);
});

test("mock active provider updates persist the selected runtime config", async () => {
  const client = new CoreProtocolClient(createMockTransport());

  const initial = await client.getActiveProviderSettings();
  assert.equal(initial.active_provider.provider_name, "localhost.chat");
  assert.equal(initial.active_provider.model, "Qwen3-4B-Q5_K_M.gguf");

  const applied = await client.updateActiveProviderSettings({
    provider: {
      kind: "openai",
      provider_name: "openai.chat",
      model: "gpt-4.1-mini",
      api_key_env: "OPENAI_API_KEY",
      timeout_seconds: 90,
      health_timeout_seconds: 7,
      temperature: 0.3,
      max_tokens: 4096,
    },
  });
  assert.equal(applied.active_provider.provider_name, "openai.chat");
  assert.equal(applied.active_provider.base_url, "https://api.openai.com/v1");
  assert.equal(applied.conversation.default_provider, "openai.chat");
  assert.equal(applied.conversation.routes.chat.provider, "openai.chat");
  assert.equal(applied.conversation.routes.coding_agent.provider, "openai.chat");

  const reloaded = await client.getActiveProviderSettings();
  assert.equal(reloaded.active_provider.provider_name, "openai.chat");
  assert.equal(reloaded.active_provider.model, "gpt-4.1-mini");
  assert.equal(reloaded.active_provider.timeout_seconds, 90);
  assert.equal(reloaded.active_provider.temperature, 0.3);

  const catalog = await client.getActiveProviderCatalog({
    provider: reloaded.active_provider,
  });
  assert.equal(catalog.kind, "openai");
  assert.equal(catalog.selected_model, "gpt-4.1-mini");
  assert.equal(catalog.reachable, true);
  assert.equal(catalog.ok, true);
  assert.equal(catalog.models.includes("gpt-4.1-mini"), true);
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
  const withHealth = applyProviderHealth(withMessages, [{ provider: "localhost.chat", ok: true }]);
  const withProviders = applyProviderNames(withHealth, ["localhost.chat"]);
  const withSettings = applyConversationSettings(withProviders, {
    default_provider: "localhost.chat",
    routes: {
      chat: { provider: "localhost.chat", prompt_profile: "default" },
      coding_agent: { provider: "localhost.chat", prompt_profile: "coding_agent" },
    },
    prompt_profiles: {
      default: { personality: "Short" },
      coding_agent: { personality: "Coder" },
    },
  });
  const withStatus = applySettingsStatus(withSettings, "Runtime settings applied");
  const withDrawer = applyActiveDrawer(withStatus, "config");
  const withActiveProviderSettings = applyActiveProviderSettings(withDrawer, {
    active_provider: {
      kind: "llama.cpp",
      provider_name: "localhost.chat",
      model: "Qwen3-4B-Q5_K_M.gguf",
      host: "127.0.0.1",
      port: 8080,
      base_url: "http://127.0.0.1:8080/v1",
      timeout_seconds: 120,
      health_timeout_seconds: 5,
      temperature: 0.7,
      max_tokens: 2048,
    },
    provider_options: [{ kind: "llama.cpp", default_provider_name: "localhost.chat" }],
  });
  const withActiveProviderStatus = applyActiveProviderStatus(
    withActiveProviderSettings,
    "Active provider applied",
  );
  const withActiveProviderCatalog = applyActiveProviderCatalog(withActiveProviderStatus, {
    models: ["Qwen3-4B-Q5_K_M.gguf"],
    selected_model: "Qwen3-4B-Q5_K_M.gguf",
    ok: true,
    reachable: true,
  });
  const withActiveProviderDraft = applyActiveProviderDraft(
    withActiveProviderCatalog,
    createActiveProviderDraft(
      withActiveProviderCatalog.activeProviderSettings.active_provider,
      withActiveProviderCatalog.activeProviderSettings.provider_options,
    ),
    { dirty: true },
  );
  const withOpenAICompat = applyOpenAICompatibleSettings(withStatus, {
    providers: [{ provider_name: "localhost.chat", model: "Qwen3-4B-Q5_K_M.gguf" }],
  });
  const withSelectedProvider = selectProviderConfig(withOpenAICompat, "localhost.chat");
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
  const withToolsCatalog = applyToolsCatalog(withApprovalStatus, [
    {
      name: "workspace.read",
      output_kind: "file_content",
      metadata: { parallel_safe: true, mutates_state: false },
    },
  ]);
  const withToolStatus = applyToolCatalogStatus(withToolsCatalog, "Tool catalog synced");
  const withToolGuide = applyToolGuide(withToolStatus, {
    provider_role: "coding_agent",
    workflow: ["Inspect first"],
    tools: [{ name: "workspace_read", summary: "Read files" }],
  });
  const withToolGuideStatus = applyToolGuideStatus(withToolGuide, "Tool guide synced");
  const withPromptPreview = applyPromptPreview(withToolGuideStatus, {
    provider_role: "coding_agent",
    prompt_profile: "coding_agent",
    system_instruction: "System:\nCode carefully",
    tool_count: 2,
  });
  const withPromptPreviewStatus = applyPromptPreviewStatus(withPromptPreview, "Prompt preview synced");
  const withAgentBundle = applyAgentBundle(withPromptPreviewStatus, {
    provider_role: "coding_agent",
    route: { provider: "localhost.chat", prompt_profile: "coding_agent" },
    tools: [{ name: "workspace_read" }, { name: "shell_run" }],
  });
  const withAgentBundleStatus = applyAgentBundleStatus(withAgentBundle, "Agent bundle synced");
  const withGrant = applyAllowAllCmdGrant(withToolStatus, {
    allow_all_cmd: true,
    updated_by: "desktop-ui",
  });
  const withGrantStatus = applyAllowAllCmdStatus(withGrant, "Grant syncing");
  const withParallelInspect = applyParallelInspectStatus(
    withGrantStatus,
    "Parallel inspect completed",
  );
  const withParallelResults = applyParallelInspectResults(withParallelInspect, [
    {
      path: "PROJECT_HANDOFF.md",
      status: "succeeded",
      content: "mock",
    },
  ]);
  const withToolActivityStatus = applyToolActivityStatus(
    withParallelResults,
    "Running workspace.read",
  );
  const withToolActivitySnapshot = applyToolActivitySnapshot(withToolActivityStatus, {
    items: [
      {
        request_id: "request-1",
        tool_name: "workspace.read",
        status: "waiting_approval",
      },
    ],
    status: "Approval requested for workspace.read",
  });
  const withInspectorSelection = applyInspectorSelection(withToolActivitySnapshot, {
    request_id: "request-1",
    message_id: "tool-result-call-1",
  });
  const withLinkedRun = linkLatestUserMessageToRun(
    appendMessage(withInspectorSelection, { id: "user-1", role: "user", text: "hi" }),
    "run-9",
    "conversation-1",
  );
  const withCollapsedRun = toggleRunGroupCollapsed(withLinkedRun, "run-9");
  const withExpandedRun = expandRunGroup(withCollapsedRun, "run-9");

  assert.equal(initial.consoleOpen, false);
  assert.equal(snapped.consoleOpen, true);
  assert.equal(withConversation.conversationId, "conversation-1");
  assert.equal(withMessages.messages.length, 1);
  assert.equal(withHealth.providerHealthSummary, "providers: 1/1 healthy");
  assert.equal(withProviders.availableProviders[0], "localhost.chat");
  assert.equal(withSettings.conversationSettings.default_provider, "localhost.chat");
  assert.equal(withStatus.settingsStatus, "Runtime settings applied");
  assert.equal(withDrawer.activeDrawer, "config");
  assert.equal(withActiveProviderSettings.activeProviderSettings.active_provider.provider_name, "localhost.chat");
  assert.equal(withActiveProviderStatus.activeProviderStatus, "Active provider applied");
  assert.equal(withActiveProviderCatalog.activeProviderCatalog.selected_model, "Qwen3-4B-Q5_K_M.gguf");
  assert.equal(withActiveProviderDraft.activeProviderDraftDirty, true);
  assert.equal(withOpenAICompat.openaiCompatibleSettings.providers[0].model, "Qwen3-4B-Q5_K_M.gguf");
  assert.equal(withSelectedProvider.selectedProviderConfigName, "localhost.chat");
  assert.equal(withProviderStatus.providerConfigStatus, "Provider config applied");
  assert.equal(withAnthropicSettings.anthropicMessagesSettings.providers[0].model, "claude-sonnet-4-20250514");
  assert.equal(withSelectedAnthropic.selectedAnthropicConfigName, "claude.coder");
  assert.equal(withAnthropicStatus.anthropicConfigStatus, "Anthropic config applied");
  assert.equal(withApprovals.pendingApprovals.length, 1);
  assert.equal(withApprovals.approvalStatus, "1 approval pending");
  assert.equal(withResolvedApproval.pendingApprovals.length, 0);
  assert.equal(withApprovalStatus.approvalStatus, "Approval denied");
  assert.equal(withToolsCatalog.toolsCatalog.length, 1);
  assert.equal(withToolStatus.toolCatalogStatus, "Tool catalog synced");
  assert.equal(withToolGuide.toolGuide.tools[0].name, "workspace_read");
  assert.equal(withToolGuide.toolGuideStatus, "1 preferred tool in playbook");
  assert.equal(withToolGuideStatus.toolGuideStatus, "Tool guide synced");
  assert.equal(withPromptPreview.promptPreview.provider_role, "coding_agent");
  assert.equal(withPromptPreview.promptPreviewStatus, "Runtime prompt ready for coding_agent");
  assert.equal(withPromptPreviewStatus.promptPreviewStatus, "Prompt preview synced");
  assert.equal(withAgentBundle.agentBundle.tools.length, 2);
  assert.equal(withAgentBundle.agentBundleStatus, "coding_agent bundle ready | 2 tools");
  assert.equal(withAgentBundleStatus.agentBundleStatus, "Agent bundle synced");
  assert.equal(withGrant.allowAllCmd, true);
  assert.equal(withGrant.allowAllCmdUpdatedBy, "desktop-ui");
  assert.equal(withGrantStatus.allowAllCmdStatus, "Grant syncing");
  assert.equal(withParallelInspect.parallelInspectStatus, "Parallel inspect completed");
  assert.equal(withParallelResults.parallelInspectResults.length, 1);
  assert.equal(withParallelResults.parallelInspectResults[0].path, "PROJECT_HANDOFF.md");
  assert.equal(withToolActivityStatus.toolActivityStatus, "Running workspace.read");
  assert.equal(withToolActivitySnapshot.toolActivity.length, 1);
  assert.equal(withToolActivitySnapshot.toolActivity[0].request_id, "request-1");
  assert.equal(
    withToolActivitySnapshot.toolActivityStatus,
    "Approval requested for workspace.read",
  );
  assert.equal(withInspectorSelection.inspectorSelection.request_id, "request-1");
  assert.equal(withLinkedRun.messages.at(-1).run_id, "run-9");
  assert.equal(withCollapsedRun.collapsedRunIds.includes("run-9"), true);
  assert.equal(withExpandedRun.collapsedRunIds.includes("run-9"), false);
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
    payload: { text: "Echo: ", run_id: "run-0", conversation_id: "conversation-1" },
  });
  const completed = applyCoreEvent(withDelta, {
    topic: "conversation.run.completed",
    payload: {
      run_id: "run-0",
      conversation_id: "conversation-1",
      message: { content: "Echo: hello", metadata: { run_id: "run-0" } },
    },
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
  const withGrantEvent = applyCoreEvent(resolved, {
    topic: "permission.grant.updated",
    payload: {
      session_id: "desktop-ui",
      allow_all_cmd: true,
      updated_by: "desktop-ui",
    },
  });
  const withToolRequested = applyCoreEvent(withGrantEvent, {
    topic: "conversation.tool.requested",
    payload: {
      run_id: "run-1",
      conversation_id: "conversation-1",
      request_id: "request-1",
      tool_call: {
        id: "call-1",
        name: "workspace.read",
        arguments: { path: "README.md" },
      },
    },
  });
  const withToolStarted = applyCoreEvent(withToolRequested, {
    topic: "tool.started",
    payload: {
      request_id: "request-1",
      tool: "workspace.read",
      tool_call_id: "call-1",
      run_id: "run-1",
    },
  });
  const withApprovalForTool = applyCoreEvent(withToolStarted, {
    topic: "approval.pending",
    payload: {
      approval_id: "approval-2",
      request_id: "request-1",
      tool_name: "workspace.read",
      reason: "Need approval",
      arguments: { path: "README.md" },
    },
  });
  const withApprovalResponseForTool = applyCoreEvent(withApprovalForTool, {
    topic: "approval.responded",
    payload: {
      approval_id: "approval-2",
      request_id: "request-1",
      tool_name: "workspace.read",
      approved: true,
    },
  });
  const withToolFinished = applyCoreEvent(withApprovalForTool, {
    topic: "tool.finished",
    payload: {
      request_id: "request-1",
      tool_name: "workspace.read",
      tool_call_id: "call-1",
      status: "succeeded",
      output: { path: "README.md", content: "ok" },
    },
  });
  const withProfileDeniedTool = applyCoreEvent(withToolFinished, {
    topic: "conversation.tool.requested",
    payload: {
      run_id: "run-2",
      conversation_id: "conversation-1",
      request_id: "request-2",
      tool_call: {
        id: "call-2",
        name: "shell.run",
        arguments: { command: "git push" },
      },
    },
  });
  const withProfileDeniedFinished = applyCoreEvent(withProfileDeniedTool, {
    topic: "tool.finished",
    payload: {
      request_id: "request-2",
      tool_name: "shell.run",
      tool_call_id: "call-2",
      status: "denied",
      error: "Capability shell.execute is outside profile observe",
    },
  });
  const withUserDeniedTool = applyCoreEvent(withProfileDeniedFinished, {
    topic: "conversation.tool.requested",
    payload: {
      run_id: "run-3",
      conversation_id: "conversation-1",
      request_id: "request-3",
      tool_call: {
        id: "call-3",
        name: "shell.run",
        arguments: { command: "git push" },
      },
    },
  });
  const withUserDeniedPending = applyCoreEvent(withUserDeniedTool, {
    topic: "approval.pending",
    payload: {
      approval_id: "approval-3",
      request_id: "request-3",
      tool_name: "shell.run",
      reason: "Need approval",
      arguments: { command: "git push" },
    },
  });
  const withUserDeniedResponse = applyCoreEvent(withUserDeniedPending, {
    topic: "approval.responded",
    payload: {
      approval_id: "approval-3",
      request_id: "request-3",
      tool_name: "shell.run",
      approved: false,
    },
  });

  assert.equal(withRuntime.bridgeTransport, "spawned");
  assert.equal(withRuntime.bridgeProcessStarted, true);
  assert.equal(withDesktopEvent.consoleOpen, true);
  assert.equal(withDesktopEvent.presence, "thinking");
  assert.equal(completed.messages.at(-1).text, "Echo: hello");
  assert.equal(completed.messages.at(-1).run_id, "run-0");
  assert.equal(completed.activeAssistantMessageId, null);
  assert.equal(withPendingApproval.pendingApprovals.length, 1);
  assert.equal(resolved.pendingApprovals.length, 0);
  assert.equal(withGrantEvent.allowAllCmd, true);
  assert.equal(withToolRequested.toolActivity.length, 1);
  assert.equal(withToolStarted.toolActivity.find((item) => item.tool_call_id === "call-1").status, "running");
  assert.equal(withApprovalForTool.toolActivity.find((item) => item.tool_call_id === "call-1").status, "waiting_approval");
  assert.equal(withApprovalResponseForTool.toolActivity.find((item) => item.tool_call_id === "call-1").status, "approved_pending_run");
  assert.equal(withToolFinished.toolActivity.find((item) => item.tool_call_id === "call-1").status, "succeeded");
  assert.equal(withToolFinished.messages.at(-1).role, "tool");
  assert.equal(withToolFinished.messages.at(-1).request_id, "request-1");
  assert.equal(withProfileDeniedFinished.toolActivity.find((item) => item.tool_call_id === "call-2").status, "denied_by_profile");
  assert.equal(withUserDeniedResponse.toolActivity.find((item) => item.tool_call_id === "call-3").status, "denied_by_user");
});

test("run summary helpers build copy-ready artifacts", () => {
  const group = {
    run_id: "run-42",
    messages: [
      { role: "user", text: "Inspect the repo", run_id: "run-42" },
      {
        role: "assistant",
        text: "I inspected the repo and found the failing reconnect hydration path.",
        run_id: "run-42",
      },
      {
        role: "tool",
        tool_name: "workspace.read",
        status: "succeeded",
        output: { path: "docs/notes/tool_activity_reconnect_issue.md", content: "ok" },
        text: "",
        run_id: "run-42",
      },
    ],
  };

  assert.equal(summarizeDesktopText("  a   b  ", 20), "a b");

  const summary = summarizeRunGroup(group);
  assert.equal(summary.outcome, "complete");
  assert.equal(summary.assistantCount, 1);
  assert.equal(summary.toolCount, 1);
  assert.match(summary.assistantPreviewText, /^Assistant: I inspected the repo/);
  assert.match(summary.toolPreviewText, /^Latest tool: workspace\.read \| succeeded \| \{/);
  assert.match(summary.toolCopyText, /"path": "docs\/notes\/tool_activity_reconnect_issue\.md"/);

  const artifacts = buildRunCopyArtifacts(group);
  assert.match(artifacts.summaryText, /run run-42/);
  assert.match(artifacts.summaryText, /outcome: complete/);
  assert.equal(
    artifacts.assistantText,
    "I inspected the repo and found the failing reconnect hydration path.",
  );
  assert.match(artifacts.toolText, /"content": "ok"/);
  assert.match(artifacts.jsonText, /"run_id": "run-42"/);
  assert.match(artifacts.jsonText, /"outcome": "complete"/);

  const latestTool = findLatestToolActivityForRun(
    [
      { run_id: "run-42", request_id: "request-2", tool_name: "workspace.read" },
      { run_id: "run-41", request_id: "request-1", tool_name: "shell.run" },
    ],
    "run-42",
  );
  assert.equal(latestTool.request_id, "request-2");
  assert.equal(findLatestToolActivityForRun([], "run-42"), null);

  const inspectorGroups = groupRunInspectorItems([
    { run_id: "run-42", request_id: "request-2", tool_name: "workspace.read" },
    { run_id: "run-42", request_id: "request-3", tool_name: "shell.run" },
    { approval_id: "approval-9", tool_name: "approval-only" },
  ]);
  assert.equal(inspectorGroups.length, 2);
  assert.equal(inspectorGroups[0].kind, "run");
  assert.equal(inspectorGroups[0].run_id, "run-42");
  assert.equal(inspectorGroups[0].items.length, 2);
  assert.equal(inspectorGroups[1].kind, "standalone");
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
              : request.method === "tool.activity.snapshot"
                ? {
                    items: [
                      {
                        request_id: "request-1",
                        tool_name: "workspace.read",
                        status: "waiting_approval",
                      },
                    ],
                    status: "Approval requested for workspace.read",
                  }
              : request.method === "tools.list"
                ? [
                    {
                      name: "workspace.read",
                      output_kind: "file_content",
                        metadata: { parallel_safe: true, mutates_state: false },
                    },
                  ]
                : request.method === "tools.guide"
                  ? {
                      provider_role: request.params.provider_role || null,
                      workflow: ["Inspect first"],
                      tools: [
                        {
                          name: "workspace_read",
                          summary: "Read files",
                          when_to_use: "Inspect target files",
                          avoid_when: "When you need to edit",
                        },
                      ],
                      text: "Coding agent tool guide",
                    }
                : request.method === "conversations.prompt_preview"
                  ? {
                      provider_role: request.params.provider_role || "chat",
                      prompt_profile: "coding_agent",
                      system_instruction: "System:\nCode carefully\n\nCoding agent tool guide",
                      tool_count: 1,
                    }
                : request.method === "agents.bundle"
                  ? {
                      provider_role: request.params.provider_role || "coding_agent",
                      route: {
                        provider: "localhost.chat",
                        prompt_profile: "coding_agent",
                      },
                      active_provider: {
                        kind: "llama.cpp",
                        provider_name: "localhost.chat",
                      },
                      prompt_preview: {
                        provider_role: "coding_agent",
                        prompt_profile: "coding_agent",
                        system_instruction: "System:\nCode carefully\n\nCoding agent tool guide",
                        tool_count: 1,
                      },
                      tool_guide: {
                        provider_role: "coding_agent",
                        workflow: ["Inspect first"],
                        tools: [{ name: "workspace_read" }],
                      },
                      codex_manifest: {
                        provider_role: request.params.provider_role || "coding_agent",
                        system_prompt: "System:\nCode carefully\n\nCoding agent tool guide",
                        tool_instructions: ["Inspect first"],
                        approval_rules: {
                          profile: "assist",
                          interactive_approval: true,
                          dangerous_model_actions_blocked_in_assist: true,
                        },
                        parallel_rules: {
                          read_only_parallel_only: true,
                          writes_and_shell_sequential: true,
                        },
                        tools: [{ name: "workspace_read" }],
                      },
                      tools: [
                        {
                          name: "workspace_read",
                          output_kind: "file_content",
                        },
                      ],
                    }
                : request.method === "tools.invoke_many"
                  ? {
                      parallel: request.params.parallel,
                      results: [
                        {
                          tool_name: "workspace.read",
                          status: "succeeded",
                          output: {
                            path: "README.md",
                            content: "mock",
                          },
                        },
                      ],
                    }
                  : request.method === "permissions.allow_all_cmd.get"
                    ? {
                        session_id: request.params.session_id,
                        allow_all_cmd: false,
                        updated_by: "none",
                      }
                    : request.method === "permissions.allow_all_cmd.set"
                      ? {
                          session_id: request.params.session_id,
                          allow_all_cmd: request.params.allowed,
                          updated_by: request.params.actor,
                        }
            : request.method === "providers.health"
            ? [{ provider: "localhost.chat", ok: true }]
            : request.method === "settings.conversation.get"
              ? {
                  default_provider: "localhost.chat",
                  routes: {
                    chat: { provider: "localhost.chat", prompt_profile: "default" },
                    coding_agent: {
                      provider: "localhost.chat",
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
                        provider_name: "localhost.chat",
                        backend: "llama.cpp",
                        base_url: "http://127.0.0.1:8080/v1",
                        model: "Qwen3-4B-Q5_K_M.gguf",
                        timeout_seconds: 120,
                        health_timeout_seconds: 5,
                        temperature: 0.7,
                        max_tokens: 2048,
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
  await session.getToolActivitySnapshot();
  await session.providersHealth();
  await session.getConversationSettings();
  await session.updateConversationSettings({
    default_provider: "localhost.chat",
    routes: {
      chat: { provider: "localhost.chat", prompt_profile: "default" },
      coding_agent: { provider: "localhost.chat", prompt_profile: "coding_agent" },
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
        provider_name: "localhost.chat",
        backend: "llama.cpp",
        base_url: "http://127.0.0.1:8080/v1",
        model: "Qwen3-4B-Q5_K_M.gguf",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.7,
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
  await session.listTools();
  await session.getToolsGuide({ providerRole: "coding_agent" });
  await session.getConversationPromptPreview({ providerRole: "coding_agent" });
  await session.getAgentBundle({ providerRole: "coding_agent" });
  await session.invokeMany(
    [{ name: "workspace.read", arguments: { path: "README.md" } }],
    { parallel: true },
  );
  await session.getAllowAllCmd();
  await session.setAllowAllCmd(true);

  assert.equal(lines[0].params.session_id, "desktop-ui");
  assert.equal(lines[1].params.source, "desktop-ui");
  assert.equal(lines[2].method, "approval.pending.list");
  assert.equal(lines[3].method, "approval.respond");
  assert.equal(lines[4].method, "tool.activity.snapshot");
  assert.equal(lines[5].method, "providers.health");
  assert.equal(lines[6].method, "settings.conversation.get");
  assert.equal(lines[7].method, "settings.conversation.update");
  assert.equal(lines[8].method, "settings.providers.openai_compat.get");
  assert.equal(lines[9].method, "settings.providers.openai_compat.update");
  assert.equal(lines[10].method, "settings.providers.anthropic_messages.get");
  assert.equal(lines[11].method, "settings.providers.anthropic_messages.update");
  assert.equal(lines[12].method, "tools.list");
  assert.equal(lines[13].method, "tools.guide");
  assert.equal(lines[13].params.provider_role, "coding_agent");
  assert.equal(lines[14].method, "conversations.prompt_preview");
  assert.equal(lines[14].params.provider_role, "coding_agent");
  assert.equal(lines[15].method, "agents.bundle");
  assert.equal(lines[15].params.provider_role, "coding_agent");
  assert.equal(lines[16].method, "tools.invoke_many");
  assert.equal(lines[16].params.session_id, "desktop-ui");
  assert.equal(lines[17].method, "permissions.allow_all_cmd.get");
  assert.equal(lines[18].method, "permissions.allow_all_cmd.set");
  assert.equal(lines[18].params.allowed, true);
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
