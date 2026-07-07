# YueAI Project Handoff

File nay chi la muc luc ngan. Khong dua chi tiet dai vao day.

Chi giu 3 thu:
- muc tieu chinh;
- yeu cau chung cho agent sau;
- danh sach note can doc theo tung domain + next target.

## Muc tieu chinh

- Tiep tuc xay YueAI theo huong desktop local-first.
- Huong hien tai van la desktop shell Tauri + native bridge toi `yue_core`.
- Uu tien hien tai la hoan thanh core chat/runtime/tooling cho agent truoc khi mo rong them UX provider rieng.
- Local path uu tien cao nhat la local host OpenAI-compatible server tai `http://127.0.0.1:8080/v1` theo flow `yue.py`; `LM Studio` la path phu.
- Re-check ngay `2026-07-06`: `llama-server.exe` da duoc chay that tai `127.0.0.1:8080`; file `C:\Users\Yue\Downloads\llama\cmd.txt` dang tro toi model `30b` khong ton tai, con model GGUF co that tren may la `D:\!AI_Models\qwen\qwen3-4B-Q5_K_M\Qwen3-4B-Q5_K_M.gguf`.
- Re-check ngay `2026-07-06`: `config.example.toml` da duoc canh khop runtime that:
  - `default_provider = "localhost.chat"`
  - `plugins.options."llama.cpp".model = "Qwen3-4B-Q5_K_M.gguf"`
- Re-check ngay `2026-07-06`: chat that da verify duoc qua:
  - CLI `python -m yue_core --config config.example.toml chat ...`
  - `providers-health`
  - `desktop-demo --headless-smoke-test`
- Chua duoc xem la xong cho cac phan: non-dev frontend path, lifecycle hardening, renderer/VRM, memory/observer, permissions, voice.

## Yeu cau chung cho agent sau

- Khong mo rong file handoff nay thanh tai lieu dai.
- Khong doc toan bo `docs/` theo kieu tuan tu. Handoff nay chi dung de chon nhanh 1 nhanh note lien quan.
- Truoc khi lam domain nao, chi doc note domain do va cac note phu thuoc truc tiep.
- Git workflow cho repo nay:
  - khong tao branch moi;
  - lam viec truc tiep tren `main`;
  - sau khi hoan thanh thay doi va verify, phai `git push` len `origin/main`.
- Lam xong gi chi note `done` khi da verify bang lenh/test that.
- Neu chua chac chan, phai ghi ro vao note cua domain do:
  - dieu gi da xac nhan;
  - dieu gi con nghi ngo;
  - file nao can mo tiep;
  - lenh nao can chay lai.
- Sau moi dot lam viec:
  - cap nhat note domain lien quan;
  - cap nhat file nay neu thu tu uu tien hoac next target thay doi.
- Neu thay thong tin cu trong handoff da duoc tach ra note rieng, khong xoa y nghia cua no; chi chuyen no sang note phu hop.
- Neu task lien quan desktop shell, provider routing, JSONL transport, runtime editor, hoac provider health:
  - doc `agent_start_here.md` truoc;
  - sau do doc `runtime_flow_map.md`;
  - chi sau do moi mo code dung domain de tranh phi token.
- Neu can chuan bi cho agent tiep theo, doc them `docs/notes/agent_roadmap.md` truoc khi mo code.

## Chien luoc load docs toi thieu

- Bat dau bang:
  - `PROJECT_HANDOFF.md`
  - `docs/notes/agent_start_here.md`
- Sau do chi chon 1 nhanh chinh:
  - core/tooling
  - provider/runtime
  - desktop shell/bridge
  - product/roadmap
- `docs/*.md` o root chu yeu la reference docs theo domain protocol/provider.
  Khong nen mo chung tru khi note trong `docs/notes/` chi dinh ro.

## Chi muc note

- Product direction:
  - [docs/notes/product_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\product_direction.md)
- Desktop bridge status:
  - [docs/notes/desktop_bridge_status.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\desktop_bridge_status.md)
- Desktop debug pitfalls:
  - [docs/notes/desktop_debug_pitfalls.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\desktop_debug_pitfalls.md)
- Validation commands:
  - [docs/notes/validation_commands.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\validation_commands.md)
- Hardware constraints:
  - [docs/notes/hardware_constraints.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\hardware_constraints.md)
