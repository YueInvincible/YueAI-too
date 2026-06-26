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

export function createMessage(role, text) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
  };
}
