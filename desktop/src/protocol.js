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
