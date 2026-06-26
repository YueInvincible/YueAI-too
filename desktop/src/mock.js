import { createMessage } from "./protocol.js";

function now() {
  return new Date().toISOString();
}

function defaultState() {
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

export function createMockTransport() {
  const state = defaultState();
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
        case "providers.list":
          return ["fake.echo"];
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

function reduceDesktopCommand(state, command, value) {
  if (command === "avatar.click" || command === "console.toggle" || command === "hotkey.toggle_console") {
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
