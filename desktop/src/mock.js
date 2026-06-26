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
  let conversationSettings = {
    default_provider: "fake.echo",
    routes: {
      chat: { provider: "fake.echo", prompt_profile: "default" },
      coding_agent: { provider: "fake.echo", prompt_profile: "coding_agent" },
    },
    prompt_profiles: {
      default: {
        personality: "Local-first assistant.",
        system_instruction: "",
        tool_instruction: "",
        response_instruction: "",
      },
      coding_agent: {
        personality: "Senior coding agent.",
        system_instruction: "",
        tool_instruction: "",
        response_instruction: "",
      },
    },
  };
  let openaiCompatibleSettings = {
    providers: [
      {
        provider_name: "ollama.chat",
        backend: "ollama",
        base_url: "http://127.0.0.1:11434/v1",
        model: "qwen2.5:7b-instruct",
        api_key_env: "",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.6,
        max_tokens: 1024,
        headers: {},
      },
    ],
  };
  let anthropicMessagesSettings = {
    providers: [
      {
        provider_name: "claude.coder",
        backend: "anthropic",
        base_url: "https://api.anthropic.com",
        model: "claude-sonnet-4-20250514",
        api_key_env: "ANTHROPIC_API_KEY",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.2,
        max_tokens: 2048,
        anthropic_version: "2023-06-01",
        headers: {},
      },
    ],
  };
  let pendingApprovals = [
    {
      approval_id: "mock-approval-1",
      request_id: "mock-request-1",
      tool_name: "shell.run",
      actor: "desktop-preview",
      session_id: "desktop-preview",
      reason: "Command requires explicit approval",
      risk_level: "high",
      arguments: {
        command: "git push origin feature/desktop-bridge",
      },
      created_at: now(),
    },
  ];

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
        case "approval.request": {
          const approval = {
            approval_id: `mock-approval-${pendingApprovals.length + 1}`,
            request_id: `mock-request-${pendingApprovals.length + 1}`,
            tool_name: "approval.request",
            actor: params.actor || "desktop-ui",
            session_id: params.session_id || null,
            reason: params.action_description,
            risk_level: params.risk_level,
            arguments: {
              action_description: params.action_description,
            },
            created_at: now(),
          };
          pendingApprovals = [...pendingApprovals, approval];
          return { approved: false, pending: approval };
        }
        case "approval.pending.list":
          return JSON.parse(JSON.stringify(pendingApprovals));
        case "approval.respond": {
          const match = pendingApprovals.find((item) => item.approval_id === params.approval_id);
          if (!match) {
            throw new Error(`Unknown approval request: ${params.approval_id}`);
          }
          pendingApprovals = pendingApprovals.filter(
            (item) => item.approval_id !== params.approval_id,
          );
          return {
            ...JSON.parse(JSON.stringify(match)),
            approved: Boolean(params.approved),
          };
        }
        case "providers.list":
          return [
            "fake.echo",
            ...openaiCompatibleSettings.providers.map((item) => item.provider_name),
            ...anthropicMessagesSettings.providers.map((item) => item.provider_name),
          ];
        case "providers.health":
          return [
            {
              provider: "fake.echo",
              ok: true,
              reachable: true,
              backend: "fake",
            },
          ];
        case "settings.conversation.get":
          return JSON.parse(JSON.stringify(conversationSettings));
        case "settings.conversation.update":
          conversationSettings = JSON.parse(
            JSON.stringify(
              Object.fromEntries(
                Object.entries(params).filter(([key]) => key !== "persist"),
              ),
            ),
          );
          return JSON.parse(JSON.stringify(conversationSettings));
        case "settings.providers.openai_compat.get":
          return JSON.parse(JSON.stringify(openaiCompatibleSettings));
        case "settings.providers.openai_compat.update":
          openaiCompatibleSettings = JSON.parse(
            JSON.stringify(
              Object.fromEntries(
                Object.entries(params).filter(([key]) => key !== "persist"),
              ),
            ),
          );
          return JSON.parse(JSON.stringify(openaiCompatibleSettings));
        case "settings.providers.anthropic_messages.get":
          return JSON.parse(JSON.stringify(anthropicMessagesSettings));
        case "settings.providers.anthropic_messages.update":
          anthropicMessagesSettings = JSON.parse(
            JSON.stringify(
              Object.fromEntries(
                Object.entries(params).filter(([key]) => key !== "persist"),
              ),
            ),
          );
          return JSON.parse(JSON.stringify(anthropicMessagesSettings));
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
