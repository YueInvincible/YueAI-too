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
    default_provider: "localhost.chat",
    routes: {
      chat: { provider: "localhost.chat", prompt_profile: "default" },
      coding_agent: { provider: "localhost.chat", prompt_profile: "coding_agent" },
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
        provider_name: "localhost.chat",
        backend: "llama.cpp",
        base_url: "http://127.0.0.1:8080/v1",
        model: "Qwen3-4B-Q5_K_M.gguf",
        api_key_env: "",
        timeout_seconds: 120,
        health_timeout_seconds: 5,
        temperature: 0.7,
        max_tokens: 2048,
        headers: {},
      },
    ],
  };
  function buildActiveProviderSettings() {
    const provider = openaiCompatibleSettings.providers[0] || {
      provider_name: "localhost.chat",
      backend: "llama.cpp",
      base_url: "http://127.0.0.1:8080",
      model: "Qwen3-4B-Q5_K_M.gguf",
      api_key_env: "",
      timeout_seconds: 120,
      health_timeout_seconds: 5,
      temperature: 0.7,
      max_tokens: 2048,
      headers: {},
    };
    const kind = provider.backend === "anthropic" ? "anthropic" : provider.backend;
    return {
      single_provider_mode: true,
      active_provider: {
        kind,
        label: kind === "llama.cpp" ? "Local llama.cpp" : provider.backend,
        family: ["llama.cpp", "ollama", "lmstudio", "custom"].includes(kind) ? "local" : "cloud",
        plugin_id: kind === "anthropic" ? "anthropic.messages" : "openai.compat",
        provider_name: provider.provider_name,
        backend: provider.backend,
        base_url: provider.base_url,
        host: "127.0.0.1",
        port: 8080,
        model: provider.model,
        api_key_env: provider.api_key_env || "",
        timeout_seconds: provider.timeout_seconds,
        health_timeout_seconds: provider.health_timeout_seconds,
        temperature: provider.temperature,
        max_tokens: provider.max_tokens,
        headers: provider.headers || {},
        anthropic_version: provider.anthropic_version || "2023-06-01",
      },
      provider_options: [
        { kind: "llama.cpp", label: "Local llama.cpp" },
        { kind: "ollama", label: "Ollama" },
        { kind: "lmstudio", label: "LM Studio" },
        { kind: "custom", label: "Custom OpenAI-compatible" },
        { kind: "openai", label: "OpenAI" },
        { kind: "google", label: "Google AI" },
        { kind: "openrouter", label: "OpenRouter" },
        { kind: "anthropic", label: "Anthropic" },
      ],
      conversation: JSON.parse(JSON.stringify(conversationSettings)),
    };
  }
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
  let allowAllCmdGrant = {
    session_id: "desktop-preview",
    allow_all_cmd: false,
    updated_by: "none",
  };
  let toolActivitySnapshot = {
    items: [
      {
        run_id: "mock-run-1",
        conversation_id: "mock-conversation-1",
        tool_call_id: "mock-call-1",
        request_id: "mock-request-1",
        tool_name: "shell.run",
        arguments: {
          command: "git push origin feature/desktop-bridge",
        },
        status: "waiting_approval",
        output: null,
        error: "Command requires explicit approval",
        approval_id: "mock-approval-1",
      },
    ],
    status: "Approval requested for shell.run",
  };
  const toolCatalog = [
    {
      name: "workspace.read",
      description: "Read a UTF-8 workspace file with line-range metadata.",
      input_schema: {},
      capability: "file.read",
      risk: "low",
      plugin_id: "core",
      output_kind: "file_content",
      metadata: {
        output_kind: "file_content",
        parallel_safe: true,
        mutates_state: false,
      },
    },
    {
      name: "workspace.grep",
      description: "Search workspace file contents by literal string or regex.",
      input_schema: {},
      capability: "file.read",
      risk: "low",
      plugin_id: "core",
      output_kind: "structured",
      metadata: {
        output_kind: "structured",
        parallel_safe: true,
        mutates_state: false,
      },
    },
    {
      name: "shell.run",
      description: "Run a shell command with explicit cwd, timeout, and risk metadata.",
      input_schema: {},
      capability: "shell.execute",
      risk: "high",
      plugin_id: "core",
      output_kind: "command_output",
      metadata: {
        output_kind: "command_output",
        parallel_safe: false,
        mutates_state: true,
      },
    },
  ];
  const toolGuide = {
    provider_role: "coding_agent",
    workflow: [
      "Start with read-only inspection. Read or search narrowly before editing.",
      "Use parallel reads only for independent inspection calls that are marked parallel-safe.",
      "Keep edits and shell actions sequential. Re-read affected files after non-trivial changes.",
      "Use approval before proposing or attempting risky actions outside the normal edit flow.",
      "Verify with the smallest command or diff that proves the change.",
    ],
    tools: [
      {
        name: "workspace_read",
        summary: "Read file content with optional line bounds.",
        when_to_use: "Use for exact inspection after locating the target file.",
        avoid_when: "Do not read huge files blindly; narrow by path or line range first.",
        output_kind: "file_content",
        parallel_safe: true,
        mutates_state: false,
        risk: "low",
      },
      {
        name: "workspace_edit",
        summary: "Replace an exact block in one workspace file.",
        when_to_use: "Use for surgical edits with known search text.",
        avoid_when: "Do not use until you have read the target file and confirmed the exact block.",
        output_kind: "structured",
        parallel_safe: false,
        mutates_state: true,
        risk: "medium",
      },
      {
        name: "shell_run",
        summary: "Run a one-shot shell command with timeout and sanitized output.",
        when_to_use: "Use for verification, build/test commands, or targeted repo inspection not covered by workspace tools.",
        avoid_when: "Do not use before cheaper file reads/searches. Avoid destructive commands unless explicitly requested.",
        output_kind: "command_output",
        parallel_safe: false,
        mutates_state: true,
        risk: "high",
      },
    ],
    text: "Coding agent tool guide:\n- Start with read-only inspection. Read or search narrowly before editing.",
  };
  const promptPreview = {
    provider_role: "coding_agent",
    prompt_profile: "coding_agent",
    system_instruction:
      "System:\nYou are responsible for implementing code changes safely and validating them with real checks.\n\nTool usage:\nInspect relevant files before editing.\n\nCoding agent tool guide:\n- Start with read-only inspection.",
    tool_count: 3,
  };
  const agentBundle = {
    provider_role: "coding_agent",
    default_provider: "localhost.chat",
    route: {
      provider: "localhost.chat",
      prompt_profile: "coding_agent",
    },
    active_provider: {
      kind: "llama.cpp",
      provider_name: "localhost.chat",
      model: "Qwen3-4B-Q5_K_M.gguf",
    },
    prompt_preview: promptPreview,
    tool_guide: toolGuide,
    codex_manifest: {
      provider_role: "coding_agent",
      system_prompt: promptPreview.system_instruction,
      tool_instructions: toolGuide.workflow,
      approval_rules: {
        profile: "assist",
        interactive_approval: true,
        dangerous_model_actions_blocked_in_assist: true,
      },
      parallel_rules: {
        read_only_parallel_only: true,
        writes_and_shell_sequential: true,
      },
      tools: toolGuide.tools.map((item) => ({
        name: item.name,
        when_to_use: item.when_to_use,
        avoid_when: item.avoid_when,
        parallel_safe: item.parallel_safe,
        mutates_state: item.mutates_state,
        risk: item.risk,
      })),
    },
    tools: toolCatalog,
  };
  const agentStarterPack = {
    provider_role: "coding_agent",
    name: "YueAI coding_agent starter pack",
    summary: "Copy-ready prompt and tool rules for wiring another coding-agent client.",
    starter_prompt:
      "You are a coding agent attached to the YueAI runtime.\nFollow the system prompt and tool manifest below.\nDo not rename tools, widen permissions, or parallelize state-changing actions.\nWhen uncertain, inspect first and ask the user before destructive or ambiguous steps.",
    system_prompt: promptPreview.system_instruction,
    codex_manifest: agentBundle.codex_manifest,
    tool_manifest_json: JSON.stringify(agentBundle.codex_manifest, null, 2),
    integration_checklist: [
      "Load the system prompt exactly as provided before the first user turn.",
      "Register tools with the exact filtered names from the manifest.",
      "Treat read-only tools as the only safe parallel batch; keep writes and shell actions sequential.",
      "Preserve approval boundaries from the manifest before any risky action.",
      "Prefer inspect -> edit -> verify, and ask the user when intent or blast radius is unclear.",
    ],
    text:
      "# YueAI coding_agent starter pack\n\nUse this pack when wiring another agent client to the YueAI runtime.\n\n## Starter prompt\n```text\nYou are a coding agent attached to the YueAI runtime.\nFollow the system prompt and tool manifest below.\nDo not rename tools, widen permissions, or parallelize state-changing actions.\nWhen uncertain, inspect first and ask the user before destructive or ambiguous steps.\n```\n\n## Runtime system prompt\n```text\n"
      + promptPreview.system_instruction
      + "\n```\n\n## Integration checklist\n- Load the system prompt exactly as provided before the first user turn.\n- Register tools with the exact filtered names from the manifest.\n- Treat read-only tools as the only safe parallel batch; keep writes and shell actions sequential.\n- Preserve approval boundaries from the manifest before any risky action.\n- Prefer inspect -> edit -> verify, and ask the user when intent or blast radius is unclear.\n\n## Codex-style tool manifest\n```json\n"
      + JSON.stringify(agentBundle.codex_manifest, null, 2)
      + "\n```",
  };

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
          toolActivitySnapshot = {
            items: toolActivitySnapshot.items.map((item) =>
              item.approval_id === params.approval_id
                ? {
                    ...item,
                    status: params.approved ? "approved_pending_run" : "denied_by_user",
                    error: params.approved ? null : "Denied by user approval",
                  }
                : item,
            ),
            status: params.approved ? `Approved ${match.tool_name}` : `Denied ${match.tool_name}`,
          };
          return {
            ...JSON.parse(JSON.stringify(match)),
            approved: Boolean(params.approved),
          };
        }
        case "tool.activity.snapshot":
          return JSON.parse(JSON.stringify(toolActivitySnapshot));
        case "tools.list":
          return JSON.parse(JSON.stringify(toolCatalog));
        case "tools.guide":
          return JSON.parse(JSON.stringify(toolGuide));
        case "agents.bundle":
          return JSON.parse(JSON.stringify(agentBundle));
        case "agents.starter_pack":
          if (params?.format) {
            const format = String(params.format);
            const slices = {
              text: agentStarterPack.text,
              json: JSON.stringify(agentStarterPack, null, 2),
              "manifest-json": agentStarterPack.tool_manifest_json,
              "system-prompt": agentStarterPack.system_prompt,
              "starter-prompt": agentStarterPack.starter_prompt,
              checklist: agentStarterPack.integration_checklist.map((item) => `- ${item}`).join("\n"),
            };
            if (!(format in slices)) {
              throw new Error(`Unsupported starter pack format: ${format}`);
            }
            return {
              provider_role: params.provider_role || "coding_agent",
              format,
              content: slices[format],
            };
          }
          return JSON.parse(JSON.stringify(agentStarterPack));
        case "tools.invoke_many":
          return {
            parallel: Boolean(params.parallel),
            results: (params.calls || []).map((call, index) => ({
              request_id: `mock-batch-${index + 1}`,
              tool_name: call.name,
              status: "succeeded",
              output:
                call.name === "workspace.read"
                  ? {
                      path: call.arguments?.path || "",
                      content: `Mock content for ${call.arguments?.path || "unknown path"}`,
                      start_line: call.arguments?.start_line || 1,
                      end_line: call.arguments?.end_line || 1,
                      total_lines: 1,
                      returned_lines: 1,
                      truncated: false,
                    }
                  : {
                      ok: true,
                    },
              error: null,
            })),
          };
        case "permissions.allow_all_cmd.get":
          if (params.session_id !== allowAllCmdGrant.session_id) {
            return {
              session_id: params.session_id,
              allow_all_cmd: false,
              updated_by: "none",
            };
          }
          return JSON.parse(JSON.stringify(allowAllCmdGrant));
        case "permissions.allow_all_cmd.set":
          allowAllCmdGrant = {
            session_id: params.session_id,
            allow_all_cmd: Boolean(params.allowed),
            updated_by: params.actor || "desktop-ui",
          };
          return JSON.parse(JSON.stringify(allowAllCmdGrant));
        case "providers.list":
          return [
            ...openaiCompatibleSettings.providers.map((item) => item.provider_name),
            ...anthropicMessagesSettings.providers.map((item) => item.provider_name),
          ];
        case "providers.health":
          return [
            {
              provider: "localhost.chat",
              ok: true,
              reachable: true,
              backend: "llama.cpp",
              model: "Qwen3-4B-Q5_K_M.gguf",
              model_available: true,
              models: ["Qwen3-4B-Q5_K_M.gguf"],
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
        case "settings.providers.active.get":
          return JSON.parse(JSON.stringify(buildActiveProviderSettings()));
        case "settings.providers.active.catalog": {
          const next = JSON.parse(JSON.stringify((params && params.provider) || {}));
          const kind = String(next.kind || next.backend || "llama.cpp");
          const modelsByKind = {
            "llama.cpp": ["Qwen3-4B-Q5_K_M.gguf"],
            ollama: ["qwen2.5:7b-instruct", "qwen2.5-coder:7b"],
            lmstudio: ["openai/gpt-oss-20b", "qwen2.5-coder-7b-instruct"],
            custom: ["custom-model"],
            openai: ["gpt-4.1-mini", "gpt-4.1"],
            google: ["gemini-2.5-flash", "gemini-2.5-pro"],
            openrouter: ["openai/gpt-4.1-mini", "anthropic/claude-sonnet-4"],
            anthropic: ["claude-sonnet-4-20250514", "claude-3-7-sonnet-latest"],
          };
          const models = modelsByKind[kind] || [];
          return {
            kind,
            provider_name: next.provider_name || `${kind}.chat`,
            models,
            selected_model: next.model || models[0] || "",
            reachable: true,
            ok: true,
            error: null,
            auto_selected: !next.model && Boolean(models[0]),
          };
        }
        case "settings.providers.active.update": {
          const next = JSON.parse(JSON.stringify((params && params.provider) || {}));
          const kind = String(next.kind || next.backend || "llama.cpp");
          const backend = kind === "anthropic" ? "anthropic" : kind;
          const baseUrl = next.base_url || (
            kind === "llama.cpp"
              ? `http://${next.host || "127.0.0.1"}:${next.port || 8080}`
              : ["ollama", "lmstudio", "custom"].includes(kind)
                ? `http://${next.host || "127.0.0.1"}:${next.port || (kind === "ollama" ? 11434 : kind === "lmstudio" ? 1234 : 8080)}/v1`
                : kind === "anthropic"
                  ? "https://api.anthropic.com"
                  : kind === "google"
                    ? "https://generativelanguage.googleapis.com/v1beta/openai"
                    : kind === "openrouter"
                      ? "https://openrouter.ai/api/v1"
                      : "https://api.openai.com/v1"
          );
          const provider = {
            provider_name: next.provider_name || `${kind}.chat`,
            backend,
            base_url: baseUrl,
            model: next.model || "mock-model",
            api_key_env: next.api_key_env || "",
            timeout_seconds: Number(next.timeout_seconds || 120),
            health_timeout_seconds: Number(next.health_timeout_seconds || 5),
            temperature: Number(next.temperature || 0.7),
            max_tokens: Number(next.max_tokens || 1024),
            headers: {},
          };
          if (kind === "anthropic") {
            anthropicMessagesSettings = {
              providers: [
                {
                  ...provider,
                  anthropic_version: next.anthropic_version || "2023-06-01",
                },
              ],
            };
          } else {
            openaiCompatibleSettings = {
              providers: [provider],
            };
          }
          conversationSettings.default_provider = provider.provider_name;
          conversationSettings.routes.chat.provider = provider.provider_name;
          conversationSettings.routes.coding_agent.provider = provider.provider_name;
          return JSON.parse(JSON.stringify(buildActiveProviderSettings()));
        }
        case "conversations.create":
          conversationCounter += 1;
          return { id: `mock-conversation-${conversationCounter}` };
        case "conversations.prompt_preview":
          return JSON.parse(JSON.stringify(promptPreview));
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