- Model/runtime direction:
  - [docs/notes/model_runtime_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\model_runtime_direction.md)
- Provider and prompt config:
  - [docs/notes/provider_and_prompt_config.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\provider_and_prompt_config.md)
- Runtime flow map:
  - [docs/notes/runtime_flow_map.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\runtime_flow_map.md)
- Agent start-here:
  - [docs/notes/agent_start_here.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\agent_start_here.md)
- Voice deferred scope:
  - [docs/notes/voice_deferred_scope.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\voice_deferred_scope.md)
- Permissions and safety:
  - [docs/notes/permissions_and_safety.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\permissions_and_safety.md)
- Memory and observer roadmap:
  - [docs/notes/memory_and_observer_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\memory_and_observer_roadmap.md)
- Agent roadmap:
  - [docs/notes/agent_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\agent_roadmap.md)
- App development roadmap:
  - [docs/notes/app_development_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\app_development_roadmap.md)
- Tool activity reconnect issue:
  - [docs/notes/tool_activity_reconnect_issue.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\tool_activity_reconnect_issue.md)

## Trang thai tong quan

- Da co desktop session protocol, desktop demo, va JSONL transport cho `desktop.*` + `conversation.*` + `approval.*`.
- Workspace `desktop/` da co frontend shell, Rust native bridge, JS/Rust tests, va debug-window proof khi preview server dang chay.
- Desktop native bridge gio da uu tien nap config runtime cua repo theo thu tu:
  - `YUE_CORE_CONFIG`
  - `config.local.toml`
  - `config.example.toml`
  - roi moi fallback default core settings.
- Diagnostic harness cho packaged bootstrap da duoc tang muc chi tiet:
  - co retry probe tu `main.rs`
  - co them stage `probe_dispatching`, `probe_dispatched`, `probe_timeout`
  - payload callback co them `locationHref`
  - muc dich la phan biet ro packaged NSIS dang ket o callback eval, page load, hay runtime bootstrap
- Core da co provider routing theo role (`chat`, `coding_agent`) va prompt-profile config (`personality`, `system_instruction`, `tool_instruction`, `response_instruction`).
- Core da co plugin `openai.compat` de cau hinh:
  - OpenAI;
  - Google AI / Gemini qua OpenAI compatibility;
  - OpenRouter;
  - Ollama;
  - LM Studio;
  - llama.cpp;
  - custom OpenAI-compatible endpoint.
- Core da co plugin `anthropic.messages` cho Claude direct qua Anthropic Messages API.
- Core da co provider health-check qua `providers.health` va CLI `providers-health`.
- Core da co tool surface built-in cho agent:
  - `file.read`
  - `file.list`
  - `file.search`
  - `file.write`
  - `file.edit`
  - `file.move`
  - `file.delete`
  - `shell.exec`
  - `process.list`
  - `process.kill`
  - `git.status`
  - `git.diff`
  - `package.install`
- Core da co them lop tool alias/surface gan hon voi coding-agent workflow:
  - alias underscore duoc uu tien cho `coding_agent`:
    - `workspace_list`
    - `workspace_read`
    - `workspace_search`
    - `workspace_grep`
    - `workspace_write`
    - `workspace_edit`
    - `workspace_ops`
    - `shell_run`
    - `shell_session`
    - `git_status`
    - `git_diff`
    - `todo_update`
    - `ask_user_approval`
  - ten dotted legacy van con de giu compatibility:
    - `workspace.list`
    - `workspace.read`
    - `workspace.search`
    - `workspace.grep`
    - `workspace.write`
    - `workspace.edit`
    - `workspace.ops`
    - `shell.run`
    - `shell.session`
    - `todo.update`
    - `approval.request`
- Permission model da co enforcement co ban theo profile:
  - `observe`: read-only tooling;
  - `assist`: read/edit/git/process-list auto-allow, action nguy hiem can approval;
  - `admin`: allow toan bo capability da dang ky.
- Permission model da biet phan biet `actor=model` va `actor=user/ui`:
  - model bi chan cac action nguy hiem nhu `shell.exec`, `file.delete`, `process.kill`, `package.install` trong profile `assist`;
  - user/ui van co the di qua luong approval neu runtime bat interactive approval.
