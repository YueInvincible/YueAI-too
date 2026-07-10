import { CoreProtocolClient, createMessage } from "./protocol.js";
import {
  applyApprovalResponse,
  applyApprovalStatus,
  applyAgentBundle,
  applyAgentBundleStatus,
  applyAgentStarterPack,
  applyAgentStarterPackStatus,
  applyAllowAllCmdGrant,
  applyAllowAllCmdStatus,
  applyAuditPreview,
  applyAuditPreviewStatus,
  applyCapabilityGrants,
  applyCapabilityGrantsStatus,
  appendMessage,
  applyAnthropicConfigStatus,
  applyAnthropicMessagesSettings,
  applyBridgeRuntime,
  applyConversationSettings,
  applyInspectorSelection,
  linkLatestUserMessageToRun,
  applyOpenAICompatibleSettings,
  applyParallelInspectStatus,
  applyParallelInspectResults,
  applyPendingApprovals,
  applyPromptPreview,
  applyPromptPreviewStatus,
  applyCoreEvent,
  applyDesktopSnapshot,
  applyProviderNames,
  applyProviderConfigStatus,
  applyProviderHealth,
  applySettingsStatus,
  buildRunCopyArtifacts,
  applyToolActivitySnapshot,
  applyToolActivityStatus,
  applyToolsCatalog,
  applyToolGuide,
  defaultDesktopViewState,
  expandInspectorRunGroup,
  expandRunGroup,
  findLatestToolActivityForRun,
  groupRunInspectorItems,
  selectAnthropicConfig,
  selectProviderConfig,
  setConversationId,
  summarizeDesktopText,
  summarizeRunGroup,
  toggleInspectorRunGroupCollapsed,
  toggleRunGroupCollapsed,
} from "./state.js";
import { createMockTransport } from "./mock.js";
import {
  TauriEventPump,
  createPreferredTransport,
  createTauriBridgeCommands,
  detectTauriInvoke,
} from "./tauriTransport.js";

const sessionId = "desktop-preview";

const presenceLine = document.querySelector("#presence-line");
const windowLine = document.querySelector("#window-line");
const sessionLine = document.querySelector("#session-line");
const bridgeLine = document.querySelector("#bridge-line");
const providerLine = document.querySelector("#provider-line");
const consolePanel = document.querySelector("#console-panel");
const overviewSessionKicker = document.querySelector("#overview-session-kicker");
const overviewRuntimeSummary = document.querySelector("#overview-runtime-summary");
const overviewProviderSummary = document.querySelector("#overview-provider-summary");
const overviewActivitySummary = document.querySelector("#overview-activity-summary");
const overviewBridgePending = document.querySelector("#overview-bridge-pending");
const overviewBridgeEvents = document.querySelector("#overview-bridge-events");
const overviewMessageCount = document.querySelector("#overview-message-count");
const overviewApprovalCount = document.querySelector("#overview-approval-count");
const overviewBandBridgeNote = document.querySelector("#overview-band-bridge-note");
const providerStatusList = document.querySelector("#provider-status-list");
const settingsStatusLine = document.querySelector("#settings-status-line");
const settingsForm = document.querySelector("#settings-form");
const settingsSaveButton = document.querySelector("#settings-save-button");
const providerConfigStatusLine = document.querySelector("#provider-config-status-line");
const providerConfigForm = document.querySelector("#provider-config-form");
const providerConfigSaveButton = document.querySelector("#provider-config-save-button");
const providerConfigAddButton = document.querySelector("#provider-config-add-button");
const providerConfigRemoveButton = document.querySelector("#provider-config-remove-button");
const providerHeaderAddButton = document.querySelector("#provider-header-add-button");
const providerHeadersList = document.querySelector("#provider-headers-list");
const providerConfigSelect = document.querySelector("#provider-config-select");
const providerBackendInput = document.querySelector("#provider-backend-input");
const providerBaseUrlInput = document.querySelector("#provider-base-url-input");
const providerModelInput = document.querySelector("#provider-model-input");
const providerApiKeyEnvInput = document.querySelector("#provider-api-key-env-input");
const providerTimeoutInput = document.querySelector("#provider-timeout-input");
const providerHealthTimeoutInput = document.querySelector("#provider-health-timeout-input");
const providerTemperatureInput = document.querySelector("#provider-temperature-input");
const providerMaxTokensInput = document.querySelector("#provider-max-tokens-input");
const providerPresetButtons = document.querySelectorAll("[data-provider-preset]");
const anthropicConfigStatusLine = document.querySelector("#anthropic-config-status-line");
const anthropicConfigForm = document.querySelector("#anthropic-config-form");
const anthropicConfigSaveButton = document.querySelector("#anthropic-config-save-button");
const anthropicConfigAddButton = document.querySelector("#anthropic-config-add-button");
const anthropicConfigRemoveButton = document.querySelector("#anthropic-config-remove-button");
const anthropicHeaderAddButton = document.querySelector("#anthropic-header-add-button");
const anthropicHeadersList = document.querySelector("#anthropic-headers-list");
const anthropicConfigSelect = document.querySelector("#anthropic-config-select");
const anthropicBackendInput = document.querySelector("#anthropic-backend-input");
const anthropicBaseUrlInput = document.querySelector("#anthropic-base-url-input");
const anthropicModelInput = document.querySelector("#anthropic-model-input");
const anthropicApiKeyEnvInput = document.querySelector("#anthropic-api-key-env-input");
const anthropicVersionInput = document.querySelector("#anthropic-version-input");
const anthropicTimeoutInput = document.querySelector("#anthropic-timeout-input");
const anthropicHealthTimeoutInput = document.querySelector("#anthropic-health-timeout-input");
const anthropicTemperatureInput = document.querySelector("#anthropic-temperature-input");
const anthropicMaxTokensInput = document.querySelector("#anthropic-max-tokens-input");
const anthropicPresetButtons = document.querySelectorAll("[data-anthropic-preset]");
const providerOptions = document.querySelector("#provider-options");
const runInspectorStatusLine = document.querySelector("#run-inspector-status-line");
const runInspectorList = document.querySelector("#run-inspector-list");
const allowAllCmdStatusLine = document.querySelector("#allow-all-cmd-status-line");
const allowAllCmdToggle = document.querySelector("#allow-all-cmd-toggle");
const permissionCenterStatusLine = document.querySelector("#permission-center-status-line");
const permissionCenterRefreshButton = document.querySelector("#permission-center-refresh-button");
const permissionGrantsList = document.querySelector("#permission-grants-list");
const permissionAuditStatusLine = document.querySelector("#permission-audit-status-line");
const permissionAuditRefreshButton = document.querySelector("#permission-audit-refresh-button");
const permissionAuditList = document.querySelector("#permission-audit-list");
const parallelInspectStatusLine = document.querySelector("#parallel-inspect-status-line");
const parallelInspectForm = document.querySelector("#parallel-inspect-form");
const parallelInspectPathsInput = document.querySelector("#parallel-inspect-paths-input");
const parallelInspectStartLineInput = document.querySelector("#parallel-inspect-start-line-input");
const parallelInspectEndLineInput = document.querySelector("#parallel-inspect-end-line-input");
const parallelInspectResults = document.querySelector("#parallel-inspect-results");
const toolCatalogStatusLine = document.querySelector("#tool-catalog-status-line");
const toolCatalogList = document.querySelector("#tool-catalog-list");
const toolGuideStatusLine = document.querySelector("#tool-guide-status-line");
const toolGuideWorkflowList = document.querySelector("#tool-guide-workflow-list");
const toolGuideList = document.querySelector("#tool-guide-list");
const toolGuideCopyButton = document.querySelector("#tool-guide-copy-button");
const promptPreviewCopyButton = document.querySelector("#prompt-preview-copy-button");
const promptPreviewStatusLine = document.querySelector("#prompt-preview-status-line");
const promptPreviewContent = document.querySelector("#prompt-preview-content");
const agentBundleCopyButton = document.querySelector("#agent-bundle-copy-button");
const codexManifestCopyButton = document.querySelector("#codex-manifest-copy-button");
const agentBundleStatusLine = document.querySelector("#agent-bundle-status-line");
const agentBundleContent = document.querySelector("#agent-bundle-content");
const agentStarterPackCopyButton = document.querySelector("#agent-starter-pack-copy-button");
const agentStarterPackStatusLine = document.querySelector("#agent-starter-pack-status-line");
const agentStarterPackContent = document.querySelector("#agent-starter-pack-content");
const defaultProviderInput = document.querySelector("#default-provider-input");
const chatProviderInput = document.querySelector("#chat-provider-input");
const chatProfileInput = document.querySelector("#chat-profile-input");
const codingProviderInput = document.querySelector("#coding-provider-input");
const codingProfileInput = document.querySelector("#coding-profile-input");
const defaultPersonalityInput = document.querySelector("#default-personality-input");
const defaultSystemInput = document.querySelector("#default-system-input");
const codingPersonalityInput = document.querySelector("#coding-personality-input");
const codingSystemInput = document.querySelector("#coding-system-input");
const codingToolInput = document.querySelector("#coding-tool-input");
const codingResponseInput = document.querySelector("#coding-response-input");
const messageLog = document.querySelector("#message-log");
const avatarButton = document.querySelector("#avatar-button");
const closeConsoleButton = document.querySelector("#close-console-button");
const messageForm = document.querySelector("#message-form");
const messageInput = document.querySelector("#message-input");

let state = defaultDesktopViewState();
let eventPump = null;
let pendingRuntimeInfo = null;
let bridgeCommands = null;
let usingNativeBridge = false;
let client = null;

