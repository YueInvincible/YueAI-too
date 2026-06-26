import { CoreProtocolClient, createMessage } from "./protocol.js";
import {
  applyApprovalResponse,
  applyApprovalStatus,
  appendMessage,
  applyAnthropicConfigStatus,
  applyAnthropicMessagesSettings,
  applyBridgeRuntime,
  applyConversationSettings,
  applyOpenAICompatibleSettings,
  applyPendingApprovals,
  applyCoreEvent,
  applyDesktopSnapshot,
  applyProviderNames,
  applyProviderConfigStatus,
  applyProviderHealth,
  applySettingsStatus,
  defaultDesktopViewState,
  selectAnthropicConfig,
  selectProviderConfig,
  setConversationId,
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
const approvalStatusLine = document.querySelector("#approval-status-line");
const approvalList = document.querySelector("#approval-list");
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
    model: "replace-me",
    api_key_env: "",
    timeout_seconds: 120,
    health_timeout_seconds: 5,
    temperature: 0.7,
    max_tokens: 1024,
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
  approvalStatusLine.textContent = state.approvalStatus;
  bridgeLine.title = state.bridgeLastError || state.bridgeNote;
  consolePanel.classList.toggle("hidden", !state.consoleOpen);

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

  approvalList.replaceChildren();
  for (const item of state.pendingApprovals) {
    const row = document.createElement("article");
    row.className = "approval-row";

    const title = document.createElement("div");
    title.className = "approval-title";
    title.textContent = item.tool_name || "approval";

    const meta = document.createElement("div");
    meta.className = "approval-meta";
    meta.textContent = [
      item.risk_level || "unknown risk",
      item.actor || "unknown actor",
      item.session_id || "no session",
    ].join(" | ");

    const reason = document.createElement("div");
    reason.className = "approval-reason";
    reason.textContent = item.reason || "No reason provided";

    const args = document.createElement("pre");
    args.className = "approval-arguments";
    args.textContent = JSON.stringify(item.arguments || {}, null, 2);

    const actions = document.createElement("div");
    actions.className = "approval-actions";

    const approveButton = document.createElement("button");
    approveButton.className = "send-button";
    approveButton.type = "button";
    approveButton.textContent = "Approve";
    approveButton.addEventListener("click", async () => {
      await respondToApproval(item.approval_id, true);
    });

    const denyButton = document.createElement("button");
    denyButton.className = "ghost-button";
    denyButton.type = "button";
    denyButton.textContent = "Deny";
    denyButton.addEventListener("click", async () => {
      await respondToApproval(item.approval_id, false);
    });

    actions.append(approveButton, denyButton);
    row.append(title, meta, reason, args, actions);
    approvalList.append(row);
  }

  messageLog.replaceChildren();
  for (const item of state.messages) {
    const row = document.createElement("article");
    row.className = `message-row role-${item.role}`;
    row.textContent = `${item.role}: ${item.text}`;
    messageLog.append(row);
  }
  messageLog.scrollTop = messageLog.scrollHeight;
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

async function toggleConsole(command) {
  const payload = await client.desktopCommand(command, undefined, sessionId);
  state = applyDesktopSnapshot(state, payload.state);
  render();
}

async function sendMessage(text) {
  if (!state.conversationId) {
    const conversation = await client.createConversation();
    state = setConversationId(state, conversation.id);
  }
  state = appendMessage(state, createMessage("user", text));
  render();
  await client.desktopCommand("presence.set", "thinking", sessionId);
  state = applyDesktopSnapshot(state, (await client.desktopState()));
  render();
  const response = await client.sendConversationMessage(state.conversationId, text);
  if (!usingNativeBridge) {
    state = appendMessage(state, {
      role: "assistant",
      text: response.message.text || response.message.content || "",
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
    await client.respondApproval(approvalId, approved);
    state = applyApprovalResponse(state, approvalId);
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
    model: "replace-me",
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