- Default `coding_agent` prompt profile da co tool guidance mac dinh de model biet uu tien inspect/edit/verify flow.
- Tool result dua nguoc vao conversation tool-loop da co payload co cau truc hon:
  - `request_id`
  - `tool_name`
  - `ok`
  - `status`
  - `output`
  - `error`
- Core + desktop shell da co conversation route/prompt editor voi 2 che do:
  - apply runtime;
  - save nguoc lai TOML cho `conversation` config.
- Core + desktop shell da co editor cho `openai.compat` provider config voi 2 che do:
  - apply runtime + reload provider registry;
  - save nguoc lai TOML.
- Desktop shell da ho tro them/xoa provider rows, quick presets, va custom header editor cho `openai.compat`.
- Core + desktop shell da co editor cho `anthropic.messages` provider config voi 2 che do:
  - apply runtime + reload provider registry;
  - save nguoc lai TOML.
- Desktop shell da ho tro them/xoa provider rows, quick preset Claude API, va custom header editor cho `anthropic.messages`.
- `config.example.toml` hien da duoc canh lai de startup path hop voi huong core hien tai:
  - `permissions.profile = "assist"`
  - `interactive_approval = true`
  - `default_provider` + route `chat`/`coding_agent` mac dinh -> `localhost.chat`
- Desktop shell da co panel tool control/contract cho agent:
  - toggle `allow-all-cmd` theo session;
  - `tools.invoke_many` cho parallel inspect read-only;
  - render metadata tool `output_kind`, `parallel_safe`, `mutates_state`;
  - hien ket qua batch inspect theo tung tool call thay vi chi dump vao message log.
- Desktop shell UI da duoc doi sang chat-first shell ro hon:
  - `Ops` va `Config` la drawer mo theo nguc canh thay vi full panel song song;
  - `Ops` gom run inspector, shell grant, parallel inspect, provider health, va tool contract;
  - khu vuc chat gio giu frame co dinh, khong con che do mo rong `Focus chat`;
  - dong message moi duoc canh theo stack tu day len de doc nhu giao dien chat thay vi console phang.
- Active provider drawer gio da co them lop readiness ro hon:
  - nut `Refresh runtime`;
  - health strip hien `reachable/offline`, model duoc detect hay khong, va endpoint dang probe;
  - hint text local path gio noi ro hon khi `127.0.0.1`/base URL khong reachable.
- Lop desktop protocol/state gio da duoc cap nhat cho active-provider surface:
  - `settings.providers.active.get`
  - `settings.providers.active.catalog`
  - `settings.providers.active.update`
  - state shape/view helpers tuong ung da co trong `desktop/src/state.js`
  - protocol/unit test gio khoa them regression "apply active provider xong van giu config moi", khong de mock path roi ve default.
- Desktop shell da co them conversation tool activity timeline:
  - UI hien tai gom approval + tool activity thanh `Run inspector` theo item/run thay vi 2 panel rieng.
  - render `conversation.tool.requested`, `tool.started`, `approval.pending`, `tool.finished`, `conversation.tool.completed`;
  - tool events da co them correlation fields de map chac hon trong UI: `run_id`, `conversation_id`, `tool_call_id`.
  - `conversation.tool.requested` hien da carry them `request_id` de approval panel va tool activity panel link truc tiep;
  - UI da phan biet duoc `denied_by_user` voi `denied_by_profile`.
  - reconnect/bootstrap gio co them `tool.activity.snapshot` de hydrate lai tool activity timeline neu attach lai giua run/pending approval.
  - `Run inspector` gio group item theo `run_id` thay vi chi list phang; item khong co run van duoc render standalone.
  - `Run inspector` run groups gio co the collapse/expand doc lap, khong dung chung state thu gon voi message log.
  - header moi `Run inspector` run group gio co them action mo run dich trong message log.
  - approval/tool item gio co jump toi assistant turn hoac tool-result entry lien quan trong message log.
  - message log gio append them structured `tool` result entries cho conversation tool calls.
  - assistant turn + tool results trong message log gio duoc gom theo `run_id`.
  - run groups trong message log gio co the collapse/expand.
  - moi run group da co summary badge/tong ket co ban o header.
  - moi run group da co them summary row preview assistant/tool moi nhat.
  - summary row moi run group da co them action copy local-first:
    - `Copy summary`
    - `Focus inspector`
    - `Copy answer`
    - `Copy tool result`
    - `Copy run JSON`