const OPENAI_COMPAT_PRESETS = {
  openai: {
    backend: "openai",
    base_url: "https://api.openai.com/v1",
    model: "gpt-4.1-mini",
    api_key_env: "OPENAI_API_KEY",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 2048,
    headers: {},
  },
  google: {
    backend: "google",
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai",
    model: "gemini-2.5-flash",
    api_key_env: "GEMINI_API_KEY",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 2048,
    headers: {},
  },
  openrouter: {
    backend: "openrouter",
    base_url: "https://openrouter.ai/api/v1",
    model: "openai/gpt-4.1-mini",
    api_key_env: "OPENROUTER_API_KEY",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 2048,
    headers: {},
  },
  ollama: {
    backend: "ollama",
    base_url: "http://127.0.0.1:11434/v1",
    model: "qwen2.5:7b-instruct",
    api_key_env: "",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.6,
    max_tokens: 1024,
    headers: {},
  },
  lmstudio: {
    backend: "lmstudio",
    base_url: "http://127.0.0.1:1234/v1",
    model: "local-model",
    api_key_env: "",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 1024,
    headers: {},
  },
  custom: {
    backend: "custom",
    base_url: "http://127.0.0.1:8080/v1",
    model: "Qwen3-4B-Q5_K_M.gguf",
    api_key_env: "",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 2048,
    headers: {},
  },
};

const ANTHROPIC_PRESETS = {
  claude: {
    backend: "anthropic",
    base_url: "https://api.anthropic.com",
    model: "claude-sonnet-4-20250514",
    api_key_env: "ANTHROPIC_API_KEY",
    anthropic_version: "2023-06-01",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.2,
    max_tokens: 2048,
    headers: {},
  },
};

const RISKY_AUDIT_CATEGORIES = [
  "permission.decision",
  "permission.grant.updated",
  "permission.capability_grant.updated",
  "permission.capability_grant.revoked",
  "approval.pending",
  "approval.responded",
  "tool.result",
];

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function waitForTauriInvoke(globalObject, { attempts = 20, intervalMs = 100 } = {}) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const invoke = detectTauriInvoke(globalObject);
    if (invoke) {
      return invoke;
    }
    await delay(intervalMs);
  }
  return null;
}

function render() {
  presenceLine.textContent = `${state.presence} / ${state.expression}`;
  windowLine.textContent = `anchor: ${state.windowAnchor} | hotkey: ${state.hotkey}`;
  sessionLine.textContent = `session: ${state.attachedSessionIds.join(", ") || "disconnected"}`;
  bridgeLine.textContent = `bridge: ${state.bridgeTransport} | core: ${state.bridgeProcessStarted ? "started" : "idle"}`;
  providerLine.textContent = state.providerHealthSummary;
  settingsStatusLine.textContent = state.settingsStatus;
  providerConfigStatusLine.textContent = state.providerConfigStatus;
  anthropicConfigStatusLine.textContent = state.anthropicConfigStatus;
  runInspectorStatusLine.textContent = describeRunInspectorStatus(state);
  allowAllCmdStatusLine.textContent = state.allowAllCmdStatus;
  permissionCenterStatusLine.textContent = state.capabilityGrantsStatus;
  permissionAuditStatusLine.textContent = state.auditPreviewStatus;
  parallelInspectStatusLine.textContent = state.parallelInspectStatus;
  toolCatalogStatusLine.textContent = state.toolCatalogStatus;
  toolGuideStatusLine.textContent = state.toolGuideStatus;
  promptPreviewStatusLine.textContent = state.promptPreviewStatus;
  agentBundleStatusLine.textContent = state.agentBundleStatus;
  agentStarterPackStatusLine.textContent = state.agentStarterPackStatus;
  allowAllCmdToggle.checked = Boolean(state.allowAllCmd);
  bridgeLine.title = state.bridgeLastError || state.bridgeNote;
  consolePanel.classList.toggle("hidden", !state.consoleOpen);

  const providerCount = state.providerHealth.length;
  const healthyCount = state.providerHealth.filter((item) => item.ok).length;
  overviewSessionKicker.textContent = state.attachedSessionIds.join(", ") || "Disconnected";
  overviewRuntimeSummary.textContent = state.bridgeProcessStarted
    ? "Bridge live and listening"
    : "Bridge idle";
  overviewProviderSummary.textContent =
    providerCount > 0
      ? `${healthyCount} of ${providerCount} providers healthy`
      : "No provider health loaded yet.";
  overviewActivitySummary.textContent = state.toolActivityStatus;
  overviewBridgePending.textContent = String(state.bridgePendingRequests || 0);
  overviewBridgeEvents.textContent = String(state.bridgeQueuedEvents || 0);
  overviewMessageCount.textContent = String(state.messages.length);
  overviewApprovalCount.textContent = String(state.pendingApprovals.length);
  overviewBandBridgeNote.textContent = state.bridgeLastError || state.bridgeNote;

  providerOptions.replaceChildren();
  for (const provider of state.availableProviders) {
    const option = document.createElement("option");
    option.value = provider;
    providerOptions.append(option);
  }

  providerStatusList.replaceChildren();
  for (const item of state.providerHealth) {
    const row = document.createElement("article");
    row.className = "provider-status-row";
    const head = document.createElement("div");
    head.className = "provider-status-head";
    const name = document.createElement("div");
    name.className = "provider-status-name";
    name.textContent = item.provider;
    const badge = document.createElement("div");
    badge.className = `provider-status-badge ${item.ok ? "ok" : "error"}`;
    badge.textContent = item.ok ? "online" : "offline";
    head.append(name, badge);
    const meta = document.createElement("div");
    meta.className = "provider-status-meta";
    meta.textContent = [
      item.backend || "unknown",
      item.model || null,
      item.model_available === false ? "selected model missing" : null,
      item.error || null,
    ]
      .filter(Boolean)
      .join(" | ");
    row.append(head, meta);
    providerStatusList.append(row);
  }

  const settings = state.conversationSettings;
  if (settings) {
    defaultProviderInput.value = settings.default_provider || "";
    chatProviderInput.value = settings.routes?.chat?.provider || "";
    chatProfileInput.value = settings.routes?.chat?.prompt_profile || "";
    codingProviderInput.value = settings.routes?.coding_agent?.provider || "";
    codingProfileInput.value = settings.routes?.coding_agent?.prompt_profile || "";
    defaultPersonalityInput.value =
      settings.prompt_profiles?.default?.personality || "";
    defaultSystemInput.value =
      settings.prompt_profiles?.default?.system_instruction || "";
    codingPersonalityInput.value =
      settings.prompt_profiles?.coding_agent?.personality || "";
    codingSystemInput.value =
      settings.prompt_profiles?.coding_agent?.system_instruction || "";
    codingToolInput.value =
      settings.prompt_profiles?.coding_agent?.tool_instruction || "";
      codingResponseInput.value =
      settings.prompt_profiles?.coding_agent?.response_instruction || "";
  }

  providerConfigSelect.replaceChildren();
  const providerConfigs = state.openaiCompatibleSettings?.providers || [];
  for (const item of providerConfigs) {
    const option = document.createElement("option");
    option.value = item.provider_name;
    option.textContent = item.provider_name;
    providerConfigSelect.append(option);
  }
  providerConfigSelect.value = state.selectedProviderConfigName;
  const selectedProviderConfig =
    providerConfigs.find((item) => item.provider_name === state.selectedProviderConfigName) ||
    null;
  providerBackendInput.value = selectedProviderConfig?.backend || "";
  providerBaseUrlInput.value = selectedProviderConfig?.base_url || "";
  providerModelInput.value = selectedProviderConfig?.model || "";
  providerApiKeyEnvInput.value = selectedProviderConfig?.api_key_env || "";
  providerTimeoutInput.value = String(selectedProviderConfig?.timeout_seconds ?? "");
  providerHealthTimeoutInput.value = String(
    selectedProviderConfig?.health_timeout_seconds ?? "",
  );
  providerTemperatureInput.value = String(selectedProviderConfig?.temperature ?? "");
  providerMaxTokensInput.value = String(selectedProviderConfig?.max_tokens ?? "");
  renderHeaderRows(providerHeadersList, selectedProviderConfig?.headers || {});

  anthropicConfigSelect.replaceChildren();
  const anthropicConfigs = state.anthropicMessagesSettings?.providers || [];
  for (const item of anthropicConfigs) {
    const option = document.createElement("option");
    option.value = item.provider_name;
    option.textContent = item.provider_name;
    anthropicConfigSelect.append(option);
  }
  anthropicConfigSelect.value = state.selectedAnthropicConfigName;
  const selectedAnthropicConfig =
    anthropicConfigs.find((item) => item.provider_name === state.selectedAnthropicConfigName) ||
    null;
  anthropicBackendInput.value = selectedAnthropicConfig?.backend || "";
  anthropicBaseUrlInput.value = selectedAnthropicConfig?.base_url || "";
  anthropicModelInput.value = selectedAnthropicConfig?.model || "";
  anthropicApiKeyEnvInput.value = selectedAnthropicConfig?.api_key_env || "";
  anthropicVersionInput.value = selectedAnthropicConfig?.anthropic_version || "";
  anthropicTimeoutInput.value = String(selectedAnthropicConfig?.timeout_seconds ?? "");
  anthropicHealthTimeoutInput.value = String(
    selectedAnthropicConfig?.health_timeout_seconds ?? "",
  );
  anthropicTemperatureInput.value = String(selectedAnthropicConfig?.temperature ?? "");
  anthropicMaxTokensInput.value = String(selectedAnthropicConfig?.max_tokens ?? "");
  renderHeaderRows(anthropicHeadersList, selectedAnthropicConfig?.headers || {});

  runInspectorList.replaceChildren();
  const runInspectorItems = buildRunInspectorItems(state);
  const runInspectorGroups = groupRunInspectorItems(runInspectorItems);
  if (runInspectorGroups.length === 0) {
    runInspectorList.append(renderRunInspectorEmptyState());
  }
  for (const group of runInspectorGroups) {
    runInspectorList.append(renderRunInspectorGroup(group));
  }

  permissionGrantsList.replaceChildren();
  const capabilityGrants = Array.isArray(state.capabilityGrants) ? state.capabilityGrants : [];
  if (capabilityGrants.length === 0) {
    const empty = document.createElement("div");
    empty.className = "console-note permission-empty";
    empty.textContent = "No scoped capability grants are active for this session.";
    permissionGrantsList.append(empty);
  }
  for (const grant of capabilityGrants) {
    permissionGrantsList.append(renderPermissionGrantRow(grant));
  }

  permissionAuditList.replaceChildren();
  const auditPreview = Array.isArray(state.auditPreview) ? state.auditPreview : [];
  if (auditPreview.length === 0) {
    const empty = document.createElement("div");
    empty.className = "console-note permission-empty";
    empty.textContent = "No recent risky actions are available yet.";
    permissionAuditList.append(empty);
  }
  for (const record of auditPreview) {
    permissionAuditList.append(renderPermissionAuditRow(record));
  }

  toolCatalogList.replaceChildren();
  for (const item of state.toolsCatalog) {
    const row = document.createElement("article");
    row.className = "tool-catalog-row";

    const head = document.createElement("div");
    head.className = "tool-catalog-head";

    const name = document.createElement("div");
    name.className = "tool-catalog-name";
    name.textContent = item.name || "unknown tool";

    const badges = document.createElement("div");
    badges.className = "tool-catalog-badges";
    badges.append(
      createToolBadge(item.output_kind || item.metadata?.output_kind || "structured"),
      createToolBadge(
        item.metadata?.parallel_safe ? "parallel_safe" : "sequential_only",
        item.metadata?.parallel_safe ? "safe" : "risky",
      ),
      createToolBadge(
        item.metadata?.mutates_state ? "mutates_state" : "read_only",
        item.metadata?.mutates_state ? "risky" : "safe",
      ),
    );

    head.append(name, badges);

    const description = document.createElement("div");
    description.className = "tool-catalog-description";
    description.textContent = item.description || "No description";

    const meta = document.createElement("div");
    meta.className = "tool-catalog-meta";
    meta.textContent = [
      item.capability || "no capability",
      item.risk || "unknown risk",
      item.plugin_id || "core",
    ].join(" | ");

    const contract = document.createElement("div");
    contract.className = "tool-catalog-contract";
    contract.textContent = describeToolContract(item);

    row.append(head, description, meta, contract);
    toolCatalogList.append(row);
  }

  toolGuideWorkflowList.replaceChildren();
  for (const step of state.toolGuide?.workflow || []) {
    const item = document.createElement("li");
    item.className = "tool-guide-workflow-item";
    item.textContent = step;
    toolGuideWorkflowList.append(item);
  }

  toolGuideList.replaceChildren();
  for (const item of state.toolGuide?.tools || []) {
    const row = document.createElement("article");
    row.className = "tool-guide-row";

    const head = document.createElement("div");
    head.className = "tool-catalog-head";

    const name = document.createElement("div");
    name.className = "tool-catalog-name";
    name.textContent = item.name || "unknown tool";

    const badges = document.createElement("div");
    badges.className = "tool-catalog-badges";
    badges.append(
      createToolBadge(item.output_kind || "structured"),
      createToolBadge(item.parallel_safe ? "parallel_safe" : "sequential_only", item.parallel_safe ? "safe" : "risky"),
      createToolBadge(item.mutates_state ? "mutates_state" : "read_only", item.mutates_state ? "risky" : "safe"),
    );
    head.append(name, badges);

    const summary = document.createElement("div");
    summary.className = "tool-catalog-description";
    summary.textContent = item.summary || "No summary";

    const whenToUse = document.createElement("div");
    whenToUse.className = "tool-guide-line";
    whenToUse.textContent = `Use when: ${item.when_to_use || "n/a"}`;

    const avoidWhen = document.createElement("div");
    avoidWhen.className = "tool-guide-line";
    avoidWhen.textContent = `Avoid when: ${item.avoid_when || "n/a"}`;

    row.append(head, summary, whenToUse, avoidWhen);
    toolGuideList.append(row);
  }
  promptPreviewContent.textContent =
    state.promptPreview?.system_instruction || "Runtime prompt unavailable.";
  agentBundleContent.textContent = state.agentBundle
    ? JSON.stringify(state.agentBundle, null, 2)
    : "Agent bundle unavailable.";
  agentStarterPackContent.textContent = state.agentStarterPack?.text || "Agent starter pack unavailable.";

  parallelInspectResults.replaceChildren();
  for (const item of state.parallelInspectResults) {
    const row = document.createElement("article");
    row.className = "parallel-inspect-row";

    const head = document.createElement("div");
    head.className = "parallel-inspect-head";

    const path = document.createElement("div");
    path.className = "parallel-inspect-path";
    path.textContent = item.path || item.tool_name || "unknown path";

    const badge = createToolBadge(
      item.status || "unknown",
      item.status === "succeeded" ? "safe" : "risky",
    );
    head.append(path, badge);

    const meta = document.createElement("div");
    meta.className = "parallel-inspect-meta";
    meta.textContent = [
      item.start_line && item.end_line
        ? `lines ${item.start_line}-${item.end_line}`
        : `lines ${item.start_line || "?"}-${item.end_line || "?"}`,
      item.total_lines ? `${item.returned_lines || 0}/${item.total_lines} returned` : null,
      item.truncated ? "truncated" : "full",
    ]
      .filter(Boolean)
      .join(" | ");

    const preview = document.createElement("pre");
    preview.className = "parallel-inspect-preview";
    preview.textContent = item.error || item.content || "No output";

    row.append(head, meta, preview);
    parallelInspectResults.append(row);
  }

  messageLog.replaceChildren();
  for (const group of buildMessageGroups(state.messages)) {
    const block = document.createElement("section");
    block.className = `message-group ${group.kind === "run" ? "is-run-group" : "is-loose-group"}`;
    if (group.kind === "run") {
      block.dataset.runId = group.run_id || "";
    }
    if (group.kind === "run") {
      const header = document.createElement("button");
      header.className = "message-group-header";
      header.type = "button";
      const collapsed = isRunGroupCollapsed(state, group.run_id);
      header.append(renderRunGroupHeader(group, collapsed));
      header.addEventListener("click", () => {
        state = toggleRunGroupCollapsed(state, group.run_id);
        render();
      });
      block.append(header);
      block.append(renderRunGroupSummary(group));
    }
    if (!isRunGroupCollapsed(state, group.run_id)) {
      for (const item of group.messages) {
        const row = renderMessageRow(item);
        block.append(row);
      }
    }
    messageLog.append(block);
  }
  messageLog.scrollTop = messageLog.scrollHeight;
}

