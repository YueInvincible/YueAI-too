function normalizeBridgeResponse(response) {
  if (!response || typeof response !== "object") {
    throw new Error("Invalid bridge response");
  }
  if (response.ok) {
    return response.result;
  }
  throw new Error(response.error || "Bridge request failed");
}

export function createTauriTransport({ invoke }) {
  if (typeof invoke !== "function") {
    throw new TypeError("invoke is required");
  }
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

export function createTauriBridgeCommands({ invoke }) {
  if (typeof invoke !== "function") {
    throw new TypeError("invoke is required");
  }
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

export function detectTauriInvoke(globalObject = globalThis) {
  if (typeof globalObject?.__TAURI__?.core?.invoke === "function") {
    return globalObject.__TAURI__.core.invoke;
  }
  if (typeof globalObject?.__TAURI_INTERNALS__?.invoke === "function") {
    return globalObject.__TAURI_INTERNALS__.invoke;
  }
  return null;
}

export function createPreferredTransport(globalObject, fallbackTransport) {
  const invoke = detectTauriInvoke(globalObject);
  if (invoke) {
    return createTauriTransport({ invoke });
  }
  return fallbackTransport;
}

export class TauriEventPump {
  constructor({ commands, onEvent, intervalMs = 250 }) {
    if (!commands || typeof commands.drainEvents !== "function") {
      throw new TypeError("commands.drainEvents is required");
    }
    if (typeof onEvent !== "function") {
      throw new TypeError("onEvent is required");
    }
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
    this.timer = setInterval(() => {
      void this.tick();
    }, this.intervalMs);
    void this.tick();
  }

  stop() {
    this.running = false;
    if (this.timer) {
      clearInterval(this.timer);
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