- Da verify:
  - JS tests pass;
  - Rust tests pass;
  - Python tests pass;
  - `python -m yue_core --config config.example.toml doctor` load dung startup config moi;
  - `python -m yue_core --config config.example.toml providers-health` tra `localhost.chat` = reachable + model_available;
  - `python -m yue_core --config config.example.toml chat ...` chat that qua localhost chay duoc;
  - `python -m yue_core --config config.example.toml desktop-demo --headless-smoke-test` chat that qua desktop controller chay duoc;
  - `cargo tauri build --bundles nsis --ci --no-sign` pass.
- Luu y verify:
  - nhung thay doi UI moi nhat quanh `Run inspector` collapse/group/open-run duoc code xong sau dot verify gan nhat theo yeu cau user "cu tiep tuc code";
  - lan verify desktop gan nhat truoc dot UI moi nhat la:
    - `node --check desktop/src/app.js`
    - `node --check desktop/src/runtime.js`
    - `node --check desktop/src/state.js`
    - `node --test desktop/tests/protocol.test.js`
  - re-check ngay 2026-07-07 cho active-provider protocol/state slice:
    - `node --check desktop/src/protocol.js`
    - `node --check desktop/src/state.js`
    - `node --test desktop/tests/protocol.test.js`
  - re-check ngay 2026-07-07 cho desktop Tauri diagnostic harness:
    - `cargo check --manifest-path desktop/src-tauri/Cargo.toml`
    - `cargo test --manifest-path desktop/src-tauri/Cargo.toml`
  - chua rebuild/re-run lai NSIS-installed app sau khi them richer diagnostic stages; packaged path van chua duoc coi la xanh.
  - `desktop/index.html` hien dang nap `desktop/src/runtime.js` truc tiep; `desktop/src/app.js` khong phai live entrypoint cua shell packaged/dev preview hien tai, nen moi thay doi runtime shell phai uu tien doi chieu voi `runtime.js`.
  - lan re-check packaged NSIS sau dot startup/config moi nhat moi chi tra diagnostic `{"stage":"scheduled"}`, chua quay lai `runtime_bootstrap`; khong duoc coi packaged path la da xanh.
- Mot so noi dung tu handoff cu da duoc tach sang note rieng. Cho nao chua du bang chung hoac moi la dinh huong thi phai danh dau ro trong note tuong ung, khong duoc tu coi la done.

## Thu tu uu tien hien tai

1. Core chat/runtime/tool loop + tooling cho agent:
   doc `runtime_flow_map.md` + `agent_roadmap.md` + `permissions_and_safety.md`
2. Desktop shell/UI va packaged/lifecycle hardening:
   tiep tuc trong note desktop; core chat/localhost runtime da co proof that, UI chat-first co dinh da on hon, gio uu tien noi lifecycle packaged/native vao path nay
3. Backend/provider stack de phuc vu core:
   doc `provider_and_prompt_config.md` + `model_runtime_direction.md` + `hardware_constraints.md`
4. Memory/observer + permissions mo rong:
   doc `memory_and_observer_roadmap.md` + `permissions_and_safety.md`
5. Voice:
   de sau, doc `voice_deferred_scope.md`

## Next target

- Doc `docs/notes/agent_roadmap.md` truoc de lay thu tu mo file va next step.
- Core/tooling:
  - giu core/tool surface theo alias underscore cho `coding_agent`; neu mo rong them phai giu it tool, backend thong minh, permission ro.
- Desktop/core UX tiep theo:
  - noi packaged/Tauri desktop app vao local runtime hien dang chay that, giam phu thuoc mock/fallback path;
  - neu co the, de desktop tu spawn/stop `llama-server` hoac it nhat hien readiness ro rang cho `127.0.0.1:8080`;
  - debug packaged non-dev path dang dung o diagnostic `scheduled` sau dot startup/config moi;
  - giam drift giua `desktop/src/app.js` va `desktop/src/runtime.js` neu tiep tuc mo rong desktop shell;
  - sau khi on lai packaged bootstrap, moi quay ve action run-level nhu retry/export/replay thay vi polish visual nho.
- Backend/provider:
  - giu local host OpenAI-compatible server tai `127.0.0.1:8080` la path uu tien cao nhat.
  - `LM Studio` la path phu, khong con la default uu tien.