function createJumpButton(label, message, selection) {
  const button = document.createElement("button");
  button.className = "ghost-button inline-button";
  button.type = "button";
  button.textContent = label;
  button.disabled = !message;
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    if (!message) {
      return;
    }
    focusInspectorSelection(
      buildInspectorSelection(selection, message.id),
      message.id,
    );
  });
  return button;
}

function buildRunInspectorItems(state) {
  const items = [];
  const seenApprovalIds = new Set();
  for (const toolItem of state.toolActivity) {
    const approval = state.pendingApprovals.find(
      (item) =>
        (toolItem.approval_id && item.approval_id === toolItem.approval_id) ||
        (toolItem.request_id && item.request_id === toolItem.request_id),
    );
    if (approval?.approval_id) {
      seenApprovalIds.add(approval.approval_id);
    }
    items.push({
      ...toolItem,
      kind: "tool_activity",
      approval_pending: Boolean(approval),
      approval_record: approval || null,
      reason: approval?.reason || toolItem.error || null,
      risk_level: approval?.risk_level || null,
      actor: approval?.actor || null,
      session_id: approval?.session_id || null,
      permission: normalizePermissionMetadata(toolItem),
    });
  }
  for (const approval of state.pendingApprovals) {
    if (approval.approval_id && seenApprovalIds.has(approval.approval_id)) {
      continue;
    }
    items.push({
      run_id: null,
      conversation_id: null,
      tool_call_id: null,
      request_id: approval.request_id || null,
      tool_name: approval.tool_name || "approval",
      arguments: approval.arguments || {},
      status: "waiting_approval",
      output: null,
      error: approval.reason || null,
      approval_id: approval.approval_id || null,
      kind: "approval_only",
      approval_pending: true,
      approval_record: approval,
      reason: approval.reason || null,
      risk_level: approval.risk_level || null,
      actor: approval.actor || null,
      session_id: approval.session_id || null,
      permission: null,
    });
  }
  return items;
}

function renderRunInspectorGroup(group) {
  const block = document.createElement("section");
  block.className = "run-inspector-group";

  if (group.kind === "run") {
    const collapsed = isInspectorRunGroupCollapsed(state, group.run_id);
    const header = document.createElement("button");
    header.className = "run-inspector-group-header";
    header.type = "button";
    header.append(renderRunInspectorGroupHeader(group, collapsed));
    header.addEventListener("click", () => {
      state = toggleInspectorRunGroupCollapsed(state, group.run_id);
      render();
    });
    block.append(header);
  }

  if (group.kind !== "run" || !isInspectorRunGroupCollapsed(state, group.run_id)) {
    const list = document.createElement("div");
    list.className = "run-inspector-group-list";
    for (const item of group.items) {
      list.append(renderRunInspectorItem(item));
    }
    block.append(list);
  }
  return block;
}

function renderRunInspectorGroupHeader(group, collapsed = false) {
  const row = document.createElement("div");
  row.className = "run-inspector-group-header-inner";

  const title = document.createElement("div");
  title.className = "run-inspector-group-title";
  title.textContent = `${collapsed ? "[+]" : "[-]"} run ${group.run_id}`;

  const toolCount = group.items.length;
  const pendingCount = group.items.filter((item) => item.approval_pending).length;
  const issueCount = group.items.filter((item) =>
    [
      "failed",
      "denied",
      "denied_by_user",
      "denied_by_profile",
      "denied_by_missing_scope",
      "denied_by_approval_unavailable",
      "denied_by_policy",
      "timed_out",
      "cancelled",
    ].includes(item.status),
  ).length;

  const badges = document.createElement("div");
  badges.className = "run-inspector-group-badges";
  badges.append(
    createToolBadge(`${toolCount} tool`, toolCount > 0 ? "neutral" : "safe"),
    createToolBadge(
      pendingCount > 0 ? `${pendingCount} pending` : "ready",
      pendingCount > 0 ? "neutral" : "safe",
    ),
    createToolBadge(
      issueCount > 0 ? `${issueCount} issue` : "clean",
      issueCount > 0 ? "risky" : "safe",
    ),
  );

  const actions = document.createElement("div");
  actions.className = "run-inspector-group-actions";

  const openRunButton = document.createElement("button");
  openRunButton.className = "ghost-button inline-button";
  openRunButton.type = "button";
  openRunButton.textContent = "Open run";
  openRunButton.addEventListener("click", (event) => {
    event.stopPropagation();
    focusMessageRunGroup(group.run_id);
  });

  actions.append(openRunButton);
  row.append(title, badges, actions);
  return row;
}

