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
  const consolePanel = document.querySelector("#console-panel");
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

  function render() {
    presenceLine.textContent = `${state.presence} / ${state.expression}`;
    windowLine.textContent = `anchor: ${state.windowAnchor} | hotkey: ${state.hotkey}`;
    sessionLine.textContent = `session: ${state.attachedSessionIds.join(", ") || "disconnected"}`;
    bridgeLine.textContent = `bridge: ${state.bridgeTransport} | core: ${state.bridgeProcessStarted ? "started" : "idle"}`;
    bridgeLine.title = state.bridgeLastError || state.bridgeNote;
    consolePanel.classList.toggle("hidden", !state.consoleOpen);

    messageLog.replaceChildren();
    for (const item of state.messages) {
      const row = document.createElement("article");
      row.className = `message-row role-${item.role}`;
      row.textContent = `${item.role}: ${item.text}`;
      messageLog.append(row);
    }
    messageLog.scrollTop = messageLog.scrollHeight;
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
