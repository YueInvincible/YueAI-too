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
    toolGuide: null,
    toolGuideStatus: "Tool playbook unavailable",
    promptPreview: null,
    promptPreviewStatus: "Runtime prompt unavailable",
    agentBundle: null,
    agentBundleStatus: "Agent bundle unavailable",
    agentStarterPack: null,
    agentStarterPackStatus: "Agent starter pack unavailable",
    allowAllCmd: false,
    allowAllCmdUpdatedBy: "none",
    allowAllCmdStatus: "Session shell grant disabled",
    capabilityGrants: [],
    capabilityGrantsStatus: "No scoped grants loaded",
    parallelInspectStatus: "Parallel inspect idle",
    parallelInspectResults: [],
    toolActivity: [],
    toolActivityStatus: "No active tool run",
    inspectorSelection: null,
    collapsedRunIds: [],
    collapsedInspectorRunIds: [],
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

export function linkLatestUserMessageToRun(state, runId, conversationId = null) {
  if (!runId) {
    return state;
  }
  let linked = false;
  const messages = [...state.messages].reverse().map((message) => {
    if (
      !linked &&
      message.role === "user" &&
      !message.run_id
    ) {
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

export function applyActiveDrawer(state, activeDrawer) {
  return {
    ...state,
    activeDrawer: activeDrawer || null,
  };
}

export function applySettingsStatus(state, settingsStatus) {
  return {
    ...state,
    settingsStatus: settingsStatus || state.settingsStatus,
  };
}

export function applyActiveProviderSettings(state, activeProviderSettings) {
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

export function applyActiveProviderStatus(state, activeProviderStatus) {
  return {
    ...state,
    activeProviderStatus: activeProviderStatus || state.activeProviderStatus,
  };
}

export function applyActiveProviderDraft(state, activeProviderDraft, options = {}) {
  return {
    ...state,
    activeProviderDraft: activeProviderDraft
      ? JSON.parse(JSON.stringify(activeProviderDraft))
      : null,
    activeProviderDraftDirty:
      options.dirty !== undefined ? Boolean(options.dirty) : state.activeProviderDraftDirty,
  };
}

export function applyActiveProviderCatalog(state, activeProviderCatalog) {
  return {
    ...state,
    activeProviderCatalog: activeProviderCatalog
      ? JSON.parse(JSON.stringify(activeProviderCatalog))
      : null,
  };
}

export function createActiveProviderDraft(snapshot, providerOptions = []) {
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

export function applyToolsCatalog(state, toolsCatalog = []) {
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

export function applyToolCatalogStatus(state, toolCatalogStatus) {
  return {
    ...state,
    toolCatalogStatus: toolCatalogStatus || state.toolCatalogStatus,
  };
}

export function applyToolGuide(state, toolGuide) {
  const nextGuide = toolGuide ? JSON.parse(JSON.stringify(toolGuide)) : null;
  const toolCount = nextGuide?.tools?.length || 0;
  return {
    ...state,
    toolGuide: nextGuide,
    toolGuideStatus:
      toolCount > 0
        ? `${toolCount} preferred tool${toolCount === 1 ? "" : "s"} in playbook`
        : "Tool playbook unavailable",
  };
}

export function applyToolGuideStatus(state, toolGuideStatus) {
  return {
    ...state,
    toolGuideStatus: toolGuideStatus || state.toolGuideStatus,
  };
}

export function applyPromptPreview(state, promptPreview) {
  const nextPreview = promptPreview ? JSON.parse(JSON.stringify(promptPreview)) : null;
  const hasInstruction = Boolean(nextPreview?.system_instruction);
  return {
    ...state,
    promptPreview: nextPreview,
    promptPreviewStatus: hasInstruction
      ? `Runtime prompt ready for ${nextPreview.provider_role || "chat"}`
      : "Runtime prompt unavailable",
  };
}

export function applyPromptPreviewStatus(state, promptPreviewStatus) {
  return {
    ...state,
    promptPreviewStatus: promptPreviewStatus || state.promptPreviewStatus,
  };
}

export function applyAgentBundle(state, agentBundle) {
  const nextBundle = agentBundle ? JSON.parse(JSON.stringify(agentBundle)) : null;
  const toolCount = nextBundle?.tools?.length || 0;
  return {
    ...state,
    agentBundle: nextBundle,
    agentBundleStatus: nextBundle
      ? `${nextBundle.provider_role || "agent"} bundle ready | ${toolCount} tools`
      : "Agent bundle unavailable",
  };
}

export function applyAgentBundleStatus(state, agentBundleStatus) {
  return {
    ...state,
    agentBundleStatus: agentBundleStatus || state.agentBundleStatus,
  };
}

export function applyAgentStarterPack(state, agentStarterPack) {
  const nextPack = agentStarterPack ? JSON.parse(JSON.stringify(agentStarterPack)) : null;
  return {
    ...state,
    agentStarterPack: nextPack,
    agentStarterPackStatus: nextPack
      ? `${nextPack.provider_role || "agent"} starter pack ready`
      : "Agent starter pack unavailable",
  };
}

export function applyAgentStarterPackStatus(state, agentStarterPackStatus) {
  return {
    ...state,
    agentStarterPackStatus: agentStarterPackStatus || state.agentStarterPackStatus,
  };
}

export function applyAllowAllCmdGrant(state, grant) {
  const allowed = Boolean(grant?.allow_all_cmd);
  const updatedBy = grant?.updated_by || "none";
  const nextState = {
    ...state,
    allowAllCmd: allowed,
    allowAllCmdUpdatedBy: updatedBy,
    allowAllCmdStatus: allowed
      ? `Session shell grant enabled by ${updatedBy}`
      : "Session shell grant disabled",
  };
  if (Array.isArray(grant?.capability_grants)) {
    return applyCapabilityGrants(nextState, grant);
  }
  return {
    ...nextState,
  };
}

export function applyAllowAllCmdStatus(state, allowAllCmdStatus) {
  return {
    ...state,
    allowAllCmdStatus: allowAllCmdStatus || state.allowAllCmdStatus,
  };
}

export function applyCapabilityGrants(state, grant = {}) {
  const items = Array.isArray(grant?.capability_grants)
    ? JSON.parse(JSON.stringify(grant.capability_grants))
    : [];
  return {
    ...state,
    capabilityGrants: items,
    capabilityGrantsStatus:
      items.length > 0
        ? `${items.length} scoped grant${items.length === 1 ? "" : "s"} active`
        : "No scoped grants active",
  };
}

export function applyCapabilityGrantsStatus(state, capabilityGrantsStatus) {
  return {
    ...state,
    capabilityGrantsStatus: capabilityGrantsStatus || state.capabilityGrantsStatus,
  };
}

export function applyParallelInspectStatus(state, parallelInspectStatus) {
  return {
    ...state,
    parallelInspectStatus: parallelInspectStatus || state.parallelInspectStatus,
  };
}

export function applyParallelInspectResults(state, parallelInspectResults = []) {
  return {
    ...state,
    parallelInspectResults: Array.isArray(parallelInspectResults)
      ? JSON.parse(JSON.stringify(parallelInspectResults))
      : [],
  };
}

export function applyToolActivityStatus(state, toolActivityStatus) {
  return {
    ...state,
    toolActivityStatus: toolActivityStatus || state.toolActivityStatus,
  };
}

export function applyInspectorSelection(state, selection) {
  return {
    ...state,
    inspectorSelection: selection ? JSON.parse(JSON.stringify(selection)) : null,
  };
}

export function toggleRunGroupCollapsed(state, runId) {
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

export function expandRunGroup(state, runId) {
  if (!runId || !(state.collapsedRunIds || []).includes(runId)) {
    return state;
  }
  return {
    ...state,
    collapsedRunIds: (state.collapsedRunIds || []).filter((item) => item !== runId),
  };
}

export function toggleInspectorRunGroupCollapsed(state, runId) {
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

export function expandInspectorRunGroup(state, runId) {
  if (!runId || !(state.collapsedInspectorRunIds || []).includes(runId)) {
    return state;
  }
  return {
    ...state,
    collapsedInspectorRunIds: (state.collapsedInspectorRunIds || []).filter((item) => item !== runId),
  };
}

export function summarizeDesktopText(value, maxChars = 120) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) {
    return "none";
  }
  if (text.length <= maxChars) {
    return text;
  }
  return `${text.slice(0, maxChars - 1)}...`;
}

export function summarizeRunGroup(group = {}) {
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

export function buildRunCopyArtifacts(group = {}) {
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

export function findLatestToolActivityForRun(toolActivity = [], runId) {
  if (!runId || !Array.isArray(toolActivity)) {
    return null;
  }
  return toolActivity.find((item) => item?.run_id === runId) || null;
}

export function groupRunInspectorItems(items = []) {
  const groups = [];
  for (const item of Array.isArray(items) ? items : []) {
    if (item?.run_id) {
      const existing = groups.find((group) => group.kind === "run" && group.run_id === item.run_id);
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
      id: item?.approval_id || item?.request_id || item?.tool_call_id || `inspector-${groups.length}`,
      items: [item],
    });
  }
  return groups;
}

export function applyToolActivitySnapshot(state, snapshot = {}) {
  const items = Array.isArray(snapshot?.items)
    ? JSON.parse(JSON.stringify(snapshot.items))
    : [];
  return {
    ...state,
    toolActivity: items,
    toolActivityStatus: snapshot?.status || (items.length > 0 ? state.toolActivityStatus : "No active tool run"),
  };
}

export function applyToolActivityEvent(state, event = {}) {
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

export function applyCoreEvent(state, event = {}) {
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

  if (
    topic === "permission.capability_grant.updated" ||
    topic === "permission.capability_grant.revoked"
  ) {
    return applyCapabilityGrants(withToolActivity, payload);
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