function renderRunInspectorEmptyState() {
  const row = document.createElement("div");
  row.className = "run-inspector-empty";
  row.textContent = "No tool activity or pending approval in this session.";
  return row;
}

function renderRunInspectorItem(item) {
  const row = document.createElement("article");
  const linkedToolResult = findToolResultMessage(state, item);
  const linkedAssistantTurn = findAssistantTurnMessage(state, item);
  const selection = buildInspectorSelection(item, linkedToolResult?.id || linkedAssistantTurn?.id);
  row.className = [
    "tool-activity-row",
    item.approval_pending ? "attention" : toolActivityToneClass(item.status),
    selectionMatchesInspector(state.inspectorSelection, item) ? "is-selected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const head = document.createElement("div");
  head.className = "tool-activity-head";

  const name = document.createElement("div");
  name.className = "tool-activity-name";
  name.textContent = item.tool_name || "unknown tool";

  const badge = createToolBadge(
    humanizeToolStatus(item.status || "unknown"),
    toolActivityTone(item.status),
  );
  const permission = normalizePermissionMetadata(item);
  head.append(name, badge);
  if (permission?.denial_category) {
    head.append(createToolBadge(humanizeDenialCategory(permission.denial_category), "risky"));
  }

  const meta = document.createElement("div");
  meta.className = "tool-activity-meta";
  meta.textContent = [
    item.run_id ? `run ${item.run_id}` : null,
    item.tool_call_id ? `call ${item.tool_call_id}` : null,
    item.request_id ? `request ${item.request_id}` : null,
    item.approval_id ? `approval ${item.approval_id}` : null,
    item.risk_level ? item.risk_level : null,
    item.actor ? item.actor : null,
    item.session_id ? item.session_id : null,
  ]
    .filter(Boolean)
    .join(" | ");

  const reason = document.createElement("div");
  reason.className = "approval-reason";
  reason.textContent = item.reason || "";
  reason.hidden = !item.reason;

  const preview = document.createElement("pre");
  preview.className = "tool-activity-preview";
  preview.textContent =
    item.error ||
    (item.output ? JSON.stringify(item.output, null, 2) : JSON.stringify(item.arguments || {}, null, 2));

  const permissionDetails = renderPermissionMetadataDetails(permission);

  const actions = document.createElement("div");
  actions.className = "inspector-actions";

  if (item.approval_pending && item.approval_id) {
    const approveButton = document.createElement("button");
    approveButton.className = "send-button";
    approveButton.type = "button";
    approveButton.textContent = "Approve";
    approveButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await respondToApproval(item.approval_id, true);
    });

    const denyButton = document.createElement("button");
    denyButton.className = "ghost-button";
    denyButton.type = "button";
    denyButton.textContent = "Deny";
    denyButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await respondToApproval(item.approval_id, false);
    });
    actions.append(approveButton, denyButton);
  }

  actions.append(
    createJumpButton("Assistant turn", linkedAssistantTurn, selection),
    createJumpButton("Tool result", linkedToolResult, selection),
  );

  row.addEventListener("click", () => {
    focusInspectorSelection(selection, linkedToolResult?.id || linkedAssistantTurn?.id);
  });

  row.append(head, meta, reason);
  if (permissionDetails) {
    row.append(permissionDetails);
  }
  row.append(preview, actions);
  return row;
}

function describeRunInspectorStatus(state) {
  const approvals = state.pendingApprovals.length;
  const toolCount = state.toolActivity.length;
  if (approvals > 0) {
    return `${state.toolActivityStatus} | ${approvals} approval${approvals === 1 ? "" : "s"} pending`;
  }
  if (toolCount > 0) {
    return state.toolActivityStatus;
  }
  return state.approvalStatus || state.toolActivityStatus;
}

function buildInspectorSelection(source = {}, messageId = null) {
  return {
    run_id: source.run_id || null,
    request_id: source.request_id || null,
    tool_call_id: source.tool_call_id || null,
    approval_id: source.approval_id || null,
    message_id: messageId || null,
  };
}

function selectionMatchesInspector(selection, item = {}) {
  if (!selection) {
    return false;
  }
  return Boolean(
    (selection.message_id && item.id && selection.message_id === item.id) ||
      (selection.request_id && item.request_id && selection.request_id === item.request_id) ||
      (selection.tool_call_id &&
        item.tool_call_id &&
        selection.tool_call_id === item.tool_call_id) ||
      (selection.approval_id && item.approval_id && selection.approval_id === item.approval_id) ||
      (selection.run_id && item.run_id && selection.run_id === item.run_id),
  );
}

function findToolResultMessage(state, refs = {}) {
  return [...state.messages]
    .reverse()
    .find(
      (message) =>
        message.kind === "tool_result" &&
        selectionMatchesInspector(buildInspectorSelection(refs), message),
    );
}

function findAssistantTurnMessage(state, refs = {}) {
  return [...state.messages]
    .reverse()
    .find(
      (message) =>
        message.role === "assistant" &&
        selectionMatchesInspector(buildInspectorSelection(refs), message),
    );
}

function buildMessageGroups(messages = []) {
  const groups = [];
  for (const message of messages) {
    if (message.run_id) {
      const existing = groups.find(
        (group) => group.kind === "run" && group.run_id === message.run_id,
      );
      if (existing) {
        existing.messages.push(message);
      } else {
        groups.push({ kind: "run", run_id: message.run_id, messages: [message] });
      }
      continue;
    }
    groups.push({
      kind: "loose",
      id: message.id || `loose-${groups.length}`,
      messages: [message],
    });
  }
  return groups;
}

function isRunGroupCollapsed(state, runId) {
  return Boolean(runId && (state.collapsedRunIds || []).includes(runId));
}

function describeRunGroupHeader(group, collapsed) {
  const summary = summarizeRunGroup(group);
  return [
    collapsed ? "[+]" : "[-]",
    `run ${group.run_id}`,
    `${summary.userCount} user`,
    `${summary.assistantCount} assistant`,
    `${summary.toolCount} tool`,
    summary.errorCount > 0 ? `${summary.errorCount} issue` : "clean",
  ].join(" | ");
}

function renderRunGroupHeader(group, collapsed) {
  const summary = summarizeRunGroup(group);
  const wrapper = document.createElement("div");
  wrapper.className = "message-group-header-inner";

  const title = document.createElement("div");
  title.className = "message-group-title";
  title.textContent = `${collapsed ? "[+]" : "[-]"} run ${group.run_id}`;

  const badges = document.createElement("div");
  badges.className = "message-group-badges";
  badges.append(
    createToolBadge(summary.outcome, runSummaryTone(summary.outcome)),
    createToolBadge(`${summary.userCount} user`),
    createToolBadge(`${summary.assistantCount} assistant`),
    createToolBadge(`${summary.toolCount} tool`, summary.toolCount > 0 ? "neutral" : "safe"),
    createToolBadge(
      summary.errorCount > 0 ? `${summary.errorCount} issue` : "clean",
      summary.errorCount > 0 ? "risky" : "safe",
    ),
  );
  wrapper.append(title, badges);
  return wrapper;
}

function renderRunGroupSummary(group) {
  const { summary, summaryText, assistantText, toolText, jsonText } = buildRunCopyArtifacts(group);
  const latestInspectorItem = findLatestToolActivityForRun(state.toolActivity, group.run_id);
  const row = document.createElement("div");
  row.className = "message-group-summary";

  const assistantPreview = document.createElement("div");
  assistantPreview.className = "message-group-summary-line";
  assistantPreview.textContent = summary.assistantPreviewText;

  const toolPreview = document.createElement("div");
  toolPreview.className = "message-group-summary-line";
  toolPreview.textContent = summary.toolPreviewText;

  const actions = document.createElement("div");
  actions.className = "message-group-summary-actions";

  const copySummaryButton = document.createElement("button");
  copySummaryButton.className = "ghost-button inline-button";
  copySummaryButton.type = "button";
  copySummaryButton.textContent = "Copy summary";
  copySummaryButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await copyRunPayload(summaryText, `Copied run ${group.run_id} summary`);
  });

  const focusInspectorButton = document.createElement("button");
  focusInspectorButton.className = "ghost-button inline-button";
  focusInspectorButton.type = "button";
  focusInspectorButton.textContent = "Focus inspector";
  focusInspectorButton.disabled = !latestInspectorItem;
  focusInspectorButton.addEventListener("click", (event) => {
    event.stopPropagation();
    focusInspectorSelection(buildInspectorSelection(latestInspectorItem || { run_id: group.run_id }), null);
  });

  const copyAnswerButton = document.createElement("button");
  copyAnswerButton.className = "ghost-button inline-button";
  copyAnswerButton.type = "button";
  copyAnswerButton.textContent = "Copy answer";
  copyAnswerButton.disabled = !assistantText;
  copyAnswerButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await copyRunPayload(assistantText, `Copied run ${group.run_id} answer`);
  });

  const copyToolButton = document.createElement("button");
  copyToolButton.className = "ghost-button inline-button";
  copyToolButton.type = "button";
  copyToolButton.textContent = "Copy tool result";
  copyToolButton.disabled = !toolText;
  copyToolButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await copyRunPayload(toolText, `Copied run ${group.run_id} tool result`);
  });

  const copyJsonButton = document.createElement("button");
  copyJsonButton.className = "ghost-button inline-button";
  copyJsonButton.type = "button";
  copyJsonButton.textContent = "Copy run JSON";
  copyJsonButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await copyRunPayload(jsonText, `Copied run ${group.run_id} JSON`);
  });

  actions.append(
    copySummaryButton,
    focusInspectorButton,
    copyAnswerButton,
    copyToolButton,
    copyJsonButton,
  );
  row.append(assistantPreview, toolPreview, actions);
  return row;
}

