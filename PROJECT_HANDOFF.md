# YueAI Project Handoff

File nay chi la muc luc ngan. Khong dua chi tiet dai vao day.

Chi giu 3 thu:
- muc tieu chinh;
- yeu cau chung cho agent sau;
- danh sach note can doc theo tung domain + next target.

## Muc tieu chinh

- Tiep tuc xay YueAI theo huong desktop local-first.
- Huong hien tai van la desktop shell Tauri + native bridge toi `yue_core`.
- Chua duoc xem la xong cho cac phan: non-dev frontend path, lifecycle hardening, renderer/VRM, memory/observer, permissions, voice.

## Yeu cau chung cho agent sau

- Khong mo rong file handoff nay thanh tai lieu dai.
- Truoc khi lam domain nao, chi doc note domain do va cac note phu thuoc truc tiep.
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
- Voice deferred scope:
  - [docs/notes/voice_deferred_scope.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\voice_deferred_scope.md)
- Permissions and safety:
  - [docs/notes/permissions_and_safety.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\permissions_and_safety.md)
- Memory and observer roadmap:
  - [docs/notes/memory_and_observer_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\memory_and_observer_roadmap.md)

## Trang thai tong quan

- Da co desktop session protocol, desktop demo, va JSONL transport cho `desktop.*` + `conversation.*`.
- Workspace `desktop/` da co frontend shell, Rust native bridge, JS/Rust tests, va debug-window proof khi preview server dang chay.
- Core da co provider routing theo role (`chat`, `coding_agent`) va prompt-profile config (`personality`, `system_instruction`, `tool_instruction`, `response_instruction`).
- Core da co plugin `openai.compat` de cau hinh OpenAI cloud + Ollama + LM Studio + custom OpenAI-compatible endpoint trong cung mot plugin.
- Da verify:
  - JS tests pass;
  - Rust tests pass;
  - Python tests pass;
  - debug Tauri window spawn duoc `python -m yue_core serve` va don child process khi app dung.
- Mot so noi dung tu handoff cu da duoc tach sang note rieng. Cho nao chua du bang chung hoac moi la dinh huong thi phai danh dau ro trong note tuong ung, khong duoc tu coi la done.

## Thu tu uu tien hien tai

1. Runtime/model decision + provider routing tiep:
   doc `model_runtime_direction.md` + `provider_and_prompt_config.md` + `hardware_constraints.md`
2. Lifecycle hardening va integration renderer/VRM:
   tiep tuc trong note desktop, them note con khi domain nay tach ro hon
3. Memory/observer + permissions:
   doc `memory_and_observer_roadmap.md` + `permissions_and_safety.md`
4. Voice:
   de sau, doc `voice_deferred_scope.md`

## Next target

- Core provider/runtime da co config route + prompt profile; doc `provider_and_prompt_config.md` truoc khi sua tiep.
- Uu tien tiep theo:
  - them health-check/provider status cho OpenAI-compatible backends;
  - mo UI/settings editor cho provider routes + prompt profiles;
  - sau do moi quay lai lifecycle hardening neu can.
