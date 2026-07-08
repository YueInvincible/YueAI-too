# Yue Omni-Agent Checklist

## Purpose

This note is the current product/engineering checklist for moving Yue from a
chat dashboard toward a local-first desktop AI agent.

Priority order is fixed unless the user changes it:

1. Core agent runtime.
2. Desktop UI.
3. Permission/tool control.
4. Memory.
5. Plugin/tool ecosystem.
6. 3D avatar/model loading.
7. Release hardening.

## Direction Confirmed On 2026-07-08

- Yue should be a desktop AI agent, not a CLI-first clone.
- Codex is the reference for agent loop, sandbox/approval, task execution,
  code workflow, tool contracts, plugin/config discipline, and bounded context.
- Yue should extend that idea to whole-computer assistance: files, shell,
  browser, apps, mouse/keyboard, vision/screen, network/API, processes, and
  future community tools.
- The default experience should stay simple, with advanced settings hidden
  behind a clear advanced path.
- Core must load tools/plugins/personas safely so the community can extend Yue
  without core rewrites.
- 3D/avatar is important, but it comes after the agent core, permissions,
  memory, and plugin foundation are stable.

Reference points checked:

- `https://github.com/openai/codex`
- `https://raw.githubusercontent.com/openai/codex/main/AGENTS.md`
- `https://developers.openai.com/codex/config-advanced`
- `https://developers.openai.com/codex/security`

## Current State From Codebase Audit

- Core already has a usable agent skeleton:
  - `ConversationOrchestrator` with tool-call loop and run events.
  - Durable agent-run records via `SQLiteAgentRunStore`.
  - JSONL methods `agents.runs.start`, `agents.runs.get`, and
    `agents.runs.list`.
  - Structured agent-run checklist and verification state via
    `agents.runs.checklist.update` and `agents.runs.verification.update`.
  - Persona/provider snapshots plus tool/approval references recorded on agent
    runs from runtime events.
  - JSONL transport for desktop/core requests and events.
  - SQLite conversation history.
  - Provider routing by role: `chat` and `coding_agent`.
  - Prompt profiles with `personality`, `system_instruction`,
    `tool_instruction`, and `response_instruction`.
  - Built-in file/shell/process/git/package tools.
  - Permission profiles: `observe`, `assist`, `admin`.
  - Actor-aware policy for `model` vs `user/ui`.
  - Tool activity, approval bridge, audit log, legacy session shell grant, and
    first capability/resource-scoped session grants.
- Desktop already has a chat-first shell, provider settings, run inspector,
  tool contract display, and native Tauri bridge path.
- Desktop protocol/mock/runtime clients now expose `agents.runs.start/get/list`
  plus checklist/verification update wrappers, so future UI can call the new
  core agent-run surface.
- Plugin system exists but is local/trusted only:
  - discovers `*/plugin.json` under configured roots;
  - imports plugin Python in-process;
  - starts/stops plugins;
  - registers tools, services, and model providers.
- Memory/observer/persona marketplace/browser/vision/mouse/keyboard are not
  implemented as real systems yet.
- Docs currently still describe some old direction, including deferring avatar
  and not returning to VTube Studio. The corrected direction is: do not build a
  heavy VTube Studio clone, but investigate compatibility with common avatar
  formats/workflows where it stays lightweight.

## P0: Core Agent Runtime

- [x] Define an initial first-class agent run state machine separate from
  generic chat:
  `created -> planning -> inspecting -> acting -> waiting_approval -> verifying
  -> completed/failed/cancelled`.
- [x] Keep conversation chat and agent runs separate at the API level while
  allowing the UI to show them in one timeline.
- [x] Add a structured planner/checklist object owned by core, not only
  `todo.update` session state.
- [x] Add first durable run records with input, provider role, conversation id,
  status, plan seed, metadata, response message id, and error.
- [x] Extend durable run records with selected persona/prompt-profile snapshot.
- [x] Extend durable run records with provider route snapshot.
- [x] Record tool-call/tool-result references from runtime events.
- [x] Record approval pending/responded references from runtime events.
- [x] Add first verification state on durable run records:
  `not_run`, `running`, `passed`, `failed`, `skipped`.
- [ ] Add resumable runs after desktop/core restart.
- [ ] Add context compaction before memory is injected into model requests.
- [ ] Bound every model-visible fragment by token/char limits.
- [ ] Add integration tests for multi-step inspect/edit/verify flows.
- [ ] Avoid growing `app.py`, `conversation.py`, and `builtin_tools.py` further;
  split new concepts into dedicated modules.

## P0: Permission And Tool Control