async function copyRunPayload(text, successStatus) {
  try {
    await writeClipboardText(text);
    state = applyToolActivityStatus(state, successStatus);
  } catch (error) {
    state = applyToolActivityStatus(
      state,
      `Copy failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function copyToolingPayload(
  text,
  successStatus,
  failurePrefix,
  applyStatus = applyPromptPreviewStatus,
) {
  try {
    await writeClipboardText(text);
    state = applyStatus(state, successStatus);
  } catch (error) {
    state = applyStatus(
      state,
      `${failurePrefix}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function writeClipboardText(text) {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  fallbackCopyText(text);
}

function fallbackCopyText(text) {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "true");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.append(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}

function runSummaryTone(outcome) {
  switch (outcome) {
    case "issues":
      return "risky";
    case "active":
      return "neutral";
    case "complete":
      return "safe";
    default:
      return "neutral";
  }
}

function describeRunGroupHeaderLegacy(group, collapsed) {
  const userCount = group.messages.filter((item) => item.role === "user").length;
  const assistantCount = group.messages.filter((item) => item.role === "assistant").length;
  const toolCount = group.messages.filter((item) => item.role === "tool").length;
  return [
    collapsed ? "[+]" : "[-]",
    `run ${group.run_id}`,
    `${userCount} user`,
    `${assistantCount} assistant`,
    `${toolCount} tool`,
  ].join(" | ");
}

function renderMessageRow(item) {
  const row = document.createElement("article");
  row.className = [
    `message-row role-${item.role}`,
    selectionMatchesInspector(state.inspectorSelection, item) ? "is-selected" : "",
  ]
    .filter(Boolean)
    .join(" ");
  row.dataset.messageId = item.id || "";

  const head = document.createElement("div");
  head.className = "message-head";

  const title = document.createElement("div");
  title.className = "message-role";
  title.textContent = item.tool_name ? `${item.role}: ${item.tool_name}` : item.role;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = [
    item.run_id ? `run ${item.run_id}` : null,
    item.tool_call_id ? `call ${item.tool_call_id}` : null,
    item.request_id ? `request ${item.request_id}` : null,
    item.status ? `status ${item.status}` : null,
  ]
    .filter(Boolean)
    .join(" | ");

  head.append(title, meta);

  const body = document.createElement("pre");
  body.className = "message-body";
  body.textContent = item.text || "";

  row.append(head, body);
  row.addEventListener("click", () => {
    focusInspectorSelection(buildInspectorSelection(item, item.id), item.id, { renderOnly: true });
  });
  return row;
}

function focusInspectorSelection(selection, messageId = null, options = {}) {
  if (selection?.run_id) {
    state = expandRunGroup(state, selection.run_id);
    state = expandInspectorRunGroup(state, selection.run_id);
  }
  state = applyInspectorSelection(state, selection);
  render();
  if (options.renderOnly || !messageId) {
    return;
  }
  queueMicrotask(() => {
    const target = messageId
      ? messageLog.querySelector(`[data-message-id="${messageId}"]`)
      : runInspectorList.querySelector(".tool-activity-row.is-selected");
    target?.scrollIntoView({ block: "center", behavior: "smooth" });
  });
}

function isInspectorRunGroupCollapsed(state, runId) {
  return Boolean(runId && (state.collapsedInspectorRunIds || []).includes(runId));
}

function focusMessageRunGroup(runId) {
  if (!runId) {
    return;
  }
  const latestInspectorItem = findLatestToolActivityForRun(state.toolActivity, runId);
  state = expandRunGroup(state, runId);
  state = expandInspectorRunGroup(state, runId);
  if (latestInspectorItem) {
    state = applyInspectorSelection(state, buildInspectorSelection(latestInspectorItem));
  }
  render();
  queueMicrotask(() => {
    const target = messageLog.querySelector(`[data-run-id="${runId}"]`);
    target?.scrollIntoView({ block: "center", behavior: "smooth" });
  });
}

function renderPermissionGrantRow(grant = {}) {
  const row = document.createElement("article");
  row.className = "permission-grant-row";

  const head = document.createElement("div");
  head.className = "permission-grant-head";

  const title = document.createElement("div");
  title.className = "permission-grant-title";
  title.textContent = grant.capability || "unknown capability";

  const badges = document.createElement("div");
  badges.className = "tool-catalog-badges";
  badges.append(
    createToolBadge(grant.allowed === false ? "denied" : "allowed", grant.allowed === false ? "risky" : "safe"),
    createToolBadge(grant.lifetime || "session"),
  );

  head.append(title, badges);

  const meta = document.createElement("div");
  meta.className = "permission-grant-meta";
  meta.textContent = [
    grant.resource ? `resource ${grant.resource}` : "resource *",
    grant.scope_id ? `scope ${grant.scope_id}` : null,
    grant.uses_remaining != null ? `uses ${grant.uses_remaining}` : null,
    grant.updated_by ? `by ${grant.updated_by}` : null,
  ]
    .filter(Boolean)
    .join(" | ");

  const actions = document.createElement("div");
  actions.className = "permission-grant-actions";
  const revokeButton = document.createElement("button");
  revokeButton.className = "ghost-button inline-button";
  revokeButton.type = "button";
  revokeButton.textContent = "Revoke";
  revokeButton.addEventListener("click", async () => {
    await revokeCapabilityGrant(grant);
  });
  actions.append(revokeButton);

  row.append(head, meta, actions);
  return row;
}

function renderPermissionAuditRow(record = {}) {
  const row = document.createElement("article");
  row.className = "permission-audit-row";

  const head = document.createElement("div");
  head.className = "permission-grant-head";

  const title = document.createElement("div");
  title.className = "permission-grant-title";
  title.textContent = record.category || "audit";

  const badges = document.createElement("div");
  badges.className = "tool-catalog-badges";
  badges.append(createToolBadge(auditRecordToneLabel(record), auditRecordTone(record)));
  const permission = auditPermissionMetadata(record);
  if (permission?.resource_scope) {
    badges.append(createToolBadge(formatResourceScope(permission.resource_scope), "neutral"));
  }
  head.append(title, badges);

  const meta = document.createElement("div");
  meta.className = "permission-grant-meta";
  meta.textContent = [
    formatAuditTimestamp(record.timestamp),
    describeAuditRecord(record),
  ]
    .filter(Boolean)
    .join(" | ");

  const permissionDetails = renderPermissionMetadataDetails(permission);

  row.append(head, meta);
  if (permissionDetails) {
    row.append(permissionDetails);
  }
  return row;
}

function auditRecordTone(record = {}) {
  const category = record.category || "";
  const data = record.data || {};
  if (category === "tool.result" && data.status && data.status !== "succeeded") {
    return "risky";
  }
  if (category === "permission.decision" && data.outcome && data.outcome !== "allow") {
    return "risky";
  }
  if (category.includes("revoked")) {
    return "neutral";
  }
  return "safe";
}

function auditRecordToneLabel(record = {}) {
  const data = record.data || {};
  const permission = auditPermissionMetadata(record);
  return permission?.denial_category || data.denial_category || data.status || data.outcome || "record";
}

function describeAuditRecord(record = {}) {
  const data = record.data || {};
  if (record.category === "permission.decision") {
    const scope = data.resource_scope
      ? `${data.resource_scope.kind || "resource"}:${data.resource_scope.value || "*"}`
      : null;
    return [
      data.tool || "tool",
      data.outcome || "unknown",
      data.denial_category || null,
      scope,
      data.reason || null,
    ].filter(Boolean).join(" / ");
  }
  if (record.category === "tool.result") {
    const permission = auditPermissionMetadata(record);
    return [
      data.tool || "tool",
      data.status || "unknown",
      permission?.denial_category || null,
      permission?.resource_scope ? formatResourceScope(permission.resource_scope) : null,
      data.error || null,
    ].filter(Boolean).join(" / ");
  }
  if (record.category?.startsWith("permission.capability_grant")) {
    const grants = Array.isArray(data.capability_grants) ? data.capability_grants.length : 0;
    return `${data.session_id || "session"} / ${grants} scoped grant${grants === 1 ? "" : "s"}`;
  }
  if (record.category?.startsWith("approval.")) {
    return [
      data.tool_name || data.approval_id || "approval",
      data.approved === undefined ? null : data.approved ? "approved" : "denied",
      data.reason || null,
    ].filter(Boolean).join(" / ");
  }
  return summarizeDesktopText(JSON.stringify(data), 140);
}

function auditPermissionMetadata(record = {}) {
  const data = record.data || {};
  if (record.category === "permission.decision") {
    return normalizePermissionMetadata({
      permission: {
        outcome: data.outcome || null,
        reason: data.reason || null,
        rule_id: data.rule_id || null,
        denial_category: data.denial_category || null,
        resource_scope: data.resource_scope || null,
      },
    });
  }
  return normalizePermissionMetadata(data);
}

function normalizePermissionMetadata(source = {}) {
  const permission = source?.permission || source?.metadata?.permission || null;
  if (!permission || typeof permission !== "object") {
    return null;
  }
  const resourceScope =
    permission.resource_scope && typeof permission.resource_scope === "object"
      ? {
          kind: permission.resource_scope.kind || "resource",
          value: permission.resource_scope.value ?? "*",
        }
      : null;
  return {
    outcome: permission.outcome || null,
    reason: permission.reason || null,
    rule_id: permission.rule_id || null,
    denial_category: permission.denial_category || null,
    resource_scope: resourceScope,
  };
}

function renderPermissionMetadataDetails(permission) {
  if (!permission) {
    return null;
  }
  const parts = [
    permission.denial_category ? humanizeDenialCategory(permission.denial_category) : null,
    permission.outcome ? `outcome ${permission.outcome}` : null,
    permission.resource_scope ? `scope ${formatResourceScope(permission.resource_scope)}` : null,
    permission.rule_id ? `rule ${permission.rule_id}` : null,
  ].filter(Boolean);
  if (parts.length === 0 && !permission.reason) {
    return null;
  }
  const details = document.createElement("div");
  details.className = "permission-denial-details";

  const chips = document.createElement("div");
  chips.className = "permission-denial-chips";
  for (const part of parts) {
    chips.append(createToolBadge(part, "neutral"));
  }

  const reason = document.createElement("div");
  reason.className = "permission-denial-reason";
  reason.textContent = permission.reason || "Permission decision metadata";

  details.append(chips, reason);
  return details;
}

function formatResourceScope(scope = {}) {
  if (!scope || typeof scope !== "object") {
    return "";
  }
  return `${scope.kind || "resource"}:${scope.value ?? "*"}`;
}

function humanizeDenialCategory(category = "") {
  switch (category) {
    case "denied_by_user":
      return "denied by user";
    case "denied_by_missing_scope":
      return "missing scope";
    case "denied_by_approval_unavailable":
      return "approval unavailable";
    case "denied_by_policy":
      return "policy blocked";
    default:
      return category || "denied";
  }
}

function formatAuditTimestamp(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function createToolBadge(text, tone = "neutral") {
  const badge = document.createElement("span");
  badge.className = `tool-badge ${tone}`;
  badge.textContent = text;
  return badge;
}

function toolActivityTone(status) {
  if (status === "succeeded" || status === "completed") {
    return "safe";
  }
  if (
    status === "requested" ||
    status === "running" ||
    status === "waiting_approval" ||
    status === "approved_pending_run"
  ) {
    return "neutral";
  }
  return "risky";
}

function toolActivityToneClass(status) {
  if (status === "waiting_approval" || status === "approved_pending_run") {
    return "attention";
  }
  if (
    status === "denied_by_user" ||
    status === "denied_by_profile" ||
    status === "denied_by_missing_scope" ||
    status === "denied_by_approval_unavailable" ||
    status === "denied_by_policy" ||
    status === "failed"
  ) {
    return "blocked";
  }
  return "";
}

function humanizeToolStatus(status) {
  switch (status) {
    case "waiting_approval":
      return "waiting approval";
    case "approved_pending_run":
      return "approved";
    case "denied_by_user":
      return "denied by user";
    case "denied_by_profile":
      return "blocked by profile";
    case "denied_by_missing_scope":
      return "missing scope";
    case "denied_by_approval_unavailable":
      return "approval unavailable";
    case "denied_by_policy":
      return "policy blocked";
    default:
      return status;
  }
}

function describeToolContract(tool) {
  const parts = [];
  if (tool.metadata?.parallel_safe) {
    parts.push("Safe to batch with other read-only parallel-safe tools.");
  } else {
    parts.push("Run sequentially.");
  }
  if (tool.metadata?.mutates_state) {
    parts.push("Changes state or host environment.");
  } else {
    parts.push("Read-only from runtime perspective.");
  }
  if (tool.name === "shell.run" || tool.name === "shell.session" || tool.name === "shell.exec") {
    parts.push("Model shell use in `assist` can be session-granted by `allow-all-cmd`; `observe` stays blocked.");
  }
  return parts.join(" ");
}

function renderHeaderRows(container, headers = {}) {
  container.replaceChildren();
  const entries = Object.entries(headers);
  if (entries.length === 0) {
    container.append(createHeaderRow("", ""));
    return;
  }
  for (const [name, value] of entries) {
    container.append(createHeaderRow(name, value));
  }
}

function createHeaderRow(name = "", value = "") {
  const row = document.createElement("div");
  row.className = "header-row";

  const nameInput = document.createElement("input");
  nameInput.className = "message-input";
  nameInput.placeholder = "Header name";
  nameInput.value = name;
  nameInput.dataset.headerField = "name";

  const valueInput = document.createElement("input");
  valueInput.className = "message-input";
  valueInput.placeholder = "Header value";
  valueInput.value = value;
  valueInput.dataset.headerField = "value";

  const removeButton = document.createElement("button");
  removeButton.className = "ghost-button inline-button";
  removeButton.type = "button";
  removeButton.textContent = "Remove";
  removeButton.addEventListener("click", () => {
    row.remove();
  });

  row.append(nameInput, valueInput, removeButton);
  return row;
}

function readHeaders(container) {
  const headers = {};
  const rows = container.querySelectorAll(".header-row");
  for (const row of rows) {
    const name = row.querySelector('[data-header-field="name"]')?.value.trim() || "";
    const value = row.querySelector('[data-header-field="value"]')?.value || "";
    if (name) {
      headers[name] = value;
    }
  }
  return headers;
}

function applyProviderPreset(preset) {
  if (!preset) {
    return;
  }
  providerBackendInput.value = preset.backend || "";
  providerBaseUrlInput.value = preset.base_url || "";
  providerModelInput.value = preset.model || "";
  providerApiKeyEnvInput.value = preset.api_key_env || "";
  providerTimeoutInput.value = String(preset.timeout_seconds ?? "");
  providerHealthTimeoutInput.value = String(preset.health_timeout_seconds ?? "");
  providerTemperatureInput.value = String(preset.temperature ?? "");
  providerMaxTokensInput.value = String(preset.max_tokens ?? "");
  renderHeaderRows(providerHeadersList, preset.headers || {});
}

function applyAnthropicPreset(preset) {
  if (!preset) {
    return;
  }
  anthropicBackendInput.value = preset.backend || "";
  anthropicBaseUrlInput.value = preset.base_url || "";
  anthropicModelInput.value = preset.model || "";
  anthropicApiKeyEnvInput.value = preset.api_key_env || "";
  anthropicVersionInput.value = preset.anthropic_version || "";
  anthropicTimeoutInput.value = String(preset.timeout_seconds ?? "");
  anthropicHealthTimeoutInput.value = String(preset.health_timeout_seconds ?? "");
  anthropicTemperatureInput.value = String(preset.temperature ?? "");
  anthropicMaxTokensInput.value = String(preset.max_tokens ?? "");
  renderHeaderRows(anthropicHeadersList, preset.headers || {});
}

function readParallelInspectCalls() {
  const paths = parallelInspectPathsInput.value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
  const startLineRaw = parallelInspectStartLineInput.value.trim();
  const endLineRaw = parallelInspectEndLineInput.value.trim();
  const startLine = startLineRaw ? Number(startLineRaw) : null;
  const endLine = endLineRaw ? Number(endLineRaw) : null;
  return paths.map((path) => {
    const args = { path };
    if (Number.isFinite(startLine) && startLine > 0) {
      args.start_line = startLine;
    }
    if (Number.isFinite(endLine) && endLine > 0) {
      args.end_line = endLine;
    }
    return {
      name: "workspace.read",
      arguments: args,
    };
  });
}

async function bootstrap() {
  const fallbackTransport = window.__YUE_TRANSPORT__ || createMockTransport();
  const tauriInvoke = await waitForTauriInvoke(window);
  bridgeCommands = tauriInvoke ? createTauriBridgeCommands({ invoke: tauriInvoke }) : null;
  usingNativeBridge = Boolean(bridgeCommands);
  client = new CoreProtocolClient(
    tauriInvoke ? createPreferredTransport(window, fallbackTransport) : fallbackTransport,
  );

  if (bridgeCommands) {
    pendingRuntimeInfo = await bridgeCommands.runtimeInfo();
    state = applyBridgeRuntime(state, pendingRuntimeInfo);
    eventPump = new TauriEventPump({
      commands: bridgeCommands,
      onEvent(event) {
        state = applyCoreEvent(state, event);
        render();
      },
    });
    eventPump.start();
  }
  const snapshot = await client.desktopState();
  state = applyDesktopSnapshot(state, snapshot);
  const attached = await client.desktopAttach(sessionId, { surface: "preview" });
  state = applyDesktopSnapshot(state, attached.state);
  state = applyProviderNames(state, await client.listProviders());
  state = applyProviderHealth(state, await client.providersHealth());
  state = applyConversationSettings(state, await client.getConversationSettings());
  state = applyOpenAICompatibleSettings(state, await client.getOpenAICompatibleSettings());
  state = applyAnthropicMessagesSettings(state, await client.getAnthropicMessagesSettings());
  state = applyPendingApprovals(state, await client.listPendingApprovals());
  state = applyToolActivitySnapshot(state, await client.getToolActivitySnapshot());
  state = applyToolsCatalog(state, await client.listTools());
  state = applyToolGuide(state, await client.getToolsGuide({ providerRole: "coding_agent" }));
  state = applyPromptPreview(state, await client.getConversationPromptPreview({ providerRole: "coding_agent" }));
  state = applyAgentBundle(state, await client.getAgentBundle({ providerRole: "coding_agent" }));
  state = applyAgentStarterPack(state, await client.getAgentStarterPack({ providerRole: "coding_agent" }));
  state = applyAllowAllCmdGrant(state, await client.getAllowAllCmd(sessionId));
  state = applyCapabilityGrants(state, await client.getCapabilityGrants(sessionId));
  state = applyAuditPreview(state, await client.getRecentAudit({
    limit: 8,
    categories: RISKY_AUDIT_CATEGORIES,
  }));
  if (bridgeCommands) {
    pendingRuntimeInfo = await bridgeCommands.runtimeInfo();
    state = applyBridgeRuntime(state, pendingRuntimeInfo);
  }
  render();
  if (bridgeCommands && pendingRuntimeInfo?.diagnostic_enabled) {
    await bridgeCommands.reportDiagnostic({
      readyState: document.readyState,
      hasTauri: typeof window.__TAURI__ !== "undefined",
      hasInternals: typeof window.__TAURI_INTERNALS__ !== "undefined",
      hasInvoke: typeof window.__TAURI_INTERNALS__?.invoke === "function",
      hasIpc: typeof window.__TAURI_INTERNALS__?.ipc === "function",
      bridgeLine: bridgeLine.textContent,
      autoExitMs: pendingRuntimeInfo.diagnostic_auto_exit_ms ?? null,
    });
    await bridgeCommands.shutdownCore();
  }
}

async function submitParallelInspect() {
  const calls = readParallelInspectCalls();
  if (calls.length === 0) {
    state = applyParallelInspectStatus(state, "Add at least one workspace path");
    render();
    return;
  }
  state = applyParallelInspectStatus(
    state,
    `Running parallel inspect for ${calls.length} path${calls.length === 1 ? "" : "s"}...`,
  );
  render();
  try {
    const result = await client.invokeMany(calls, {
      parallel: true,
      actor: "desktop-ui",
      sessionId,
    });
    const inspectResults = (result.results || []).map((item) => ({
      tool_name: item.tool_name,
      status: item.status,
      path: item.output?.path || "",
      content: item.output?.content || "",
      start_line: item.output?.start_line || null,
      end_line: item.output?.end_line || null,
      total_lines: item.output?.total_lines || null,
      returned_lines: item.output?.returned_lines || null,
      truncated: Boolean(item.output?.truncated),
      error: item.error || "",
    }));
    state = applyParallelInspectResults(state, inspectResults);
    const sections = (result.results || []).map((item) => {
      const output = item.output || {};
      return `# ${output.path || item.tool_name}\n${output.content || JSON.stringify(output, null, 2)}`;
    });
    state = appendMessage(
      state,
      createMessage("assistant", sections.join("\n\n")),
    );
    state = applyParallelInspectStatus(
      state,
      `Parallel inspect completed for ${calls.length} path${calls.length === 1 ? "" : "s"}`,
    );
  } catch (error) {
    state = applyParallelInspectStatus(
      state,
      `Parallel inspect failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function updateAllowAllCmd(allowed) {
  state = applyAllowAllCmdStatus(
    state,
    `${allowed ? "Enabling" : "Disabling"} session shell grant...`,
  );
  render();
  try {
    const grant = await client.setAllowAllCmd(sessionId, allowed, "desktop-ui");
    state = applyAllowAllCmdGrant(state, grant);
    await refreshAuditPreview();
  } catch (error) {
    allowAllCmdToggle.checked = !allowed;
    state = applyAllowAllCmdStatus(
      state,
      `Shell grant update failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function refreshCapabilityGrants() {
  state = applyCapabilityGrantsStatus(state, "Refreshing scoped grants...");
  render();
  try {
    const grant = await client.getCapabilityGrants(sessionId);
    state = applyCapabilityGrants(state, grant);
  } catch (error) {
    state = applyCapabilityGrantsStatus(
      state,
      `Grant refresh failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function refreshAuditPreview() {
  state = applyAuditPreviewStatus(state, "Refreshing audit preview...");
  render();
  try {
    const records = await client.getRecentAudit({
      limit: 8,
      categories: RISKY_AUDIT_CATEGORIES,
    });
    state = applyAuditPreview(state, records);
  } catch (error) {
    state = applyAuditPreviewStatus(
      state,
      `Audit refresh failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function revokeCapabilityGrant(grant = {}) {
  state = applyCapabilityGrantsStatus(
    state,
    `Revoking ${grant.capability || "capability grant"}...`,
  );
  render();
  try {
    const updated = await client.revokeCapabilityGrant(sessionId, {
      grantId: grant.id,
      capability: grant.capability,
      resource: grant.resource,
      actor: "desktop-ui",
    });
    state = applyCapabilityGrants(state, updated);
    await refreshAuditPreview();
  } catch (error) {
    state = applyCapabilityGrantsStatus(
      state,
      `Grant revoke failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function toggleConsole(command) {
  const payload = await client.desktopCommand(command, undefined, sessionId);
  state = applyDesktopSnapshot(state, payload.state);
  render();
}

async function sendMessage(text) {
  state = appendMessage(state, {
    ...createMessage("user", text),
    kind: "user_turn",
    conversation_id: state.conversationId,
  });
  render();
  await client.desktopCommand("presence.set", "thinking", sessionId);
  state = applyDesktopSnapshot(state, (await client.desktopState()));
  render();
  const response = await client.startAgentRun(text, {
    conversationId: state.conversationId,
    providerRole: "coding_agent",
    actor: "desktop-ui",
    metadata: { surface: "desktop-shell" },
  });
  const run = response.run || {};
  const runId = run.id || response.run_id || response.message?.metadata?.run_id || null;
  const conversationId = run.conversation_id || response.conversation_id || state.conversationId || null;
  if (conversationId && conversationId !== state.conversationId) {
    state = setConversationId(state, conversationId);
  }
  state = linkLatestUserMessageToRun(state, runId, conversationId);
  if (response.tool_activity) {
    state = applyToolActivitySnapshot(state, response.tool_activity);
  }
  if (!usingNativeBridge) {
    state = appendMessage(state, {
      role: "assistant",
      text: response.message?.text || response.message?.content || "",
      kind: "assistant_turn",
      run_id: runId,
      conversation_id: conversationId,
    });
  }
  const after = await client.desktopCommand("presence.set", "idle", sessionId);
  state = applyDesktopSnapshot(state, after.state);
  render();
}

async function respondToApproval(approvalId, approved) {
  state = applyApprovalStatus(
    state,
    `${approved ? "Approving" : "Denying"} ${approvalId}...`,
  );
  render();
  try {
    state = applyToolActivityStatus(state, approved ? "Approving tool..." : "Denying tool...");
    const response = await client.respondApproval(approvalId, approved);
    state = applyApprovalResponse(state, approvalId);
    state = applyCoreEvent(state, {
      topic: "approval.responded",
      payload: response,
    });
    state = applyApprovalStatus(
      state,
      approved ? "Approval granted" : "Approval denied",
    );
  } catch (error) {
    state = applyApprovalStatus(
      state,
      `Approval update failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

function readConversationSettingsPayload() {
  return {
    default_provider: defaultProviderInput.value.trim(),
    routes: {
      chat: {
        provider: chatProviderInput.value.trim(),
        prompt_profile: chatProfileInput.value.trim(),
      },
      coding_agent: {
        provider: codingProviderInput.value.trim(),
        prompt_profile: codingProfileInput.value.trim(),
      },
    },
    prompt_profiles: {
      default: {
        personality: defaultPersonalityInput.value,
        system_instruction: defaultSystemInput.value,
        tool_instruction: state.conversationSettings?.prompt_profiles?.default?.tool_instruction || "",
        response_instruction:
          state.conversationSettings?.prompt_profiles?.default?.response_instruction || "",
      },
      coding_agent: {
        personality: codingPersonalityInput.value,
        system_instruction: codingSystemInput.value,
        tool_instruction: codingToolInput.value,
        response_instruction: codingResponseInput.value,
      },
    },
  };
}

async function submitConversationSettings({ persist = false } = {}) {
  const payload = readConversationSettingsPayload();
  state = applySettingsStatus(
    state,
    persist ? "Saving settings to config..." : "Applying runtime settings...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveConversationSettings(payload)
      : await client.updateConversationSettings(payload);
    state = applyConversationSettings(state, updated);
    state = applySettingsStatus(
      state,
      persist ? "Settings saved to config" : "Runtime settings applied",
    );
  } catch (error) {
    state = applySettingsStatus(
      state,
      `${persist ? "Save" : "Update"} failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

function readOpenAICompatiblePayload() {
  const current = state.openaiCompatibleSettings?.providers || [];
  const selectedName = providerConfigSelect.value.trim();
  return {
    providers: current.map((item) =>
      item.provider_name === selectedName
        ? {
            ...item,
            provider_name: selectedName,
            backend: providerBackendInput.value.trim(),
            base_url: providerBaseUrlInput.value.trim(),
            model: providerModelInput.value.trim(),
            api_key_env: providerApiKeyEnvInput.value.trim(),
            timeout_seconds: Number(providerTimeoutInput.value),
            health_timeout_seconds: Number(providerHealthTimeoutInput.value),
            temperature: Number(providerTemperatureInput.value),
            max_tokens: Number(providerMaxTokensInput.value),
            headers: readHeaders(providerHeadersList),
          }
        : item,
    ),
  };
}

async function submitOpenAICompatibleSettings({ persist = false } = {}) {
  const payload = readOpenAICompatiblePayload();
  state = applyProviderConfigStatus(
    state,
    persist ? "Saving provider config..." : "Applying provider config...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveOpenAICompatibleSettings(payload)
      : await client.updateOpenAICompatibleSettings(payload);
    state = applyOpenAICompatibleSettings(state, updated);
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
    state = applyProviderConfigStatus(
      state,
      persist ? "Provider config saved" : "Provider config applied",
    );
  } catch (error) {
    state = applyProviderConfigStatus(
      state,
      `${persist ? "Save" : "Update"} failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

function createOpenAICompatibleProviderDraft() {
  const existing = new Set(
    (state.openaiCompatibleSettings?.providers || []).map((item) => item.provider_name),
  );
  let index = existing.size + 1;
  let providerName = `custom.provider.${index}`;
  while (existing.has(providerName)) {
    index += 1;
    providerName = `custom.provider.${index}`;
  }
  return {
    provider_name: providerName,
    backend: "custom",
    base_url: "http://127.0.0.1:8080/v1",
      model: "Qwen3-4B-Q5_K_M.gguf",
    api_key_env: "",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 1024,
    headers: {},
  };
}

function createAnthropicProviderDraft() {
  const existing = new Set(
    (state.anthropicMessagesSettings?.providers || []).map((item) => item.provider_name),
  );
  let index = existing.size + 1;
  let providerName = `claude.provider.${index}`;
  while (existing.has(providerName)) {
    index += 1;
    providerName = `claude.provider.${index}`;
  }
  return {
    provider_name: providerName,
    backend: "anthropic",
    base_url: "https://api.anthropic.com",
    model: "claude-sonnet-4-20250514",
    api_key_env: "ANTHROPIC_API_KEY",
    anthropic_version: "2023-06-01",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.2,
    max_tokens: 2048,
    headers: {},
  };
}

async function addOpenAICompatibleProvider({ persist = false } = {}) {
  const current = state.openaiCompatibleSettings?.providers || [];
  const draft = createOpenAICompatibleProviderDraft();
  state = selectProviderConfig(state, draft.provider_name);
  state = applyProviderConfigStatus(
    state,
    persist ? "Adding provider and saving..." : "Adding provider...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveOpenAICompatibleSettings({ providers: [...current, draft] })
      : await client.updateOpenAICompatibleSettings({ providers: [...current, draft] });
    state = applyOpenAICompatibleSettings(state, updated);
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
    state = applyProviderConfigStatus(
      state,
      persist ? "Provider added and saved" : "Provider added",
    );
  } catch (error) {
    state = applyProviderConfigStatus(
      state,
      `Add failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function removeOpenAICompatibleProvider({ persist = false } = {}) {
  const current = state.openaiCompatibleSettings?.providers || [];
  const selectedName = providerConfigSelect.value.trim();
  const remaining = current.filter((item) => item.provider_name !== selectedName);
  if (remaining.length === current.length) {
    return;
  }
  if (remaining.length === 0) {
    state = applyProviderConfigStatus(
      state,
      "Remove failed: at least one provider must remain",
    );
    render();
    return;
  }
  state = selectProviderConfig(state, remaining[0].provider_name);
  state = applyProviderConfigStatus(
    state,
    persist ? "Removing provider and saving..." : "Removing provider...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveOpenAICompatibleSettings({ providers: remaining })
      : await client.updateOpenAICompatibleSettings({ providers: remaining });
    state = applyOpenAICompatibleSettings(state, updated);
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
    state = applyProviderConfigStatus(
      state,
      persist ? "Provider removed and saved" : "Provider removed",
    );
  } catch (error) {
    state = applyProviderConfigStatus(
      state,
      `Remove failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

function readAnthropicMessagesPayload() {
  const current = state.anthropicMessagesSettings?.providers || [];
  const selectedName = anthropicConfigSelect.value.trim();
  return {
    providers: current.map((item) =>
      item.provider_name === selectedName
        ? {
            ...item,
            provider_name: selectedName,
            backend: anthropicBackendInput.value.trim(),
            base_url: anthropicBaseUrlInput.value.trim(),
            model: anthropicModelInput.value.trim(),
            api_key_env: anthropicApiKeyEnvInput.value.trim(),
            anthropic_version: anthropicVersionInput.value.trim(),
            timeout_seconds: Number(anthropicTimeoutInput.value),
            health_timeout_seconds: Number(anthropicHealthTimeoutInput.value),
            temperature: Number(anthropicTemperatureInput.value),
            max_tokens: Number(anthropicMaxTokensInput.value),
            headers: readHeaders(anthropicHeadersList),
          }
        : item,
    ),
  };
}

async function submitAnthropicMessagesSettings({ persist = false } = {}) {
  const payload = readAnthropicMessagesPayload();
  state = applyAnthropicConfigStatus(
    state,
    persist ? "Saving Anthropic config..." : "Applying Anthropic config...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveAnthropicMessagesSettings(payload)
      : await client.updateAnthropicMessagesSettings(payload);
    state = applyAnthropicMessagesSettings(state, updated);
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
    state = applyAnthropicConfigStatus(
      state,
      persist ? "Anthropic config saved" : "Anthropic config applied",
    );
  } catch (error) {
    state = applyAnthropicConfigStatus(
      state,
      `${persist ? "Save" : "Update"} failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function addAnthropicProvider({ persist = false } = {}) {
  const current = state.anthropicMessagesSettings?.providers || [];
  const draft = createAnthropicProviderDraft();
  state = selectAnthropicConfig(state, draft.provider_name);
  state = applyAnthropicConfigStatus(
    state,
    persist ? "Adding Anthropic provider and saving..." : "Adding Anthropic provider...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveAnthropicMessagesSettings({ providers: [...current, draft] })
      : await client.updateAnthropicMessagesSettings({ providers: [...current, draft] });
    state = applyAnthropicMessagesSettings(state, updated);
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
    state = applyAnthropicConfigStatus(
      state,
      persist ? "Anthropic provider added and saved" : "Anthropic provider added",
    );
  } catch (error) {
    state = applyAnthropicConfigStatus(
      state,
      `Add failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

async function removeAnthropicProvider({ persist = false } = {}) {
  const current = state.anthropicMessagesSettings?.providers || [];
  const selectedName = anthropicConfigSelect.value.trim();
  const remaining = current.filter((item) => item.provider_name !== selectedName);
  if (remaining.length === current.length) {
    return;
  }
  if (remaining.length === 0) {
    state = applyAnthropicConfigStatus(
      state,
      "Remove failed: at least one provider must remain",
    );
    render();
    return;
  }
  state = selectAnthropicConfig(state, remaining[0].provider_name);
  state = applyAnthropicConfigStatus(
    state,
    persist ? "Removing Anthropic provider and saving..." : "Removing Anthropic provider...",
  );
  render();
  try {
    const updated = persist
      ? await client.saveAnthropicMessagesSettings({ providers: remaining })
      : await client.updateAnthropicMessagesSettings({ providers: remaining });
    state = applyAnthropicMessagesSettings(state, updated);
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
    state = applyAnthropicConfigStatus(
      state,
      persist ? "Anthropic provider removed and saved" : "Anthropic provider removed",
    );
  } catch (error) {
    state = applyAnthropicConfigStatus(
      state,
      `Remove failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
}

avatarButton.addEventListener("click", async () => {
  await toggleConsole("avatar.click");
});

closeConsoleButton.addEventListener("click", async () => {
  await toggleConsole("console.close");
});

messageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }
  messageInput.value = "";
  await sendMessage(text);
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitConversationSettings();
});

settingsSaveButton.addEventListener("click", async () => {
  await submitConversationSettings({ persist: true });
});

providerConfigSelect.addEventListener("change", () => {
  state = selectProviderConfig(state, providerConfigSelect.value);
  render();
});

providerConfigForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitOpenAICompatibleSettings();
});

providerConfigSaveButton.addEventListener("click", async () => {
  await submitOpenAICompatibleSettings({ persist: true });
});

providerConfigAddButton.addEventListener("click", async () => {
  await addOpenAICompatibleProvider();
});

providerConfigRemoveButton.addEventListener("click", async () => {
  await removeOpenAICompatibleProvider();
});

providerHeaderAddButton.addEventListener("click", () => {
  providerHeadersList.append(createHeaderRow("", ""));
});

for (const button of providerPresetButtons) {
  button.addEventListener("click", () => {
    applyProviderPreset(OPENAI_COMPAT_PRESETS[button.dataset.providerPreset]);
  });
}

anthropicConfigSelect.addEventListener("change", () => {
  state = selectAnthropicConfig(state, anthropicConfigSelect.value);
  render();
});

anthropicConfigForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitAnthropicMessagesSettings();
});

anthropicConfigSaveButton.addEventListener("click", async () => {
  await submitAnthropicMessagesSettings({ persist: true });
});

anthropicConfigAddButton.addEventListener("click", async () => {
  await addAnthropicProvider();
});

anthropicConfigRemoveButton.addEventListener("click", async () => {
  await removeAnthropicProvider();
});

anthropicHeaderAddButton.addEventListener("click", () => {
  anthropicHeadersList.append(createHeaderRow("", ""));
});

for (const button of anthropicPresetButtons) {
  button.addEventListener("click", () => {
    applyAnthropicPreset(ANTHROPIC_PRESETS[button.dataset.anthropicPreset]);
  });
}

allowAllCmdToggle.addEventListener("change", async () => {
  await updateAllowAllCmd(allowAllCmdToggle.checked);
});

permissionCenterRefreshButton?.addEventListener("click", async () => {
  await refreshCapabilityGrants();
});

permissionAuditRefreshButton?.addEventListener("click", async () => {
  await refreshAuditPreview();
});

parallelInspectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitParallelInspect();
});

toolGuideCopyButton?.addEventListener("click", async () => {
  const text = state.toolGuide?.text || "";
  if (!text) {
    state = applyToolGuideStatus(state, "Tool playbook unavailable");
    render();
    return;
  }
  await copyToolingPayload(text, "Copied tool playbook", "Copy playbook failed");
});

promptPreviewCopyButton?.addEventListener("click", async () => {
  const text = state.promptPreview?.system_instruction || "";
  if (!text) {
    state = applyPromptPreviewStatus(state, "Runtime prompt unavailable");
    render();
    return;
  }
  await copyToolingPayload(text, "Copied runtime prompt", "Copy runtime prompt failed");
});

agentBundleCopyButton?.addEventListener("click", async () => {
  const text = state.agentBundle ? JSON.stringify(state.agentBundle, null, 2) : "";
  if (!text) {
    state = applyAgentBundleStatus(state, "Agent bundle unavailable");
    render();
    return;
  }
  try {
    await writeClipboardText(text);
    state = applyAgentBundleStatus(state, "Copied agent bundle");
  } catch (error) {
    state = applyAgentBundleStatus(
      state,
      `Copy agent bundle failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
});

codexManifestCopyButton?.addEventListener("click", async () => {
  const text = state.agentBundle?.codex_manifest
    ? JSON.stringify(state.agentBundle.codex_manifest, null, 2)
    : "";
  if (!text) {
    state = applyAgentBundleStatus(state, "Codex manifest unavailable");
    render();
    return;
  }
  try {
    await writeClipboardText(text);
    state = applyAgentBundleStatus(state, "Copied codex manifest");
  } catch (error) {
    state = applyAgentBundleStatus(
      state,
      `Copy codex manifest failed: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  render();
});

agentStarterPackCopyButton?.addEventListener("click", async () => {
  const text = state.agentStarterPack?.text || "";
  if (!text) {
    state = applyAgentStarterPackStatus(state, "Agent starter pack unavailable");
    render();
    return;
  }
  await copyToolingPayload(
    text,
    "Copied agent starter pack",
    "Copy starter pack failed",
    applyAgentStarterPackStatus,
  );
});

window.addEventListener("beforeunload", async () => {
  try {
    eventPump?.stop();
    await client.desktopDetach(sessionId);
    if (bridgeCommands) {
      await bridgeCommands.shutdownCore();
    }
  } catch {
    return;
  }
});

bootstrap();
