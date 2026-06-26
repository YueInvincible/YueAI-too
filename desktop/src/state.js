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