- [ ] Replace the current small capability enum with a broader capability
  taxonomy:
  - `filesystem.read`
  - `filesystem.write`
  - `filesystem.delete`
  - `shell.exec`
  - `process.read`
  - `process.control`
  - `network.http`
  - `network.browser`
  - `browser.read`
  - `browser.control`
  - `app.launch`
  - `app.control`
  - `input.mouse`
  - `input.keyboard`
  - `screen.capture`
  - `screen.ocr`
  - `vision.analyze`
  - `clipboard.read`
  - `clipboard.write`
  - `audio.capture`
  - `audio.playback`
  - `memory.read`
  - `memory.write`
  - `plugin.install`
  - `plugin.enable`
  - `plugin.disable`
  - `system.settings`
  - `system.admin`
- [ ] Move policy from mostly tool-name rules to capability/resource rules.
- [x] Add first session grant model for capability/resource scopes, exposed over
  JSONL as `permissions.capability_grants.get/set` and wired into desktop
  protocol/mock/runtime clients.
- [x] Ensure capability/resource grants cannot bypass the active permission
  profile and cannot be changed by the `model` actor.
- [x] Add scoped grant revoke API and first lifetime enforcement:
  `once`, `run`, `conversation`, `session`.
- [x] Add first core resource scope taxonomy and inference:
  - workspace paths;
  - filesystem paths;
  - shell cwd;
  - network domains/local ports;
  - app names;
  - screen regions;
  - memory namespaces.
- [ ] Add advanced resource scope policy:
  - user-selected folders;
  - whole filesystem read;
  - whole filesystem write;
  - network domains;
  - local ports;
  - app names/window titles;
  - screen/monitor region;
  - memory namespaces.
- [x] Add initial approval/grant lifetimes:
  - once;
  - for this run;
  - for this conversation;
  - for this session.
- [ ] Add persistent approval/grant lifetimes:
  - always for this plugin/tool/resource scope.
- [ ] Add policy modes beyond `observe/assist/admin`:
  - `chat_only`;
  - `read_only`;
  - `workspace_agent`;
  - `desktop_assist`;
  - `full_control_with_approval`;
  - `trusted_admin`.
- [x] Add explicit denied-by-policy vs denied-by-user vs denied-by-missing-scope
  result categories.
- [ ] Add preflight/dry-run contracts for every side-effecting tool.
- [ ] Add structured command risk analysis before shell/app/input tools run.
- [ ] Add environment-variable redaction and allowlist policy for shell tools.
- [ ] Add audit retention and privacy controls before screen/memory tools.

## P0: Tool Core

- [ ] Keep built-in tools minimal but high quality; treat community plugins as
  the main expansion path.
- [ ] Add a tool registry surface that can expose:
  - capability;
  - risk;
  - resource scope;
  - mutates state;
  - parallel safety;
  - needs foreground focus;
  - needs user visibility;
  - supports dry run;
  - output bounds.
- [ ] Add tool categories for UI filtering:
  - files;
  - shell;
  - git;
  - process;
  - browser;
  - desktop apps;
  - input;
  - screen/vision;
  - network/API;
  - memory;
  - avatar;
  - developer.
- [ ] Add a stable remote-tool protocol path, preferably MCP-compatible or
  MCP-bridgeable, so existing tool servers can be reused.
- [ ] Add tool install/enable/disable/reload lifecycle events.
- [ ] Add health checks per tool/plugin, not only provider health.

## P1: Desktop UI

- [ ] Make the desktop shell the real control surface for agent runs, not only
  chat messages.
- [ ] Add a simple default settings view:
  - provider/model;
  - personality;
  - permission mode;
  - hotkey/wake word;
  - avatar/model path.
- [ ] Add advanced settings organized as folders/tabs:
  - providers;
  - prompts/personas;
  - tools;
  - plugins;
  - permissions;
  - memory/privacy;
  - avatar;
  - diagnostics.
- [ ] Add a permission center:
  - pending approvals;
  - granted scopes;
  - revoke buttons;
  - recent risky actions;
  - audit preview.
- [ ] Add plugin center:
  - installed plugins;
  - install from URL/repo/name;
  - plugin permissions;
  - update/remove/disable.
- [ ] Add persona center:
  - local personas;
  - import/export persona packs;
  - shareable metadata;
  - model/provider overrides per persona.
- [ ] Add memory center:
  - what Yue remembers;
  - delete/edit memories;
  - turn off categories;
  - private/sensitive memory controls.
- [ ] Resolve `desktop/src/app.js` vs `desktop/src/runtime.js` drift before
  adding large new desktop features.

## P1: Memory And Observer

