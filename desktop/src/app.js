import { CoreProtocolClient, createMessage } from "./protocol.js";
import {
  appendMessage,
  applyBridgeRuntime,
  applyCoreEvent,
  applyDesktopSnapshot,
  defaultDesktopViewState,
  setConversationId,
} from "./state.js";
import { createMockTransport } from "./mock.js";
import {
  TauriEventPump,
  createPreferredTransport,
  createTauriBridgeCommands,
  detectTauriInvoke,
} from "./tauriTransport.js";

const sessionId = "desktop-preview";

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

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function waitForTauriInvoke(globalObject, { attempts = 20, intervalMs = 100 } = {}) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const invoke = detectTauriInvoke(globalObject);
    if (invoke) {
      return invoke;
    }
    await delay(intervalMs);
  }
  return null;
}

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
  const tauriInvoke = await waitForTauriInvoke(window);
  bridgeCommands = tauriInvoke ? createTauriBridgeCommands({ invoke: tauriInvoke }) : null;
  usingNativeBridge = Boolean(bridgeCommands);
  client = new CoreProtocolClient(
    tauriInvoke ? createPreferredTransport(window, fallbackTransport) : fallbackTransport,
  );

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
  const attached = await client.desktopAttach(sessionId, { surface: "preview" });
  state = applyDesktopSnapshot(state, attached.state);
  if (bridgeCommands) {
    pendingRuntimeInfo = await bridgeCommands.runtimeInfo();
    state = applyBridgeRuntime(state, pendingRuntimeInfo);
  }
  render();
  if (bridgeCommands && pendingRuntimeInfo?.diagnostic_enabled) {
    await bridgeCommands.reportDiagnostic({
      readyState: document.readyState,
      hasTauri: typeof window.__TAURI__ !== "undefined",
      hasInternals: typeof window.__TAURI_INTERNALS__ !== "undefined",
      hasInvoke: typeof window.__TAURI_INTERNALS__?.invoke === "function",
      hasIpc: typeof window.__TAURI_INTERNALS__?.ipc === "function",
      bridgeLine: bridgeLine.textContent,
      autoExitMs: pendingRuntimeInfo.diagnostic_auto_exit_ms ?? null,
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
  state = applyDesktopSnapshot(state, (await client.desktopState()));
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
    await client.desktopDetach(sessionId);
    if (bridgeCommands) {
      await bridgeCommands.shutdownCore();
    }
  } catch {
    return;
  }
});

bootstrap();
