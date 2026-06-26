export function defaultDesktopViewState() {
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

export function applyDesktopSnapshot(state, snapshot) {
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

export function appendMessage(state, message) {
  return {
    ...state,
    messages: [...state.messages, message],
  };
}

export function setConversationId(state, conversationId) {
  return {
    ...state,
    conversationId,
  };
}

export function applyBridgeRuntime(state, runtime = {}) {
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

export function applyProviderHealth(state, providerHealth = []) {
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

export function applyProviderNames(state, providerNames = []) {
  return {
    ...state,
    availableProviders: Array.isArray(providerNames) ? [...providerNames] : [],
  };
}

export function applyConversationSettings(state, conversationSettings) {
  return {
    ...state,
    conversationSettings: conversationSettings
      ? JSON.parse(JSON.stringify(conversationSettings))
      : null,
  };
}

export function applySettingsStatus(state, settingsStatus) {
  return {
    ...state,
    settingsStatus: settingsStatus || state.settingsStatus,
  };
}

export function applyOpenAICompatibleSettings(state, openaiCompatibleSettings) {
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

export function applyProviderConfigStatus(state, providerConfigStatus) {
  return {
    ...state,
    providerConfigStatus: providerConfigStatus || state.providerConfigStatus,
  };
}

export function selectProviderConfig(state, providerName) {
  return {
    ...state,
    selectedProviderConfigName: providerName || state.selectedProviderConfigName,
  };
}

export function applyAnthropicMessagesSettings(state, anthropicMessagesSettings) {
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

export function applyAnthropicConfigStatus(state, anthropicConfigStatus) {
  return {
    ...state,
    anthropicConfigStatus: anthropicConfigStatus || state.anthropicConfigStatus,
  };
}

export function selectAnthropicConfig(state, providerName) {
  return {
    ...state,
    selectedAnthropicConfigName: providerName || state.selectedAnthropicConfigName,
  };
}

export function applyPendingApprovals(state, pendingApprovals = []) {
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

export function applyApprovalResponse(state, approvalId) {
  return applyPendingApprovals(
    {
      ...state,
      approvalStatus: "Approval resolved",
    },
    state.pendingApprovals.filter((item) => item.approval_id !== approvalId),
  );
}

export function applyApprovalStatus(state, approvalStatus) {
  return {
    ...state,
    approvalStatus: approvalStatus || state.approvalStatus,
  };
}

export function applyCoreEvent(state, event = {}) {
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
