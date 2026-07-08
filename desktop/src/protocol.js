const DEFAULT_TIMEOUT_MS = 15000;

export class CoreProtocolClient {
  constructor(transport) {
    if (!transport || typeof transport.request !== "function") {
      throw new TypeError("transport.request is required");
    }
    this.transport = transport;
  }

  desktopState() {
    return this.#request("desktop.state");
  }

  desktopAttach(sessionId, metadata = {}) {
    return this.#request("desktop.attach", { session_id: sessionId, metadata });
  }

  desktopDetach(sessionId) {
    return this.#request("desktop.detach", { session_id: sessionId });
  }

  desktopCommand(command, value, source = "desktop-ui") {
    const params = { command, source };
    if (value !== undefined) {
      params.value = value;
    }
    return this.#request("desktop.command", params);
  }

  requestApproval(actionDescription, riskLevel, actor = "desktop-ui", sessionId) {
    const params = {
      action_description: actionDescription,
      risk_level: riskLevel,
      actor,
    };
    if (sessionId) {
      params.session_id = sessionId;
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

  getToolsGuide(options = {}) {
    return this.#request("tools.guide", {
      provider_role: options.providerRole,
    });
  }

  getAgentBundle(options = {}) {
    return this.#request("agents.bundle", {
      provider_role: options.providerRole || "coding_agent",
    });
  }

  getAgentStarterPack(options = {}) {
    return this.#request("agents.starter_pack", {
      provider_role: options.providerRole || "coding_agent",
      format: options.format,
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

  getAllowAllCmd(sessionId) {
    return this.#request("permissions.allow_all_cmd.get", {
      session_id: sessionId,
    });
  }

  setAllowAllCmd(sessionId, allowed, actor = "desktop-ui") {
    return this.#request("permissions.allow_all_cmd.set", {
      session_id: sessionId,
      allowed: Boolean(allowed),
      actor,
    });
  }

  createConversation(title = "Yue Desktop") {
    return this.#request("conversations.create", { title });
  }

  getConversationPromptPreview(options = {}) {
    return this.#request("conversations.prompt_preview", {
      provider_role: options.providerRole || "chat",
    });
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

export function createMessage(role, text) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
  };
}