- [ ] Implement memory as explicit stores, not hidden prompt stuffing:
  - working memory for current task/run;
  - episodic memory for events and user interactions;
  - semantic memory for facts/preferences;
  - persona/profile memory for character behavior.
- [ ] Add memory permissions:
  - read memory;
  - write memory;
  - remember this once;
  - always remember this type;
  - forget/delete.
- [ ] Add retention policy and searchable local indexes.
- [ ] Add source attribution for memories:
  - chat;
  - screen capture;
  - file;
  - browser;
  - user pinned.
- [ ] Add observer levels:
  - off;
  - app/window metadata only;
  - screenshot/OCR on demand;
  - vision on demand;
  - event-triggered observation.
- [ ] Do not add always-on vision until privacy, permission, retention, and UI
  controls exist.
- [ ] Add the example target flow:
  - user says "Hey Yue, look at this meme";
  - Yue requests/uses screen capture permission;
  - vision analysis creates an answer;
  - user can choose whether that interaction becomes memory.

## P1: Plugin Ecosystem

- [ ] Add plugin manifests with declared capabilities, resources, entrypoint,
  author, license, version, homepage/repo, checksum, and trust level.
- [ ] Add install from:
  - direct GitHub URL;
  - `owner/repo`;
  - curated index name;
  - local folder;
  - zip archive later.
- [ ] Add safe plugin install pipeline:
  - fetch metadata;
  - inspect manifest;
  - show requested permissions;
  - install disabled by default;
  - enable after user approval.
- [ ] Add plugin isolation. Current in-process plugin loading is only acceptable
  for first-party/trusted plugins.
- [ ] Add plugin update/uninstall/disable flows with rollback.
- [ ] Add plugin dependency declaration and compatibility checks against
  `CORE_API_VERSION`.
- [ ] Add a local plugin marketplace/index format so community tools/personas
  can be shared without hardcoding them into core.
- [ ] Add tests for malicious manifests:
  - entrypoint path escape;
  - duplicate IDs;
  - undeclared capability use;
  - plugin install without approval;
  - network fetch failure.

## P1: Personas / Character System

- [ ] Promote `prompt_profiles` into a shareable persona format rather than a
  few text fields only.
- [ ] Persona package should include:
  - id/name/version/author;
  - personality;
  - system style;
  - speech style;
  - boundaries;
  - example dialogues;
  - preferred model/provider;
  - avatar binding;
  - tool-use preferences;
  - memory policy.
- [ ] Support import/export of persona packs.
- [ ] Support per-persona permissions and tool restrictions.
- [ ] Add persona marketplace metadata independent from executable plugins.
- [ ] Keep copyrighted character personas user/community-provided; core should
  provide neutral schema and import mechanics.

## P2: 3D Avatar / VTube-Like Lightweight Path

- [ ] Treat avatar as a renderer-side feature with core state/events, not core
  business logic.
- [ ] Investigate avatar compatibility targets before implementation:
  - VRM 0.x/1.0 via Three.js and `@pixiv/three-vrm`;
  - Live2D/Cubism only if licensing/runtime weight is acceptable;
  - VTube Studio model workflow compatibility where practical;
  - custom loader adapter interface for community loaders.
- [ ] Add avatar state contract:
  - presence;
  - expression;
  - viseme/mouth shape;
  - gaze;
  - gesture/action;
  - idle animation;
  - tool-working animation.
- [ ] Add chat/tool/memory events that can drive expressions without coupling
  renderer to agent internals.
- [ ] Add basic model path/config UI first; advanced rigging later.
- [ ] Keep renderer lightweight and optional so Yue still runs without avatar.

## P2: Release Hardening

- [ ] Verify packaged desktop path after every bridge/runtime change.
- [ ] Add crash recovery for core child process.
- [ ] Add first-run setup wizard:
  - provider;
  - permission mode;
  - data/privacy location;
  - persona;
  - avatar optional.
- [ ] Add migration strategy for config and local database schema.
- [ ] Add telemetry/diagnostics as local-first and opt-in.
- [ ] Add export/import for config, personas, plugins list, and memory.
- [ ] Add release checklist that separates:
  - dev proof;
  - packaged proof;
  - installer proof;
  - cleanup/lifecycle proof;
  - privacy/security proof.

## Immediate Next Engineering Target

Do not start with new tools or 3D.

Start with the framework pieces that unlock everything else:

1. Add permission center UI for grant list/revoke and denied metadata display.
2. Design plugin install/manifest/trust lifecycle.
3. Expand resource taxonomy/inference as browser/app/screen/memory tools are designed.
4. Add persona package schema.
5. Add memory schema and privacy policy.
6. Only then implement browser/screen/input tools as plugins or first-party
   tool packages.
