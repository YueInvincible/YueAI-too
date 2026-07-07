(function () {
  const DEFAULT_TIMEOUT_MS = 120000;
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

    getToolActivitySnapshot() {
      return this.#request("tool.activity.snapshot");
    }

    listTools(options = {}) {
      return this.#request("tools.list", {
        provider_role: options.providerRole,
      });
    }

    invokeMany(calls, options = {}) {
      return this.#request("tools.invoke_many", {
        calls,
        parallel: Boolean(options.parallel),
        actor: options.actor || "desktop-ui",
        session_id: options.sessionId,
      });
    }

    getAllowAllCmd(currentSessionId) {
      return this.#request("permissions.allow_all_cmd.get", {
        session_id: currentSessionId,
      });
    }

    setAllowAllCmd(currentSessionId, allowed, actor = "desktop-ui") {
      return this.#request("permissions.allow_all_cmd.set", {
        session_id: currentSessionId,
        allowed: Boolean(allowed),
        actor,
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

    getActiveProviderSettings() {
      return this.#request("settings.providers.active.get");
    }

    getActiveProviderCatalog(payload = {}) {
      return this.#request("settings.providers.active.catalog", payload);
    }

    updateActiveProviderSettings(payload, options = {}) {
      const params = { ...payload };
      if (options.persist) {
        params.persist = true;
      }
      return this.#request("settings.providers.active.update", params);
    }

    saveActiveProviderSettings(payload) {
      return this.updateActiveProviderSettings(payload, { persist: true });
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
      activeDrawer: null,
      conversationSettings: null,
      settingsStatus: "Runtime only",
      activeProviderSettings: null,
      activeProviderDraft: null,
      activeProviderDraftDirty: false,
      activeProviderCatalog: null,
      activeProviderStatus: "Active provider runtime only",
      openaiCompatibleSettings: null,
      providerConfigStatus: "Provider config runtime only",
      selectedProviderConfigName: "",
      anthropicMessagesSettings: null,
      anthropicConfigStatus: "Anthropic config runtime only",
      selectedAnthropicConfigName: "",
      pendingApprovals: [],
      approvalStatus: "No pending approvals",
      toolsCatalog: [],
      toolCatalogStatus: "Tool catalog unavailable",
      allowAllCmd: false,
      allowAllCmdUpdatedBy: "none",
      allowAllCmdStatus: "Session shell grant disabled",
      parallelInspectStatus: "Parallel inspect idle",
      parallelInspectResults: [],
      toolActivity: [],
      toolActivityStatus: "No active tool run",
      inspectorSelection: null,
      collapsedRunIds: [],
      collapsedInspectorRunIds: [],
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

  function linkLatestUserMessageToRun(state, runId, conversationId = null) {
    if (!runId) {
      return state;
    }
    let linked = false;
    const messages = [...state.messages].reverse().map((message) => {
      if (!linked && message.role === "user" && !message.run_id) {
        linked = true;
        return {
          ...message,
          run_id: runId,
          conversation_id: conversationId || message.conversation_id || null,
        };
      }
      return message;
    }).reverse();
    return linked ? { ...state, messages } : state;
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

  function applyActiveDrawer(state, activeDrawer) {
    return {
      ...state,
      activeDrawer: activeDrawer || null,
    };
  }

  function applySettingsStatus(state, settingsStatus) {
    return {
      ...state,
      settingsStatus: settingsStatus || state.settingsStatus,
    };
  }

  function applyActiveProviderSettings(state, activeProviderSettings) {
    const nextDraft =
      state.activeProviderDraftDirty && state.activeProviderDraft
        ? JSON.parse(JSON.stringify(state.activeProviderDraft))
        : createActiveProviderDraft(
            activeProviderSettings?.active_provider || null,
            activeProviderSettings?.provider_options || [],
          );
    return {
      ...state,
      activeProviderSettings: activeProviderSettings
        ? JSON.parse(JSON.stringify(activeProviderSettings))
        : null,
      activeProviderDraft: nextDraft,
    };
  }

  function applyActiveProviderStatus(state, activeProviderStatus) {
    return {
      ...state,
      activeProviderStatus: activeProviderStatus || state.activeProviderStatus,
    };
  }

  function applyActiveProviderDraft(state, activeProviderDraft, options = {}) {
    return {
      ...state,
      activeProviderDraft: activeProviderDraft
        ? JSON.parse(JSON.stringify(activeProviderDraft))
        : null,
      activeProviderDraftDirty:
        options.dirty !== undefined ? Boolean(options.dirty) : state.activeProviderDraftDirty,
    };
  }

  function applyActiveProviderCatalog(state, activeProviderCatalog) {
    return {
      ...state,
      activeProviderCatalog: activeProviderCatalog
        ? JSON.parse(JSON.stringify(activeProviderCatalog))
        : null,
    };
  }

  function createActiveProviderDraft(snapshot, providerOptions = []) {
    if (snapshot) {
      return {
        kind: snapshot.kind || "llama.cpp",
        provider_name: snapshot.provider_name || "",
        model: snapshot.model || "",
        api_key_env: snapshot.api_key_env || "",
        host: snapshot.host || "",
        port: snapshot.port || "",
        base_url: snapshot.base_url || "",
        anthropic_version: snapshot.anthropic_version || "2023-06-01",
        timeout_seconds: snapshot.timeout_seconds ?? 120,
        health_timeout_seconds: snapshot.health_timeout_seconds ?? 5,
        temperature: snapshot.temperature ?? 0.7,
        max_tokens: snapshot.max_tokens ?? 1024,
      };
    }
    const fallback = providerOptions[0] || {};
    const kind = fallback.kind || "llama.cpp";
    return {
      kind,
      provider_name: fallback.default_provider_name || `${kind}.chat`,
      model: "",
      api_key_env: fallback.default_api_key_env || "",
      host: fallback.default_host || "",
      port: fallback.default_port || "",
      base_url: "",
      anthropic_version: "2023-06-01",
      timeout_seconds: 120,
      health_timeout_seconds: 5,
      temperature: 0.7,
      max_tokens: 1024,
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

  function applyToolsCatalog(state, toolsCatalog = []) {
    const items = Array.isArray(toolsCatalog)
      ? JSON.parse(JSON.stringify(toolsCatalog))
      : [];
    return {
      ...state,
      toolsCatalog: items,
      toolCatalogStatus:
        items.length > 0
          ? `${items.length} tool${items.length === 1 ? "" : "s"} loaded`
          : "Tool catalog unavailable",
    };
  }

  function applyToolCatalogStatus(state, toolCatalogStatus) {
    return {
      ...state,
      toolCatalogStatus: toolCatalogStatus || state.toolCatalogStatus,
    };
  }

  function applyAllowAllCmdGrant(state, grant) {
    const allowed = Boolean(grant?.allow_all_cmd);
    const updatedBy = grant?.updated_by || "none";
    return {
      ...state,
      allowAllCmd: allowed,
      allowAllCmdUpdatedBy: updatedBy,
      allowAllCmdStatus: allowed
        ? `Session shell grant enabled by ${updatedBy}`
        : "Session shell grant disabled",
    };
  }

  function applyAllowAllCmdStatus(state, allowAllCmdStatus) {
    return {
      ...state,
      allowAllCmdStatus: allowAllCmdStatus || state.allowAllCmdStatus,
    };
  }

  function applyParallelInspectStatus(state, parallelInspectStatus) {
    return {
      ...state,
      parallelInspectStatus: parallelInspectStatus || state.parallelInspectStatus,
    };
  }

  function applyParallelInspectResults(state, parallelInspectResults = []) {
    return {
      ...state,
      parallelInspectResults: Array.isArray(parallelInspectResults)
        ? JSON.parse(JSON.stringify(parallelInspectResults))
        : [],
    };
  }

  function applyToolActivityStatus(state, toolActivityStatus) {
    return {
      ...state,
      toolActivityStatus: toolActivityStatus || state.toolActivityStatus,
    };
  }

  function applyInspectorSelection(state, selection) {
    return {
      ...state,
      inspectorSelection: selection ? JSON.parse(JSON.stringify(selection)) : null,
    };
  }

  function toggleRunGroupCollapsed(state, runId) {
    if (!runId) {
      return state;
    }
    const current = new Set(state.collapsedRunIds || []);
    if (current.has(runId)) {
      current.delete(runId);
    } else {
      current.add(runId);
    }
    return {
      ...state,
      collapsedRunIds: [...current],
    };
  }

  function expandRunGroup(state, runId) {
    if (!runId || !(state.collapsedRunIds || []).includes(runId)) {
      return state;
    }
    return {
      ...state,
      collapsedRunIds: (state.collapsedRunIds || []).filter((item) => item !== runId),
    };
  }

  function toggleInspectorRunGroupCollapsed(state, runId) {
    if (!runId) {
      return state;
    }
    const current = new Set(state.collapsedInspectorRunIds || []);
    if (current.has(runId)) {
      current.delete(runId);
    } else {
      current.add(runId);
    }
    return {
      ...state,
      collapsedInspectorRunIds: [...current],
    };
  }

  function expandInspectorRunGroup(state, runId) {
    if (!runId || !(state.collapsedInspectorRunIds || []).includes(runId)) {
      return state;
    }
    return {
      ...state,
      collapsedInspectorRunIds: (state.collapsedInspectorRunIds || []).filter((item) => item !== runId),
    };
  }

  function applyToolActivitySnapshot(state, snapshot = {}) {
    const items = Array.isArray(snapshot?.items)
      ? JSON.parse(JSON.stringify(snapshot.items))
      : [];
    return {
      ...state,
      toolActivity: items,
      toolActivityStatus:
        snapshot?.status || (items.length > 0 ? state.toolActivityStatus : "No active tool run"),
    };
  }

  function applyToolActivityEvent(state, event = {}) {
    const topic = event?.topic;
    const payload = event?.payload || {};
    if (!topic) {
      return state;
    }
    if (topic === "conversation.run.started") {
      return {
        ...state,
        toolActivity: [],
        toolActivityStatus: "Conversation run started",
      };
    }
    const current = Array.isArray(state.toolActivity) ? [...state.toolActivity] : [];
    if (topic === "conversation.tool.requested") {
      const toolCall = payload.tool_call || {};
      return {
        ...state,
        toolActivity: [
          {
            run_id: payload.run_id || null,
            conversation_id: payload.conversation_id || null,
            tool_call_id: toolCall.id || null,
            request_id: payload.request_id || null,
            tool_name: toolCall.name || "unknown tool",
            arguments: toolCall.arguments || {},
            status: "requested",
            output: null,
            error: null,
            approval_id: null,
          },
          ...current,
        ].slice(0, 12),
        toolActivityStatus: `Requested ${toolCall.name || "tool"}`,
      };
    }
    if (topic === "tool.started") {
      const next = current.map((item) =>
        item.tool_call_id === payload.tool_call_id
          ? {
              ...item,
              request_id: payload.request_id || item.request_id,
              status: "running",
            }
          : item,
      );
      return {
        ...state,
        toolActivity: next,
        toolActivityStatus: `Running ${payload.tool || "tool"}`,
      };
    }
    if (topic === "approval.pending") {
      const next = current.map((item) =>
        item.request_id && item.request_id === payload.request_id
          ? {
              ...item,
              approval_id: payload.approval_id || null,
              status: "waiting_approval",
              error: payload.reason || item.error,
            }
          : item,
      );
      return {
        ...state,
        toolActivity: next,
        toolActivityStatus: `Approval requested for ${payload.tool_name || "tool"}`,
      };
    }
    if (topic === "approval.responded") {
      const next = current.map((item) =>
        item.request_id && item.request_id === payload.request_id
          ? {
              ...item,
              approval_id: payload.approval_id || item.approval_id,
              status: payload.approved ? "approved_pending_run" : "denied_by_user",
              error: payload.approved ? null : "Denied by user approval",
            }
          : item,
      );
      return {
        ...state,
        toolActivity: next,
        toolActivityStatus: payload.approved
          ? `Approved ${payload.tool_name || "tool"}`
          : `Denied ${payload.tool_name || "tool"}`,
      };
    }
    if (topic === "tool.finished") {
      const next = current.map((item) =>
        item.request_id === payload.request_id || item.tool_call_id === payload.tool_call_id
          ? {
              ...item,
              request_id: payload.request_id || item.request_id,
              status:
                payload.status === "denied"
                  ? classifyDeniedToolStatus(item, payload)
                  : payload.status || item.status,
              output: payload.output ?? item.output,
              error: payload.error || item.error,
            }
          : item,
      );
      return {
        ...state,
        toolActivity: next,
        toolActivityStatus: `${payload.tool_name || payload.tool || "Tool"} ${payload.status || "finished"}`,
      };
    }
    if (topic === "conversation.tool.completed") {
      const next = current.map((item) =>
        item.tool_call_id === payload.tool_call_id
          ? {
              ...item,
              status: payload.status || item.status,
            }
          : item,
      );
      return {
        ...state,
        toolActivity: next,
        toolActivityStatus: `${payload.tool || "Tool"} ${payload.status || "completed"}`,
      };
    }
    if (topic === "conversation.run.failed") {
      return {
        ...state,
        toolActivityStatus: `Conversation run failed: ${payload.error || "unknown error"}`,
      };
    }
    if (topic === "conversation.run.completed") {
      return {
        ...state,
        toolActivityStatus:
          current.length > 0 ? "Conversation run completed" : state.toolActivityStatus,
      };
    }
    return state;
  }

  function classifyDeniedToolStatus(item, payload) {
    const error = String(payload?.error || item?.error || "").toLowerCase();
    if (item?.approval_id || error.includes("user denied")) {
      return "denied_by_user";
    }
    return "denied_by_profile";
  }

  function applyCoreEvent(state, event = {}) {
    const topic = event?.topic;
    const payload = event?.payload || {};
    const withToolActivity = applyToolActivityEvent(state, event);

    if (
      topic === "tool.finished" &&
      (payload.request_id || payload.tool_call_id || payload.run_id)
    ) {
      return appendToolResultMessage(withToolActivity, payload);
    }

    if (topic === "desktop.state.changed" && payload.state) {
      return applyDesktopSnapshot(withToolActivity, payload.state);
    }

    if (topic === "conversation.delta" && typeof payload.text === "string") {
      return appendAssistantDelta(
        withToolActivity,
        payload.text,
        payload.run_id || null,
        payload.conversation_id || null,
      );
    }

    if (topic === "conversation.run.completed") {
      return finalizeAssistantMessage(
        withToolActivity,
        payload.message?.content || "",
        payload,
      );
    }

    if (topic === "conversation.run.failed" || topic === "conversation.run.cancelled") {
      return {
        ...withToolActivity,
        activeAssistantMessageId: null,
      };
    }

    if (topic === "approval.pending") {
      return applyPendingApprovals(withToolActivity, [...state.pendingApprovals, payload]);
    }

    if (topic === "approval.responded" && payload.approval_id) {
      return applyApprovalResponse(withToolActivity, payload.approval_id);
    }

    if (topic === "permission.grant.updated") {
      return applyAllowAllCmdGrant(withToolActivity, payload);
    }

    return withToolActivity;
  }

  function appendAssistantDelta(state, text, runId = null, conversationId = null) {
    const messageId = state.activeAssistantMessageId || `assistant-live-${runId || Date.now()}`;
    const existingIndex = state.messages.findIndex((message) => message.id === messageId);

    if (existingIndex >= 0) {
      const messages = state.messages.map((message) =>
        message.id === messageId
          ? {
              ...message,
              text: `${message.text}${text}`,
              run_id: runId || message.run_id || null,
              conversation_id: conversationId || message.conversation_id || null,
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
          kind: "assistant_turn",
          run_id: runId,
          conversation_id: conversationId,
        },
      ],
      activeAssistantMessageId: messageId,
    };
  }

  function finalizeAssistantMessage(state, content, payload = {}) {
    const runId = payload.run_id || payload.message?.metadata?.run_id || null;
    const conversationId = payload.conversation_id || payload.message?.conversation_id || null;
    if (!state.activeAssistantMessageId) {
      if (!content) {
        return state;
      }
      return appendMessage(state, {
        id: `assistant-final-${Date.now()}`,
        role: "assistant",
        text: content,
        kind: "assistant_turn",
        run_id: runId,
        conversation_id: conversationId,
      });
    }

    const messages = state.messages.map((message) =>
      message.id === state.activeAssistantMessageId
        ? {
            ...message,
            text: content || message.text,
            kind: "assistant_turn",
            run_id: runId || message.run_id || null,
            conversation_id: conversationId || message.conversation_id || null,
          }
        : message,
    );
    return {
      ...state,
      messages,
      activeAssistantMessageId: null,
    };
  }

  function appendToolResultMessage(state, payload = {}) {
    const toolCallId = payload.tool_call_id || null;
    const requestId = payload.request_id || null;
    const messageId = `tool-result-${toolCallId || requestId || Date.now()}`;
    const text = formatToolResultText(payload);
    const existingIndex = state.messages.findIndex((message) => message.id === messageId);
    const nextMessage = {
      id: messageId,
      role: "tool",
      kind: "tool_result",
      text,
      run_id: payload.run_id || null,
      conversation_id: payload.conversation_id || null,
      request_id: requestId,
      tool_call_id: toolCallId,
      tool_name: payload.tool_name || payload.tool || "tool",
      status: payload.status || "finished",
      output: payload.output ?? null,
      error: payload.error || null,
    };
    if (existingIndex >= 0) {
      return {
        ...state,
        messages: state.messages.map((message) =>
          message.id === messageId ? { ...message, ...nextMessage } : message,
        ),
      };
    }
    return appendMessage(state, nextMessage);
  }

  function formatToolResultText(payload = {}) {
    if (payload.error) {
      return payload.error;
    }
    if (payload.output == null) {
      return `${payload.tool_name || payload.tool || "tool"} ${payload.status || "finished"}`;
    }
    if (typeof payload.output === "string") {
      return payload.output;
    }
    try {
      return JSON.stringify(payload.output, null, 2);
    } catch {
      return String(payload.output);
    }
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
      default_provider: "localhost.chat",
      routes: {
        chat: { provider: "localhost.chat", prompt_profile: "default" },
        coding_agent: {
          provider: "localhost.chat",
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
          provider_name: "localhost.chat",
          backend: "llama.cpp",
          base_url: "http://127.0.0.1:8080/v1",
          model: "Qwen3-4B-Q5_K_M.gguf",
          api_key_env: "",
          timeout_seconds: 120,
          health_timeout_seconds: 5,
          temperature: 0.7,
          max_tokens: 2048,
          headers: {},
        },
      ],
    };
    function buildActiveProviderSettings() {
      const provider = openaiCompatibleSettings.providers[0] || {
        provider_name: "localhost.chat",
        backend: "llama.cpp",
        base_url: "http://127.0.0.1:8080",
        model: "Qwen3-4B-Q5_K_M.gguf",
        api_key_env: "",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.7,
        max_tokens: 2048,
        headers: {},
      };
      const kind = provider.backend === "anthropic" ? "anthropic" : provider.backend;
      return {
        single_provider_mode: true,
        active_provider: {
          kind,
          label: kind === "llama.cpp" ? "Local llama.cpp" : provider.backend,
          family: ["llama.cpp", "ollama", "lmstudio", "custom"].includes(kind) ? "local" : "cloud",
          plugin_id: kind === "anthropic" ? "anthropic.messages" : "openai.compat",
          provider_name: provider.provider_name,
          backend: provider.backend,
          base_url: provider.base_url,
          host: "127.0.0.1",
          port: 8080,
          model: provider.model,
          api_key_env: provider.api_key_env || "",
          timeout_seconds: provider.timeout_seconds,
          health_timeout_seconds: provider.health_timeout_seconds,
          temperature: provider.temperature,
          max_tokens: provider.max_tokens,
          headers: provider.headers || {},
          anthropic_version: provider.anthropic_version || "2023-06-01",
        },
        provider_options: [
          { kind: "llama.cpp", label: "Local llama.cpp" },
          { kind: "ollama", label: "Ollama" },
          { kind: "lmstudio", label: "LM Studio" },
          { kind: "custom", label: "Custom OpenAI-compatible" },
          { kind: "openai", label: "OpenAI" },
          { kind: "google", label: "Google AI" },
          { kind: "openrouter", label: "OpenRouter" },
          { kind: "anthropic", label: "Anthropic" },
        ],
        conversation: JSON.parse(JSON.stringify(conversationSettings)),
      };
    }
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
    let allowAllCmdGrant = {
      session_id: "desktop-preview",
      allow_all_cmd: false,
      updated_by: "none",
    };
    const toolCatalog = [
      {
        name: "workspace.read",
        description: "Read a UTF-8 workspace file with line-range metadata.",
        input_schema: {},
        capability: "file.read",
        risk: "low",
        plugin_id: "core",
        output_kind: "file_content",
        metadata: {
          output_kind: "file_content",
          parallel_safe: true,
          mutates_state: false,
        },
      },
      {
        name: "workspace.grep",
        description: "Search workspace file contents by literal string or regex.",
        input_schema: {},
        capability: "file.read",
        risk: "low",
        plugin_id: "core",
        output_kind: "structured",
        metadata: {
          output_kind: "structured",
          parallel_safe: true,
          mutates_state: false,
        },
      },
      {
        name: "shell.run",
        description: "Run a shell command with explicit cwd, timeout, and risk metadata.",
        input_schema: {},
        capability: "shell.execute",
        risk: "high",
        plugin_id: "core",
        output_kind: "command_output",
        metadata: {
          output_kind: "command_output",
          parallel_safe: false,
          mutates_state: true,
        },
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
          case "tools.list":
            return JSON.parse(JSON.stringify(toolCatalog));
          case "tools.invoke_many":
            return {
              parallel: Boolean(params.parallel),
              results: (params.calls || []).map((call, index) => ({
                request_id: `mock-batch-${index + 1}`,
                tool_name: call.name,
                status: "succeeded",
                output:
                  call.name === "workspace.read"
                    ? {
                        path: call.arguments?.path || "",
                        content: `Mock content for ${call.arguments?.path || "unknown path"}`,
                        start_line: call.arguments?.start_line || 1,
                        end_line: call.arguments?.end_line || 1,
                        total_lines: 1,
                        returned_lines: 1,
                        truncated: false,
                      }
                    : {
                        ok: true,
                      },
                error: null,
              })),
            };
          case "permissions.allow_all_cmd.get":
            if (params.session_id !== allowAllCmdGrant.session_id) {
              return {
                session_id: params.session_id,
                allow_all_cmd: false,
                updated_by: "none",
              };
            }
            return JSON.parse(JSON.stringify(allowAllCmdGrant));
          case "permissions.allow_all_cmd.set":
            allowAllCmdGrant = {
              session_id: params.session_id,
              allow_all_cmd: Boolean(params.allowed),
              updated_by: params.actor || "desktop-ui",
            };
            return JSON.parse(JSON.stringify(allowAllCmdGrant));
          case "providers.list":
            return [
              ...openaiCompatibleSettings.providers.map((item) => item.provider_name),
              ...anthropicMessagesSettings.providers.map((item) => item.provider_name),
            ];
          case "providers.health":
            return [
              {
                provider: "localhost.chat",
                ok: true,
                reachable: true,
                backend: "llama.cpp",
                model: "Qwen3-4B-Q5_K_M.gguf",
                model_available: true,
                models: ["Qwen3-4B-Q5_K_M.gguf"],
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
          case "settings.providers.active.get":
            return JSON.parse(JSON.stringify(buildActiveProviderSettings()));
          case "settings.providers.active.catalog": {
            const next = JSON.parse(JSON.stringify((params && params.provider) || {}));
            const kind = String(next.kind || next.backend || "llama.cpp");
            const modelsByKind = {
              "llama.cpp": ["Qwen3-4B-Q5_K_M.gguf"],
              ollama: ["qwen2.5:7b-instruct", "qwen2.5-coder:7b"],
              lmstudio: ["openai/gpt-oss-20b", "qwen2.5-coder-7b-instruct"],
              custom: ["custom-model"],
              openai: ["gpt-4.1-mini", "gpt-4.1"],
              google: ["gemini-2.5-flash", "gemini-2.5-pro"],
              openrouter: ["openai/gpt-4.1-mini", "anthropic/claude-sonnet-4"],
              anthropic: ["claude-sonnet-4-20250514", "claude-3-7-sonnet-latest"],
            };
            const models = modelsByKind[kind] || [];
            return {
              kind,
              provider_name: next.provider_name || `${kind}.chat`,
              models,
              selected_model: next.model || models[0] || "",
              reachable: true,
              ok: true,
              error: null,
              auto_selected: !next.model && Boolean(models[0]),
            };
          }
          case "settings.providers.active.update": {
            const next = JSON.parse(
              JSON.stringify(
                (params && params.provider) || {},
              ),
            );
            const kind = String(next.kind || next.backend || "llama.cpp");
            const backend = kind === "anthropic" ? "anthropic" : kind;
            const baseUrl = next.base_url || (
              kind === "llama.cpp"
                ? `http://${next.host || "127.0.0.1"}:${next.port || 8080}`
                : ["ollama", "lmstudio", "custom"].includes(kind)
                  ? `http://${next.host || "127.0.0.1"}:${next.port || (kind === "ollama" ? 11434 : kind === "lmstudio" ? 1234 : 8080)}/v1`
                  : kind === "anthropic"
                    ? "https://api.anthropic.com"
                    : kind === "google"
                      ? "https://generativelanguage.googleapis.com/v1beta/openai"
                      : kind === "openrouter"
                        ? "https://openrouter.ai/api/v1"
                        : "https://api.openai.com/v1"
            );
            const provider = {
              provider_name: next.provider_name || `${kind}.chat`,
              backend,
              base_url: baseUrl,
              model: next.model || "mock-model",
              api_key_env: next.api_key_env || "",
              timeout_seconds: Number(next.timeout_seconds || 120),
              health_timeout_seconds: Number(next.health_timeout_seconds || 5),
              temperature: Number(next.temperature || 0.7),
              max_tokens: Number(next.max_tokens || 1024),
              headers: {},
            };
            if (kind === "anthropic") {
              anthropicMessagesSettings = {
                providers: [
                  {
                    ...provider,
                    anthropic_version: next.anthropic_version || "2023-06-01",
                  },
                ],
              };
            } else {
              openaiCompatibleSettings = {
                providers: [provider],
              };
            }
            conversationSettings.default_provider = provider.provider_name;
            conversationSettings.routes.chat.provider = provider.provider_name;
            conversationSettings.routes.coding_agent.provider = provider.provider_name;
            return JSON.parse(JSON.stringify(buildActiveProviderSettings()));
          }
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
  const overviewSessionKicker = document.querySelector("#overview-session-kicker");
  const overviewRuntimeSummary = document.querySelector("#overview-runtime-summary");
  const overviewProviderSummary = document.querySelector("#overview-provider-summary");
  const overviewActivitySummary = document.querySelector("#overview-activity-summary");
  const overviewBridgePending = document.querySelector("#overview-bridge-pending");
  const overviewBridgeEvents = document.querySelector("#overview-bridge-events");
  const overviewMessageCount = document.querySelector("#overview-message-count");
  const overviewApprovalCount = document.querySelector("#overview-approval-count");
  const overviewBandBridgeNote = document.querySelector("#overview-band-bridge-note");
  const activeProviderStatusLine = document.querySelector("#active-provider-status-line");
  const activeProviderRuntimeLine = document.querySelector("#active-provider-runtime-line");
  const activeProviderForm = document.querySelector("#active-provider-form");
  const activeProviderSaveButton = document.querySelector("#active-provider-save-button");
  const activeProviderKindSelect = document.querySelector("#active-provider-kind-select");
  const activeProviderNameInput = document.querySelector("#active-provider-name-input");
  const activeProviderModelInput = document.querySelector("#active-provider-model-input");
  const activeProviderModelShell = document.querySelector("#active-provider-model-shell");
  const activeProviderModelRefreshButton = document.querySelector("#active-provider-model-refresh-button");
  const activeProviderModelHint = document.querySelector("#active-provider-model-hint");
  const activeProviderApiKeyEnvInput = document.querySelector("#active-provider-api-key-env-input");
  const activeProviderHostInput = document.querySelector("#active-provider-host-input");
  const activeProviderPortInput = document.querySelector("#active-provider-port-input");
  const activeProviderBaseUrlInput = document.querySelector("#active-provider-base-url-input");
  const activeProviderAnthropicVersionInput = document.querySelector("#active-provider-anthropic-version-input");
  const activeProviderTimeoutInput = document.querySelector("#active-provider-timeout-input");
  const activeProviderHealthTimeoutInput = document.querySelector("#active-provider-health-timeout-input");
  const activeProviderTemperatureInput = document.querySelector("#active-provider-temperature-input");
  const activeProviderMaxTokensInput = document.querySelector("#active-provider-max-tokens-input");
  const activeProviderLocalFields = document.querySelector("#active-provider-local-fields");
  const activeProviderAnthropicFields = document.querySelector("#active-provider-anthropic-fields");
  const configScopeSelect = document.querySelector("#config-scope-select");
  const routingConfigBlock = document.querySelector("#routing-config-block");
  const openaiConfigBlock = document.querySelector("#openai-config-block");
  const anthropicConfigBlock = document.querySelector("#anthropic-config-block");
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
  const opsDrawer = document.querySelector("#ops-drawer");
  const configDrawer = document.querySelector("#config-drawer");
  const opsDrawerButton = document.querySelector("#ops-drawer-button");
  const configDrawerButton = document.querySelector("#config-drawer-button");
  const consoleDrawerBackdrop = document.querySelector("#console-drawer-backdrop");
  const drawerCloseButtons = document.querySelectorAll("[data-close-drawer]");
  const allowAllCmdStatusLine = document.querySelector("#allow-all-cmd-status-line");
  const allowAllCmdToggle = document.querySelector("#allow-all-cmd-toggle");
  const parallelInspectStatusLine = document.querySelector("#parallel-inspect-status-line");
  const parallelInspectForm = document.querySelector("#parallel-inspect-form");
  const parallelInspectPathsInput = document.querySelector("#parallel-inspect-paths-input");
  const parallelInspectStartLineInput = document.querySelector("#parallel-inspect-start-line-input");
  const parallelInspectEndLineInput = document.querySelector("#parallel-inspect-end-line-input");
  const parallelInspectResults = document.querySelector("#parallel-inspect-results");
  const toolCatalogStatusLine = document.querySelector("#tool-catalog-status-line");
  const toolCatalogList = document.querySelector("#tool-catalog-list");
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
  const customSelectControllers = new Map();

  function createBrowserBridgeTransport() {
    return {
      async request({ method, params = {}, timeoutMs }) {
        const response = await fetch("/api/bridge/request", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            method,
            params,
            timeout_ms: timeoutMs ?? null,
          }),
        });
        const payload = await response.json();
        if (!payload.ok) {
          throw new Error(payload.error || "Browser bridge request failed");
        }
        return payload.result;
      },
    };
  }

  function createBrowserBridgeCommands() {
    return {
      async runtimeInfo() {
        const response = await fetch("/api/bridge/runtime", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Bridge runtime failed: ${response.status}`);
        }
        return response.json();
      },
      async drainEvents() {
        const response = await fetch("/api/bridge/events", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Bridge events failed: ${response.status}`);
        }
        const payload = await response.json();
        return Array.isArray(payload?.events) ? payload.events : [];
      },
      async reportDiagnostic() {
        return { ok: true };
      },
      async shutdownCore() {
        const response = await fetch("/api/bridge/shutdown", { method: "POST" });
        return response.ok ? response.json() : { stopped: false };
      },
    };
  }

  async function detectBrowserBridge() {
    try {
      const response = await fetch("/api/bridge/runtime", { cache: "no-store" });
      if (!response.ok) {
        return null;
      }
      return createBrowserBridgeCommands();
    } catch {
      return null;
    }
  }

  function resolveConfigScopeForProvider(providerName) {
    const normalized = String(providerName || "").trim();
    if (!normalized) {
      return "routing";
    }
    const openaiProviders = state.openaiCompatibleSettings?.providers || [];
    if (openaiProviders.some((item) => item.provider_name === normalized)) {
      return "openai";
    }
    const anthropicProviders = state.anthropicMessagesSettings?.providers || [];
    if (anthropicProviders.some((item) => item.provider_name === normalized)) {
      return "anthropic";
    }
    return "routing";
  }

  function setConfigScope(scope) {
    if (!configScopeSelect || !scope) {
      return;
    }
    if (configScopeSelect.value !== scope) {
      configScopeSelect.value = scope;
    }
    applyConfigScopeView();
  }

  function syncConfigScopeFromProvider(providerName) {
    const scope = resolveConfigScopeForProvider(providerName);
    setConfigScope(scope);
    if (scope === "openai" && providerConfigSelect && providerName) {
      providerConfigSelect.value = providerName;
      state = selectProviderConfig(state, providerName);
    }
    if (scope === "anthropic" && anthropicConfigSelect && providerName) {
      anthropicConfigSelect.value = providerName;
      state = selectAnthropicConfig(state, providerName);
    }
  }

  function applyConfigScopeView() {
    const scope = configScopeSelect?.value || "routing";
    routingConfigBlock?.classList.toggle("is-hidden", scope !== "routing");
    openaiConfigBlock?.classList.toggle("is-hidden", scope !== "openai");
    anthropicConfigBlock?.classList.toggle("is-hidden", scope !== "anthropic");
    try {
      window.localStorage?.setItem("yue.desktop.configScope", scope);
    } catch {
      return;
    }
  }

  function ensureCustomSelect(select) {
    if (!select || customSelectControllers.has(select)) {
      return customSelectControllers.get(select) || null;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "custom-select";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "custom-select-trigger";
    button.setAttribute("aria-haspopup", "listbox");
    button.innerHTML = `
      <span class="custom-select-trigger-copy"></span>
      <span class="custom-select-trigger-meta"></span>
      <span class="custom-select-chevron" aria-hidden="true"></span>
    `;
    const panel = document.createElement("div");
    panel.className = "custom-select-panel";
    panel.setAttribute("role", "listbox");
    select.classList.add("custom-select-native");
    select.setAttribute("tabindex", "-1");
    select.after(wrapper);
    wrapper.append(select, button, panel);

    const triggerCopy = button.querySelector(".custom-select-trigger-copy");
    const triggerMeta = button.querySelector(".custom-select-trigger-meta");

    const controller = {
      select,
      wrapper,
      button,
      panel,
      sync() {
        const options = Array.from(select.options || []);
        const selected = options.find((item) => item.value === select.value) || options[0] || null;
        triggerCopy.textContent = selected?.textContent || "Select";
        triggerMeta.textContent = options.length > 1 ? `${options.length} options` : "";
        panel.replaceChildren();
        options.forEach((option, index) => {
          const item = document.createElement("button");
          item.type = "button";
          item.className = [
            "custom-select-option",
            option.value === select.value ? "is-selected" : "",
          ].filter(Boolean).join(" ");
          item.setAttribute("role", "option");
          item.dataset.value = option.value;
          item.innerHTML = `
            <span class="custom-select-option-label">${option.textContent || option.value || `Option ${index + 1}`}</span>
            <span class="custom-select-option-meta">${option.value === select.value ? "Active" : "Switch"}</span>
          `;
          item.addEventListener("click", () => {
            if (select.value !== option.value) {
              select.value = option.value;
              select.dispatchEvent(new Event("change", { bubbles: true }));
            }
            controller.close();
            controller.sync();
          });
          panel.append(item);
        });
        wrapper.classList.toggle("is-disabled", Boolean(select.disabled));
      },
      open() {
        if (select.disabled) {
          return;
        }
        for (const entry of customSelectControllers.values()) {
          if (entry !== controller) {
            entry.close();
          }
        }
        wrapper.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");
      },
      close() {
        wrapper.classList.remove("is-open");
        button.setAttribute("aria-expanded", "false");
      },
      toggle() {
        if (wrapper.classList.contains("is-open")) {
          controller.close();
        } else {
          controller.open();
        }
      },
    };

    button.addEventListener("click", () => controller.toggle());
    select.addEventListener("change", () => controller.sync());
    customSelectControllers.set(select, controller);
    controller.sync();
    return controller;
  }

  function syncCustomSelects() {
    [
      activeProviderKindSelect,
      activeProviderModelInput,
      providerConfigSelect,
      anthropicConfigSelect,
      configScopeSelect,
    ].forEach((select) => {
      const controller = ensureCustomSelect(select);
      controller?.sync();
    });
  }

  function isLocalProviderKind(kind) {
    return ["llama.cpp", "ollama", "lmstudio", "custom"].includes(kind);
  }

  function createDefaultActiveProviderDraft(kind) {
    const option = (state.activeProviderSettings?.provider_options || []).find(
      (item) => item.kind === kind,
    ) || {};
    const current = state.activeProviderDraft || {};
    const host = option.default_host || "";
    const port = option.default_port || "";
    const suffix = kind === "llama.cpp" ? "" : "/v1";
    return {
      kind,
      provider_name: option.default_provider_name || `${kind}.chat`,
      model: "",
      api_key_env: option.default_api_key_env || "",
      host,
      port,
      base_url: isLocalProviderKind(kind) && host && port ? `http://${host}:${port}${suffix}` : "",
      anthropic_version: "2023-06-01",
      timeout_seconds: current.timeout_seconds ?? 120,
      health_timeout_seconds: current.health_timeout_seconds ?? 5,
      temperature: current.temperature ?? 0.7,
      max_tokens: current.max_tokens ?? 1024,
    };
  }

  function populateActiveProviderModelSelect(models = [], selectedModel = "") {
    if (!activeProviderModelInput) {
      return;
    }
    activeProviderModelInput.replaceChildren();
    const normalizedModels = Array.isArray(models)
      ? models.filter((item) => String(item || "").trim())
      : [];
    if (normalizedModels.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No models loaded";
      activeProviderModelInput.append(option);
      activeProviderModelInput.value = "";
      return;
    }
    for (const model of normalizedModels) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      activeProviderModelInput.append(option);
    }
    activeProviderModelInput.value =
      normalizedModels.includes(selectedModel) ? selectedModel : normalizedModels[0];
  }

  function applyActiveProviderKindView(kind) {
    const normalized = String(kind || "").trim().toLowerCase();
    activeProviderLocalFields?.toggleAttribute("hidden", !isLocalProviderKind(normalized));
    activeProviderAnthropicFields?.toggleAttribute("hidden", normalized !== "anthropic");
    if (activeProviderModelInput) {
      activeProviderModelInput.disabled = isLocalProviderKind(normalized);
    }
    if (activeProviderModelShell) {
      activeProviderModelShell.querySelector("span").textContent = isLocalProviderKind(normalized)
        ? "Detected model"
        : "Model catalog";
    }
  }

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
    parallelInspectStatusLine.textContent = state.parallelInspectStatus;
    toolCatalogStatusLine.textContent = state.toolCatalogStatus;
    allowAllCmdToggle.checked = Boolean(state.allowAllCmd);
    bridgeLine.title = state.bridgeLastError || state.bridgeNote;
    consolePanel.classList.toggle("hidden", !state.consoleOpen);
    const providerCount = state.providerHealth.length;
    const healthyCount = state.providerHealth.filter((item) => item.ok).length;
    if (overviewSessionKicker) {
      overviewSessionKicker.textContent = state.attachedSessionIds.join(", ") || "Disconnected";
    }
    if (overviewRuntimeSummary) {
      overviewRuntimeSummary.textContent = state.bridgeProcessStarted
        ? "Bridge live and listening"
        : "Bridge idle";
    }
    if (overviewProviderSummary) {
      overviewProviderSummary.textContent =
        providerCount > 0
          ? `${healthyCount} of ${providerCount} providers healthy`
          : "No provider health loaded yet.";
    }
    if (overviewActivitySummary) {
      overviewActivitySummary.textContent = state.toolActivityStatus;
    }
    if (overviewBridgePending) {
      overviewBridgePending.textContent = String(state.bridgePendingRequests || 0);
    }
    if (overviewBridgeEvents) {
      overviewBridgeEvents.textContent = String(state.bridgeQueuedEvents || 0);
    }
    if (overviewMessageCount) {
      overviewMessageCount.textContent = String(state.messages.length);
    }
    if (overviewApprovalCount) {
      overviewApprovalCount.textContent = String(state.pendingApprovals.length);
    }
    if (overviewBandBridgeNote) {
      overviewBandBridgeNote.textContent = state.bridgeLastError || state.bridgeNote;
    }
    opsDrawer?.classList.toggle("is-open", state.activeDrawer === "ops");
    configDrawer?.classList.toggle("is-open", state.activeDrawer === "config");
    consoleDrawerBackdrop?.toggleAttribute("hidden", !state.activeDrawer);
    opsDrawerButton?.classList.toggle("is-active", state.activeDrawer === "ops");
    configDrawerButton?.classList.toggle("is-active", state.activeDrawer === "config");
    applyConfigScopeView();

    if (activeProviderStatusLine) {
      activeProviderStatusLine.textContent = state.activeProviderStatus;
    }
    const activeProviderSnapshot = state.activeProviderSettings?.active_provider || null;
    const activeProviderDraft = state.activeProviderDraft || null;
    const activeProviderCatalog = state.activeProviderCatalog || null;
    if (activeProviderRuntimeLine) {
      activeProviderRuntimeLine.textContent = activeProviderSnapshot
        ? `${activeProviderSnapshot.label} | ${activeProviderSnapshot.provider_name} | ${activeProviderSnapshot.model}`
        : "Single-provider mode keeps one model active at a time.";
    }
    if (activeProviderKindSelect) {
      activeProviderKindSelect.replaceChildren();
      const options = state.activeProviderSettings?.provider_options || [];
      for (const item of options) {
        const option = document.createElement("option");
        option.value = item.kind;
        option.textContent = item.label;
        activeProviderKindSelect.append(option);
      }
      const selectedKind = activeProviderDraft?.kind || activeProviderSnapshot?.kind || "";
      if (selectedKind && activeProviderKindSelect.querySelector(`option[value="${selectedKind}"]`)) {
        activeProviderKindSelect.value = selectedKind;
      }
    }
    if (activeProviderDraft) {
      activeProviderNameInput.value = activeProviderDraft.provider_name || "";
      activeProviderApiKeyEnvInput.value = activeProviderDraft.api_key_env || "";
      activeProviderHostInput.value = activeProviderDraft.host || "";
      activeProviderPortInput.value = String(activeProviderDraft.port || "");
      activeProviderBaseUrlInput.value = activeProviderDraft.base_url || "";
      activeProviderAnthropicVersionInput.value =
        activeProviderDraft.anthropic_version || "2023-06-01";
      activeProviderTimeoutInput.value = String(activeProviderDraft.timeout_seconds ?? "");
      activeProviderHealthTimeoutInput.value = String(
        activeProviderDraft.health_timeout_seconds ?? "",
      );
      activeProviderTemperatureInput.value = String(activeProviderDraft.temperature ?? "");
      activeProviderMaxTokensInput.value = String(activeProviderDraft.max_tokens ?? "");
      populateActiveProviderModelSelect(
        activeProviderCatalog?.models || [],
        activeProviderDraft.model || activeProviderCatalog?.selected_model || "",
      );
      applyActiveProviderKindView(activeProviderDraft.kind);
      if (activeProviderModelHint) {
        if (activeProviderCatalog?.error) {
          activeProviderModelHint.textContent = activeProviderCatalog.error;
        } else if (isLocalProviderKind(activeProviderDraft.kind)) {
          activeProviderModelHint.textContent = activeProviderDraft.model
            ? `Auto-detected from local runtime: ${activeProviderDraft.model}`
            : "Refresh models to detect the runtime model from your local server.";
        } else if ((activeProviderCatalog?.models || []).length > 0) {
          activeProviderModelHint.textContent = `${activeProviderCatalog.models.length} models available from ${activeProviderDraft.provider_name || activeProviderDraft.kind}.`;
        } else {
          activeProviderModelHint.textContent = "Refresh models to load the latest catalog from this provider.";
        }
      }
    } else {
      populateActiveProviderModelSelect([], "");
      applyActiveProviderKindView(activeProviderKindSelect?.value || "");
    }
    syncCustomSelects();

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
    const messageGroups = buildMessageGroups(state.messages);
    messageLog.classList.toggle("is-stacked", messageGroups.length <= 6);
    messageLog.classList.toggle("has-messages", messageGroups.length > 0);
    for (const [index, group] of messageGroups.entries()) {
      const block = document.createElement("section");
      block.className = `message-group ${group.kind === "run" ? "is-run-group" : "is-loose-group"}`;
      block.dataset.stackDepth = String(Math.max(0, messageGroups.length - index - 1));
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

  function summarizeRunGroup(group) {
    const messages = Array.isArray(group.messages) ? group.messages : [];
    const userCount = messages.filter((item) => item.role === "user").length;
    const assistantMessages = messages.filter((item) => item.role === "assistant");
    const assistantCount = assistantMessages.length;
    const toolMessages = messages.filter((item) => item.role === "tool");
    const toolCount = toolMessages.length;
    const errorCount = toolMessages.filter((item) =>
      ["failed", "denied", "denied_by_user", "denied_by_profile", "timed_out", "cancelled"].includes(item.status),
    ).length;
    const activeCount = toolMessages.filter((item) =>
      ["requested", "running", "waiting_approval", "approved_pending_run"].includes(item.status),
    ).length;
    const outcome =
      errorCount > 0 ? "issues" : activeCount > 0 ? "active" : toolCount > 0 ? "complete" : "chat_only";
    const assistant = [...messages]
      .reverse()
      .find((item) => item.role === "assistant" && item.text);
    const tool = [...messages]
      .reverse()
      .find((item) => item.role === "tool");
    const assistantCopyText = assistant?.text || "";
    const toolCopyText = tool
      ? tool.error || tool.text || (tool.output !== undefined ? JSON.stringify(tool.output, null, 2) : "")
      : "";
    return {
      userCount,
      assistantCount,
      toolCount,
      errorCount,
      activeCount,
      outcome,
      assistant,
      tool,
      assistantPreviewText: assistant
        ? `Assistant: ${summarizeDesktopText(assistant.text, 140)}`
        : "Assistant: no final assistant turn yet",
      toolPreviewText: tool
        ? `Latest tool: ${tool.tool_name || "tool"} | ${tool.status || "unknown"} | ${summarizeDesktopText(tool.error || tool.text || toolCopyText, 120)}`
        : toolCount > 0
          ? "Latest tool: pending"
          : "Latest tool: none",
      assistantCopyText,
      toolCopyText,
    };
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

  function summarizeDesktopText(value, maxChars = 120) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!text) {
      return "none";
    }
    if (text.length <= maxChars) {
      return text;
    }
    return `${text.slice(0, maxChars - 1)}...`;
  }

  function buildRunCopyArtifacts(group = {}) {
    const summary = summarizeRunGroup(group);
    return {
      summary,
      summaryText: [
        `run ${group.run_id || "unknown"}`,
        `outcome: ${summary.outcome}`,
        `users: ${summary.userCount}`,
        `assistants: ${summary.assistantCount}`,
        `tools: ${summary.toolCount}`,
        `issues: ${summary.errorCount}`,
        summary.assistantPreviewText,
        summary.toolPreviewText,
      ].join("\n"),
      assistantText: summary.assistantCopyText,
      toolText: summary.toolCopyText,
      jsonText: JSON.stringify(
        {
          run_id: group.run_id || null,
          summary: {
            userCount: summary.userCount,
            assistantCount: summary.assistantCount,
            toolCount: summary.toolCount,
            errorCount: summary.errorCount,
            activeCount: summary.activeCount,
            outcome: summary.outcome,
          },
          messages: Array.isArray(group.messages) ? group.messages : [],
        },
        null,
        2,
      ),
    };
  }

  function findLatestToolActivityForRun(toolActivity = [], runId) {
    if (!runId || !Array.isArray(toolActivity)) {
      return null;
    }
    return toolActivity.find((item) => item?.run_id === runId) || null;
  }

  async function copyRunPayload(text, successStatus) {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        fallbackCopyText(text);
      }
      state = applyToolActivityStatus(state, successStatus);
    } catch (error) {
      state = applyToolActivityStatus(
        state,
        `Copy failed: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
    render();
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

    const sigil = document.createElement("div");
    sigil.className = "message-sigil";
    sigil.textContent =
      item.role === "user" ? "YOU" : item.role === "assistant" ? "AI" : "TOOL";

    const title = document.createElement("div");
    title.className = "message-role";
    title.textContent = item.tool_name
      ? item.tool_name
      : item.role === "assistant"
        ? "Yue"
        : item.role === "user"
          ? "You"
          : "Tool";

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = item.role === "tool"
      ? [
          item.run_id ? `run ${item.run_id}` : null,
          item.tool_call_id ? `call ${item.tool_call_id}` : null,
          item.request_id ? `request ${item.request_id}` : null,
          item.status ? `status ${item.status}` : null,
        ]
          .filter(Boolean)
          .join(" | ")
      : item.role === "assistant"
        ? "Assistant response"
        : "Prompt sent";

    const titleStack = document.createElement("div");
    titleStack.className = "message-title-stack";
    titleStack.append(title, meta);

    head.append(sigil, titleStack);

    const body = document.createElement(item.role === "tool" ? "pre" : "div");
    body.className = [
      "message-body",
      item.role === "tool" ? "is-tool-body" : "is-chat-body",
    ].join(" ");
    const text = String(item.text || "");
    if (item.role === "tool") {
      body.textContent = text;
    } else {
      const paragraphs = text
        .split(/\n{2,}/)
        .map((chunk) => chunk.trim())
        .filter(Boolean);
      if (paragraphs.length === 0) {
        body.textContent = text;
      } else {
        for (const paragraphText of paragraphs) {
          const paragraph = document.createElement("p");
          paragraph.className = "message-paragraph";
          paragraph.textContent = paragraphText;
          body.append(paragraph);
        }
      }
    }

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
      });
    }
    return items;
  }

  function groupRunInspectorItems(items = []) {
    const groups = [];
    for (const item of Array.isArray(items) ? items : []) {
      if (item?.run_id) {
        const existing = groups.find(
          (group) => group.kind === "run" && group.run_id === item.run_id,
        );
        if (existing) {
          existing.items.push(item);
        } else {
          groups.push({
            kind: "run",
            run_id: item.run_id,
            items: [item],
          });
        }
        continue;
      }
      groups.push({
        kind: "standalone",
        id:
          item?.approval_id ||
          item?.request_id ||
          item?.tool_call_id ||
          `inspector-${groups.length}`,
        items: [item],
      });
    }
    return groups;
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
      ["failed", "denied", "denied_by_user", "denied_by_profile", "timed_out", "cancelled"].includes(item.status),
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
    head.append(name, badge);

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

    row.append(head, meta, reason, preview, actions);
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
    if (status === "denied_by_user" || status === "denied_by_profile" || status === "failed") {
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
    const invoke = await waitForTauriInvoke(window);
    const browserBridge = invoke ? null : await detectBrowserBridge();
    bridgeCommands = invoke
      ? createTauriBridgeCommands(invoke)
      : browserBridge;
    usingNativeBridge = Boolean(bridgeCommands);
    client = new CoreProtocolClient(
      invoke
        ? createTauriTransport(invoke)
        : bridgeCommands
          ? createBrowserBridgeTransport()
          : fallbackTransport,
    );

    try {
      const savedScope = window.localStorage?.getItem("yue.desktop.configScope");
      if (savedScope && configScopeSelect) {
        configScopeSelect.value = savedScope;
      }
    } catch {
      // no-op
    }

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
    await refreshProviderConfigurationState();
    await refreshActiveProviderCatalog({ draft: state.activeProviderDraft });
    state = applyPendingApprovals(state, await client.listPendingApprovals());
    state = applyToolActivitySnapshot(state, await client.getToolActivitySnapshot());
    state = applyToolsCatalog(state, await client.listTools());
    state = applyAllowAllCmdGrant(state, await client.getAllowAllCmd(sessionId));
    syncConfigScopeFromProvider(
      state.conversationSettings?.routes?.chat?.provider ||
        state.conversationSettings?.default_provider ||
        "",
    );

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
    } catch (error) {
      allowAllCmdToggle.checked = !allowed;
      state = applyAllowAllCmdStatus(
        state,
        `Shell grant update failed: ${error instanceof Error ? error.message : String(error)}`,
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
    if (!state.conversationId) {
      const conversation = await client.createConversation();
      state = setConversationId(state, conversation.id);
    }
    state = appendMessage(state, {
      ...createMessage("user", text),
      kind: "user_turn",
      conversation_id: state.conversationId,
    });
    render();
    await client.desktopCommand("presence.set", "thinking", sessionId);
    state = applyDesktopSnapshot(state, await client.desktopState());
    render();
    const response = await client.sendConversationMessage(state.conversationId, text);
    state = linkLatestUserMessageToRun(state, response.run_id, state.conversationId);
    if (!usingNativeBridge) {
      state = appendMessage(state, {
        role: "assistant",
        text: response.message.text || response.message.content || "",
        kind: "assistant_turn",
        run_id: response.run_id || null,
        conversation_id: state.conversationId,
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

  function readActiveProviderDraftFromDom() {
    const kind = activeProviderKindSelect?.value?.trim() || "llama.cpp";
    const selectedModel = activeProviderModelInput?.value?.trim() || "";
    return {
      kind,
      provider_name: activeProviderNameInput.value.trim(),
      model: selectedModel,
      api_key_env: activeProviderApiKeyEnvInput.value.trim(),
      host: activeProviderHostInput.value.trim(),
      port: Number(activeProviderPortInput.value),
      base_url: activeProviderBaseUrlInput.value.trim(),
      anthropic_version: activeProviderAnthropicVersionInput.value.trim(),
      timeout_seconds: Number(activeProviderTimeoutInput.value),
      health_timeout_seconds: Number(activeProviderHealthTimeoutInput.value),
      temperature: Number(activeProviderTemperatureInput.value),
      max_tokens: Number(activeProviderMaxTokensInput.value),
    };
  }

  function syncActiveProviderDraftFromDom(options = {}) {
    state = applyActiveProviderDraft(state, readActiveProviderDraftFromDom(), options);
    return state.activeProviderDraft;
  }

  async function refreshActiveProviderCatalog({ draft = null } = {}) {
    const providerDraft = draft || state.activeProviderDraft || readActiveProviderDraftFromDom();
    try {
      const catalog = await client.getActiveProviderCatalog({ provider: providerDraft });
      state = applyActiveProviderCatalog(state, catalog);
      const nextDraft = {
        ...providerDraft,
        model: catalog.selected_model || providerDraft.model || "",
      };
      state = applyActiveProviderDraft(state, nextDraft, {
        dirty: state.activeProviderDraftDirty,
      });
    } catch (error) {
      state = applyActiveProviderCatalog(state, {
        kind: providerDraft.kind,
        provider_name: providerDraft.provider_name,
        models: [],
        selected_model: providerDraft.model || "",
        reachable: false,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  async function ensureActiveProviderModelSelection() {
    const draft = syncActiveProviderDraftFromDom({ dirty: true });
    if (draft.model) {
      return draft;
    }
    await refreshActiveProviderCatalog({ draft });
    const hydratedDraft = state.activeProviderDraft || draft;
    if (!hydratedDraft.model) {
      throw new Error("No model discovered for the selected provider");
    }
    return hydratedDraft;
  }

  function readActiveProviderSettingsPayload(draft = null) {
    const providerDraft = draft || state.activeProviderDraft || readActiveProviderDraftFromDom();
    const kind = providerDraft.kind || "llama.cpp";
    const payload = {
      provider: {
        kind,
        provider_name: providerDraft.provider_name,
        model: providerDraft.model,
        api_key_env: providerDraft.api_key_env,
        base_url: providerDraft.base_url,
        timeout_seconds: providerDraft.timeout_seconds,
        health_timeout_seconds: providerDraft.health_timeout_seconds,
        temperature: providerDraft.temperature,
        max_tokens: providerDraft.max_tokens,
      },
    };
    if (isLocalProviderKind(kind)) {
      payload.provider.host = providerDraft.host;
      payload.provider.port = providerDraft.port;
    }
    if (kind === "anthropic") {
      payload.provider.anthropic_version = providerDraft.anthropic_version;
    }
    return payload;
  }

  async function refreshProviderConfigurationState() {
    state = applyConversationSettings(state, await client.getConversationSettings());
    state = applyActiveProviderSettings(state, await client.getActiveProviderSettings());
    state = applyOpenAICompatibleSettings(state, await client.getOpenAICompatibleSettings());
    state = applyAnthropicMessagesSettings(state, await client.getAnthropicMessagesSettings());
    state = applyProviderNames(state, await client.listProviders());
    state = applyProviderHealth(state, await client.providersHealth());
  }

  async function submitActiveProviderSettings({ persist = false } = {}) {
    const draft = await ensureActiveProviderModelSelection();
    const payload = readActiveProviderSettingsPayload(draft);
    state = applyActiveProviderStatus(
      state,
      persist ? "Saving active provider..." : "Applying active provider...",
    );
    render();
    try {
      const updated = persist
        ? await client.saveActiveProviderSettings(payload)
        : await client.updateActiveProviderSettings(payload);
      state = applyActiveProviderSettings(state, updated);
      state = applyActiveProviderDraft(
        state,
        createActiveProviderDraft(updated.active_provider, updated.provider_options || []),
        { dirty: false },
      );
      await refreshProviderConfigurationState();
      await refreshActiveProviderCatalog({ draft: state.activeProviderDraft });
      state = applyActiveProviderStatus(
        state,
        persist ? "Active provider saved" : "Active provider applied",
      );
      state = applySettingsStatus(
        state,
        persist ? "Conversation routes saved through active provider" : "Conversation routes updated through active provider",
      );
    } catch (error) {
      state = applyActiveProviderStatus(
        state,
        `${persist ? "Save" : "Update"} failed: ${error instanceof Error ? error.message : String(error)}`,
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

  opsDrawerButton?.addEventListener("click", () => {
    state = applyActiveDrawer(state, state.activeDrawer === "ops" ? null : "ops");
    render();
  });

  configDrawerButton?.addEventListener("click", () => {
    state = applyActiveDrawer(state, state.activeDrawer === "config" ? null : "config");
    render();
  });

  consoleDrawerBackdrop?.addEventListener("click", () => {
    state = applyActiveDrawer(state, null);
    render();
  });

  for (const button of drawerCloseButtons) {
    button.addEventListener("click", () => {
      state = applyActiveDrawer(state, null);
      render();
    });
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    for (const controller of customSelectControllers.values()) {
      if (!controller.wrapper.contains(target)) {
        controller.close();
      }
    }
  });

  activeProviderKindSelect?.addEventListener("change", () => {
    const nextKind = activeProviderKindSelect.value;
    if (!nextKind) {
      return;
    }
    state = applyActiveProviderDraft(state, createDefaultActiveProviderDraft(nextKind), { dirty: true });
    state = applyActiveProviderCatalog(state, null);
    render();
    void refreshActiveProviderCatalog({ draft: state.activeProviderDraft }).then(render);
  });

  activeProviderForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitActiveProviderSettings();
  });

  activeProviderSaveButton?.addEventListener("click", async () => {
    await submitActiveProviderSettings({ persist: true });
  });

  activeProviderModelRefreshButton?.addEventListener("click", async () => {
    syncActiveProviderDraftFromDom({ dirty: true });
    state = applyActiveProviderStatus(state, "Refreshing model catalog...");
    render();
    await refreshActiveProviderCatalog({ draft: state.activeProviderDraft });
    state = applyActiveProviderStatus(state, "Model catalog refreshed");
    render();
  });

  [
    activeProviderNameInput,
    activeProviderModelInput,
    activeProviderApiKeyEnvInput,
    activeProviderHostInput,
    activeProviderPortInput,
    activeProviderBaseUrlInput,
    activeProviderAnthropicVersionInput,
    activeProviderTimeoutInput,
    activeProviderHealthTimeoutInput,
    activeProviderTemperatureInput,
    activeProviderMaxTokensInput,
  ].forEach((field) => {
    field?.addEventListener("input", () => {
      syncActiveProviderDraftFromDom({ dirty: true });
    });
    field?.addEventListener("change", () => {
      syncActiveProviderDraftFromDom({ dirty: true });
    });
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
    setConfigScope("openai");
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
    setConfigScope("anthropic");
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

  parallelInspectForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitParallelInspect();
  });

  configScopeSelect?.addEventListener("change", () => {
    applyConfigScopeView();
  });

  defaultProviderInput?.addEventListener("change", () => {
    syncConfigScopeFromProvider(defaultProviderInput.value);
  });

  chatProviderInput?.addEventListener("change", () => {
    syncConfigScopeFromProvider(chatProviderInput.value);
  });

  codingProviderInput?.addEventListener("change", () => {
    syncConfigScopeFromProvider(codingProviderInput.value);
  });

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
