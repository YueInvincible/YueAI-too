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
- Local path uu tien cao nhat la `LM Studio`; `llama.cpp` editor rieng de sau.
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

## Trang thai tong quan

- Da co desktop session protocol, desktop demo, va JSONL transport cho `desktop.*` + `conversation.*`.
- Workspace `desktop/` da co frontend shell, Rust native bridge, JS/Rust tests, va debug-window proof khi preview server dang chay.
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
- Da verify:
  - JS tests pass;
  - Rust tests pass;
  - Python tests pass;
  - debug Tauri window spawn duoc `python -m yue_core serve` va don child process khi app dung.
- Mot so noi dung tu handoff cu da duoc tach sang note rieng. Cho nao chua du bang chung hoac moi la dinh huong thi phai danh dau ro trong note tuong ung, khong duoc tu coi la done.

## Thu tu uu tien hien tai

1. Core chat/runtime/tool loop + tooling cho agent:
   doc `runtime_flow_map.md` + `agent_roadmap.md` + `permissions_and_safety.md`
2. Backend/provider stack de phuc vu core:
   doc `provider_and_prompt_config.md` + `model_runtime_direction.md` + `hardware_constraints.md`
3. Desktop shell/UI va packaged/lifecycle hardening:
   tiep tuc trong note desktop sau khi core/tooling on dinh hon
4. Memory/observer + permissions mo rong:
   doc `memory_and_observer_roadmap.md` + `permissions_and_safety.md`
5. Voice:
   de sau, doc `voice_deferred_scope.md`

## Next target

- Doc `docs/notes/agent_roadmap.md` truoc de lay thu tu mo file va next step.
- Core/tooling:
  - hoan thanh nhung phan con lai cua core chat/runtime/tool surface cho agent.
- Backend/provider:
  - giu `LM Studio` la local path uu tien.
  - `llama.cpp` editor rieng chi dua vao roadmap giai doan sau.
