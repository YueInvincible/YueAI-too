function randomId() {
  return `bridge-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createRequestEnvelope(method, params = {}) {
  return {
    id: randomId(),
    method,
    params,
  };
}

export function parseJsonlMessage(line) {
  const trimmed = String(line).replace(/^\uFEFF/, "").trim();
  if (!trimmed) {
    return null;
  }
  return JSON.parse(trimmed);
}

export class JsonlMessageRouter {
  constructor() {
    this.pending = new Map();
    this.eventListeners = new Set();
  }

  createPendingRequest(envelope) {
    if (!envelope?.id) {
      throw new Error("request envelope id is required");
    }
    if (this.pending.has(envelope.id)) {
      throw new Error(`duplicate pending request id: ${envelope.id}`);
    }
    return new Promise((resolve, reject) => {
      this.pending.set(envelope.id, { resolve, reject, envelope });
    });
  }

  onEvent(listener) {
    if (typeof listener !== "function") {
      throw new TypeError("listener must be a function");
    }
    this.eventListeners.add(listener);
    return () => {
      this.eventListeners.delete(listener);
    };
  }

  handleLine(line) {
    const message = parseJsonlMessage(line);
    if (message === null) {
      return { type: "ignore" };
    }
    if (message.event) {
      for (const listener of this.eventListeners) {
        listener(message.event);
      }
      return { type: "event", event: message.event };
    }
    if (!message.id) {
      throw new Error("response message id is required");
    }
    const pending = this.pending.get(message.id);
    if (!pending) {
      return { type: "orphan_response", response: message };
    }
    this.pending.delete(message.id);
    if (message.ok) {
      pending.resolve(message.result);
      return { type: "response", ok: true, response: message };
    }
    pending.reject(new Error(message.error || "bridge request failed"));
    return { type: "response", ok: false, response: message };
  }

  rejectAll(error) {
    for (const [id, pending] of this.pending) {
      pending.reject(error instanceof Error ? error : new Error(String(error)));
      this.pending.delete(id);
    }
  }
}
