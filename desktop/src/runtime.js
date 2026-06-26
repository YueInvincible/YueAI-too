(function () {
  const DEFAULT_TIMEOUT_MS = 15000;
  const sessionId = "desktop-preview";

  function createMessage(role, text) {
    return {
      id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      role,
      text,
    };
  }

  class CoreProtocolClient {
    constructor(transport) {
      if (!transport || typeof transport.request !== "function") {
        throw new TypeError("transport.request is required");
      }
      this.transport = transport;
    }

    desktopState() {
      return this.#request("desktop.state");
    }

    desktopAttach(currentSessionId, metadata = {}) {
      return this.#request("desktop.attach", { session_id: currentSessionId, metadata });
    }

    desktopDetach(currentSessionId) {
      return this.#request("desktop.detach", { session_id: currentSessionId });
    }

    desktopCommand(command, value, source = "desktop-ui") {
      const params = { command, source };
      if (value !== undefined) {
        params.value = value;
      }
      return this.#request("desktop.command", params);
    }

    requestApproval(actionDescription, riskLevel, actor = "desktop-ui", currentSessionId) {
      const params = {
        action_description: actionDescription,
        risk_level: riskLevel,
        actor,
      };
      if (currentSessionId) {
        params.session_id = currentSessionId;
      }
      return this.#request("approval.request", params);
    }

    listPendingApprovals() {
      return this.#request("approval.pending.list");
    }

    respondApproval(approvalId, approved) {
      return this.#request("approval.respond", {
        approval_id: approvalId,
        approved: Boolean(approved),
      });
    }

    createConversation(title = "Yue Desktop") {
      return this.#request("conversations.create", { title });
    }

    sendConversationMessage(conversationId, content, provider) {
      const params = { conversation_id: conversationId, content };
      if (provider) {
        params.provider = provider;
      }
      return this.#request("conversations.send", params);
    }

    listProviders() {
      return this.#request("providers.list");
    }

    providersHealth() {
      return this.#request("providers.health");
    }

    getConversationSettings() {
      return this.#request("settings.conversation.get");
    }

    updateConversationSettings(payload, options = {}) {
      const params = { ...payload };
      if (options.persist) {
        params.persist = true;
      }
      return this.#request("settings.conversation.update", params);
    }

    saveConversationSettings(payload) {
      return this.updateConversationSettings(payload, { persist: true });
    }

    getOpenAICompatibleSettings() {
      return this.#request("settings.providers.openai_compat.get");
    }

    updateOpenAICompatibleSettings(payload, options = {}) {
      const params = { ...payload };
      if (options.persist) {
        params.persist = true;
      }
      return this.#request("settings.providers.openai_compat.update", params);
    }

    saveOpenAICompatibleSettings(payload) {
      return this.updateOpenAICompatibleSettings(payload, { persist: true });
    }

    getAnthropicMessagesSettings() {
      return this.#request("settings.providers.anthropic_messages.get");
    }

    updateAnthropicMessagesSettings(payload, options = {}) {
      const params = { ...payload };
      if (options.persist) {
        params.persist = true;
      }
      return this.#request("settings.providers.anthropic_messages.update", params);
    }

    saveAnthropicMessagesSettings(payload) {
      return this.updateAnthropicMessagesSettings(payload, { persist: true });
    }

    #request(method, params = {}) {
      return this.transport.request({ method, params, timeoutMs: DEFAULT_TIMEOUT_MS });
    }
  }

  function defaultDesktopViewState() {
    return {
      attachedSessionIds: [],
      consoleOpen: false,
      presence: "idle",
      expression: "neutral",
      hotkey: "Ctrl+Shift+Y",
      windowAnchor: "bottom-right",
      modelPath: null,
      conversationId: null,
      messages: [],
      activeAssistantMessageId: null,
      bridgeMode: "preview",
      bridgeTransport: "mock",
      bridgeProcessStarted: false,
      bridgePendingRequests: 0,
      bridgeQueuedEvents: 0,
      bridgeNote: "Mock preview transport active.",
      bridgeLastError: null,
      providerHealth: [],
      providerHealthSummary: "providers: unavailable",
      availableProviders: [],
      conversationSettings: null,
      settingsStatus: "Runtime only",
      openaiCompatibleSettings: null,
      providerConfigStatus: "Provider config runtime only",
      selectedProviderConfigName: "",
      anthropicMessagesSettings: null,
      anthropicConfigStatus: "Anthropic config runtime only",
      selectedAnthropicConfigName: "",
      pendingApprovals: [],
      approvalStatus: "No pending approvals",
    };
  }

  function applyDesktopSnapshot(state, snapshot) {
    return {
      ...state,
      attachedSessionIds: [...snapshot.attached_session_ids],
      consoleOpen: Boolean(snapshot.console_open),
      presence: snapshot.presence,
      expression: snapshot.expression,
      hotkey: snapshot.hotkey,
      windowAnchor: snapshot.window_anchor,
      modelPath: snapshot.model_path,
    };
  }

  function appendMessage(state, message) {
    return {
      ...state,
      messages: [...state.messages, message],
    };
  }

  function setConversationId(state, conversationId) {
    return {
      ...state,
      conversationId,
    };
  }

  function applyBridgeRuntime(state, runtime = {}) {
    return {
      ...state,
      bridgeMode: runtime.mode || state.bridgeMode,
      bridgeTransport: runtime.core_transport || state.bridgeTransport,
      bridgeProcessStarted: Boolean(runtime.process_started),
      bridgePendingRequests: Number(runtime.pending_requests || 0),
      bridgeQueuedEvents: Number(runtime.queued_events || 0),
      bridgeNote: runtime.note || state.bridgeNote,
      bridgeLastError: runtime.last_error || null,
    };
  }

  function applyProviderHealth(state, providerHealth = []) {
    const items = Array.isArray(providerHealth) ? [...providerHealth] : [];
    const okCount = items.filter((item) => item?.ok).length;
    const totalCount = items.length;
    return {
      ...state,
      providerHealth: items,
      providerHealthSummary:
        totalCount > 0
          ? `providers: ${okCount}/${totalCount} healthy`
          : "providers: unavailable",
    };
  }

  function applyProviderNames(state, providerNames = []) {
    return {
      ...state,
      availableProviders: Array.isArray(providerNames) ? [...providerNames] : [],
    };
  }

  function applyConversationSettings(state, conversationSettings) {
    return {
      ...state,
      conversationSettings: conversationSettings
        ? JSON.parse(JSON.stringify(conversationSettings))
        : null,
    };
  }

  function applySettingsStatus(state, settingsStatus) {
    return {
      ...state,
      settingsStatus: settingsStatus || state.settingsStatus,
    };
  }

  function applyOpenAICompatibleSettings(state, openaiCompatibleSettings) {
    const providers = openaiCompatibleSettings?.providers || [];
    const preferred = state.selectedProviderConfigName;
    const selected =
      providers.find((item) => item.provider_name === preferred)?.provider_name ||
      providers[0]?.provider_name ||
      "";
    return {
      ...state,
      openaiCompatibleSettings: openaiCompatibleSettings
        ? JSON.parse(JSON.stringify(openaiCompatibleSettings))
        : null,
      selectedProviderConfigName: selected,
    };
  }

  function applyProviderConfigStatus(state, providerConfigStatus) {
    return {
      ...state,
      providerConfigStatus: providerConfigStatus || state.providerConfigStatus,
    };
  }

  function selectProviderConfig(state, providerName) {
    return {
      ...state,
      selectedProviderConfigName: providerName || state.selectedProviderConfigName,
    };
  }

  function applyAnthropicMessagesSettings(state, anthropicMessagesSettings) {
    const providers = anthropicMessagesSettings?.providers || [];
    const preferred = state.selectedAnthropicConfigName;
    const selected =
      providers.find((item) => item.provider_name === preferred)?.provider_name ||
      providers[0]?.provider_name ||
      "";
    return {
      ...state,
      anthropicMessagesSettings: anthropicMessagesSettings
        ? JSON.parse(JSON.stringify(anthropicMessagesSettings))
        : null,
      selectedAnthropicConfigName: selected,
    };
  }

  function applyAnthropicConfigStatus(state, anthropicConfigStatus) {
    return {
      ...state,
      anthropicConfigStatus: anthropicConfigStatus || state.anthropicConfigStatus,
    };
  }

  function selectAnthropicConfig(state, providerName) {
    return {
      ...state,
      selectedAnthropicConfigName: providerName || state.selectedAnthropicConfigName,
    };
  }

  function applyPendingApprovals(state, pendingApprovals = []) {
    const items = [];
    const seen = new Set();
    for (const item of Array.isArray(pendingApprovals) ? pendingApprovals : []) {
      if (!item?.approval_id || seen.has(item.approval_id)) {
        continue;
      }
      seen.add(item.approval_id);
      items.push(JSON.parse(JSON.stringify(item)));
    }
    return {
      ...state,
      pendingApprovals: items,
      approvalStatus:
        items.length > 0
          ? `${items.length} approval${items.length === 1 ? "" : "s"} pending`
          : "No pending approvals",
    };
  }

  function applyApprovalResponse(state, approvalId) {
    return applyPendingApprovals(
      {
        ...state,
        approvalStatus: "Approval resolved",
      },
      state.pendingApprovals.filter((item) => item.approval_id !== approvalId),
    );
  }

  function applyApprovalStatus(state, approvalStatus) {
    return {
      ...state,
      approvalStatus: approvalStatus || state.approvalStatus,
    };
  }

  function applyCoreEvent(state, event = {}) {
    const topic = event?.topic;
    const payload = event?.payload || {};

    if (topic === "desktop.state.changed" && payload.state) {
      return applyDesktopSnapshot(state, payload.state);
    }

    if (topic === "conversation.delta" && typeof payload.text === "string") {
      return appendAssistantDelta(state, payload.text);
    }

    if (topic === "conversation.run.completed") {
      return finalizeAssistantMessage(state, payload.message?.content || "");
    }

    if (topic === "conversation.run.failed" || topic === "conversation.run.cancelled") {
      return {
        ...state,
        activeAssistantMessageId: null,
      };
    }

    if (topic === "approval.pending") {
      return applyPendingApprovals(state, [...state.pendingApprovals, payload]);
    }

    if (topic === "approval.responded" && payload.approval_id) {
      return applyApprovalResponse(state, payload.approval_id);
    }

    return state;
  }

  function appendAssistantDelta(state, text) {
    const messageId = state.activeAssistantMessageId || `assistant-live-${Date.now()}`;
    const existingIndex = state.messages.findIndex((message) => message.id === messageId);

    if (existingIndex >= 0) {
      const messages = state.messages.map((message) =>
        message.id === messageId
          ? {
              ...message,
              text: `${message.text}${text}`,
            }
          : message,
      );
      return {
        ...state,
        messages,
        activeAssistantMessageId: messageId,
      };
    }

    return {
      ...state,
      messages: [
        ...state.messages,
        {
          id: messageId,
          role: "assistant",
          text,
        },
      ],
      activeAssistantMessageId: messageId,
    };
  }

  function finalizeAssistantMessage(state, content) {
    if (!state.activeAssistantMessageId) {
      if (!content) {
        return state;
      }
      return appendMessage(state, {
        id: `assistant-final-${Date.now()}`,
        role: "assistant",
        text: content,
      });
    }

    const messages = state.messages.map((message) =>
      message.id === state.activeAssistantMessageId
        ? {
            ...message,
            text: content || message.text,
          }
        : message,
    );
    return {
      ...state,
      messages,
      activeAssistantMessageId: null,
    };
  }

  function now() {
    return new Date().toISOString();
  }

  function defaultMockState() {
    return {
      attached_session_ids: [],
      console_open: false,
      presence: "idle",
      expression: "neutral",
      hotkey: "Ctrl+Shift+Y",
      model_path: null,
      window_anchor: "bottom-right",
      click_opens_console: true,
      updated_at: now(),
    };
  }

  function reduceDesktopCommand(state, command, value) {
    if (
      command === "avatar.click" ||
      command === "console.toggle" ||
      command === "hotkey.toggle_console"
    ) {
      if (command === "avatar.click" && !state.click_opens_console) {
        return;
      }
      state.console_open = !state.console_open;
      return;
    }
    if (command === "console.open") {
      state.console_open = true;
      return;
    }
    if (command === "console.close") {
      state.console_open = false;
      return;
    }
    if (command === "presence.set") {
      state.presence = value;
      return;
    }
    if (command === "expression.set") {
      state.expression = value;
      return;
    }
    if (command === "avatar.sleep") {
      state.presence = "sleeping";
      return;
    }
    if (command === "avatar.wake") {
      state.presence = "idle";
    }
  }

  function createMockTransport() {
    const state = defaultMockState();
    let conversationCounter = 0;
    let conversationSettings = {
      default_provider: "fake.echo",
      routes: {
        chat: { provider: "fake.echo", prompt_profile: "default" },
        coding_agent: {
          provider: "fake.echo",
          prompt_profile: "coding_agent",
        },
      },
      prompt_profiles: {
        default: {
          personality: "Local-first assistant.",
          system_instruction: "",
          tool_instruction: "",
          response_instruction: "",
        },
        coding_agent: {
          personality: "Senior coding agent.",
          system_instruction: "",
          tool_instruction: "",
          response_instruction: "",
        },
      },
    };
    let openaiCompatibleSettings = {
      providers: [
        {
          provider_name: "ollama.chat",
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
      ],
    };
    let anthropicMessagesSettings = {
      providers: [
        {
          provider_name: "claude.coder",
          backend: "anthropic",
          base_url: "https://api.anthropic.com",
          model: "claude-sonnet-4-20250514",
          api_key_env: "ANTHROPIC_API_KEY",
          timeout_seconds: 120,
          health_timeout_seconds: 5,
          temperature: 0.2,
          max_tokens: 2048,
          anthropic_version: "2023-06-01",
          headers: {},
        },
      ],
    };
    let pendingApprovals = [
      {
        approval_id: "mock-approval-1",
        request_id: "mock-request-1",
        tool_name: "shell.run",
        actor: "desktop-preview",
        session_id: "desktop-preview",
        reason: "Command requires explicit approval",
        risk_level: "high",
        arguments: {
          command: "git push origin feature/desktop-bridge",
        },
        created_at: now(),
      },
    ];

    return {
      async request({ method, params }) {
        switch (method) {
          case "desktop.state":
            return { ...state };
          case "desktop.attach":
            if (!state.attached_session_ids.includes(params.session_id)) {
              state.attached_session_ids.push(params.session_id);
            }
            state.updated_at = now();
            return {
              session_id: params.session_id,
              state: { ...state },
            };
          case "desktop.detach":
            state.attached_session_ids = state.attached_session_ids.filter(
              (item) => item !== params.session_id,
            );
            state.updated_at = now();
            return { state: { ...state } };
          case "desktop.command":
            reduceDesktopCommand(state, params.command, params.value);
            state.updated_at = now();
            return { state: { ...state } };
          case "approval.request": {
            const approval = {
              approval_id: `mock-approval-${pendingApprovals.length + 1}`,
              request_id: `mock-request-${pendingApprovals.length + 1}`,
              tool_name: "approval.request",
              actor: params.actor || "desktop-ui",
              session_id: params.session_id || null,
              reason: params.action_description,
              risk_level: params.risk_level,
              arguments: {
                action_description: params.action_description,
              },
              created_at: now(),
            };
            pendingApprovals = [...pendingApprovals, approval];
            return { approved: false, pending: approval };
          }
          case "approval.pending.list":
            return JSON.parse(JSON.stringify(pendingApprovals));
          case "approval.respond": {
            const match = pendingApprovals.find((item) => item.approval_id === params.approval_id);
            if (!match) {
              throw new Error(`Unknown approval request: ${params.approval_id}`);
            }
            pendingApprovals = pendingApprovals.filter(
              (item) => item.approval_id !== params.approval_id,
            );
            return {
              ...JSON.parse(JSON.stringify(match)),
              approved: Boolean(params.approved),
            };
          }
          case "providers.list":
            return [
              "fake.echo",
              ...openaiCompatibleSettings.providers.map((item) => item.provider_name),
              ...anthropicMessagesSettings.providers.map((item) => item.provider_name),
            ];
          case "providers.health":
            return [
              {
                provider: "fake.echo",
                ok: true,
                reachable: true,
                backend: "fake",
              },
            ];
          case "settings.conversation.get":
            return JSON.parse(JSON.stringify(conversationSettings));
          case "settings.conversation.update":
            conversationSettings = JSON.parse(JSON.stringify(params));
            return JSON.parse(JSON.stringify(conversationSettings));
          case "settings.providers.openai_compat.get":
            return JSON.parse(JSON.stringify(openaiCompatibleSettings));
          case "settings.providers.openai_compat.update":
            openaiCompatibleSettings = JSON.parse(
              JSON.stringify(
                Object.fromEntries(
                  Object.entries(params).filter(([key]) => key !== "persist"),
                ),
              ),
            );
            return JSON.parse(JSON.stringify(openaiCompatibleSettings));
          case "settings.providers.anthropic_messages.get":
            return JSON.parse(JSON.stringify(anthropicMessagesSettings));
          case "settings.providers.anthropic_messages.update":
            anthropicMessagesSettings = JSON.parse(
              JSON.stringify(
                Object.fromEntries(
                  Object.entries(params).filter(([key]) => key !== "persist"),
                ),
              ),
            );
            return JSON.parse(JSON.stringify(anthropicMessagesSettings));
          case "conversations.create":
            conversationCounter += 1;
            return { id: `mock-conversation-${conversationCounter}` };
          case "conversations.send":
            return {
              run_id: `mock-run-${conversationCounter}`,
              message: createMessage("assistant", `Echo: ${params.content}`),
            };
          default:
            throw new Error(`Unsupported mock method: ${method}`);
        }
      },
    };
  }

  function normalizeBridgeResponse(response) {
    if (!response || typeof response !== "object") {
      throw new Error("Invalid bridge response");
    }
    if (response.ok) {
      return response.result;
    }
    throw new Error(response.error || "Bridge request failed");
  }

  function createTauriTransport(invoke) {
    return {
      async request({ method, params = {}, timeoutMs }) {
        const response = await invoke("bridge_request", {
          payload: {
            method,
            params,
            timeout_ms: timeoutMs ?? null,
          },
        });
        return normalizeBridgeResponse(response);
      },
    };
  }

  function createTauriBridgeCommands(invoke) {
    return {
      async runtimeInfo() {
        return invoke("bridge_runtime_info");
      },
      async drainEvents() {
        const result = await invoke("bridge_drain_events");
        return Array.isArray(result?.events) ? result.events : [];
      },
      async reportDiagnostic(payload) {
        return invoke("bridge_report_diagnostic", { payload });
      },
      async shutdownCore() {
        return invoke("bridge_shutdown_core");
      },
    };
  }

  function detectTauriInvoke(globalObject = globalThis) {
    if (typeof globalObject?.__TAURI__?.core?.invoke === "function") {
      return globalObject.__TAURI__.core.invoke;
    }
    if (typeof globalObject?.__TAURI_INTERNALS__?.invoke === "function") {
      return globalObject.__TAURI_INTERNALS__.invoke;
    }
    return null;
  }

  class TauriEventPump {
    constructor({ commands, onEvent, intervalMs = 250 }) {
      this.commands = commands;
      this.onEvent = onEvent;
      this.intervalMs = intervalMs;
      this.timer = null;
      this.running = false;
      this.inFlight = false;
    }

    start() {
      if (this.running) {
        return;
      }
      this.running = true;
      this.timer = window.setInterval(() => {
        void this.tick();
      }, this.intervalMs);
      void this.tick();
    }

    stop() {
      this.running = false;
      if (this.timer) {
        window.clearInterval(this.timer);
        this.timer = null;
      }
    }

    async tick() {
      if (!this.running || this.inFlight) {
        return;
      }
      this.inFlight = true;
      try {
        const events = await this.commands.drainEvents();
        for (const event of events) {
          this.onEvent(event);
        }
      } finally {
        this.inFlight = false;
      }
    }
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  async function waitForTauriInvoke(globalObject, { attempts = 40, intervalMs = 100 } = {}) {
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const invoke = detectTauriInvoke(globalObject);
      if (invoke) {
        return invoke;
      }
      await delay(intervalMs);
    }
    return null;
  }

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
    const invoke = await waitForTauriInvoke(window);
    bridgeCommands = invoke ? createTauriBridgeCommands(invoke) : null;
    usingNativeBridge = Boolean(bridgeCommands);
    client = new CoreProtocolClient(invoke ? createTauriTransport(invoke) : fallbackTransport);

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
    const attached = await client.desktopAttach(sessionId, { surface: "desktop-runtime" });
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
        stage: "runtime_bootstrap",
        readyState: document.readyState,
        hasTauri: typeof window.__TAURI__ !== "undefined",
        hasInternals: typeof window.__TAURI_INTERNALS__ !== "undefined",
        hasInvoke: typeof window.__TAURI_INTERNALS__?.invoke === "function",
        hasIpc: typeof window.__TAURI_INTERNALS__?.ipc === "function",
        bridgeLine: bridgeLine.textContent,
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
    state = applyDesktopSnapshot(state, await client.desktopState());
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
          tool_instruction:
            state.conversationSettings?.prompt_profiles?.default?.tool_instruction || "",
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
      if (client) {
        await client.desktopDetach(sessionId);
      }
      if (bridgeCommands) {
        await bridgeCommands.shutdownCore();
      }
    } catch {
      return;
    }
  });

  render();
  void bootstrap();
})();
