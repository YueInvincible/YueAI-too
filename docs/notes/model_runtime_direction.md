# Model Runtime Direction

## Muc dich

Luu cac dinh huong runtime/model da duoc neu ra truoc day, tach khoi handoff tong.

## Dinh huong giu lai tu handoff cu

- Local inference van la huong chinh.
- Runtime nen de nhung thanh phan khac goi qua giao tiep on dinh, uu tien OpenAI-compatible interface neu hop.
- Cac lua chon tung duoc nhac:
  - nhom Qwen 4B de lam mac dinh nhe;
  - nhom coder 7B neu can coding/chat manh hon;
  - stack GGUF/llama.cpp la huong hop ly de thu nghiem local.

## Trang thai core hien tai

- Da co `openai.compat` plugin cho:
  - OpenAI cloud;
  - Ollama;
  - LM Studio;
  - llama.cpp;
  - custom OpenAI-compatible endpoint.
- Da co config route rieng cho:
  - normal chat;
  - coding agent.
- Da co prompt-profile config de doi:
  - personality;
  - system instruction;
  - tool instruction;
  - response instruction.
- Core hien tai dang unify tren `/v1/chat/completions` streaming de dung chung cho local va cloud.

## Tieu chi chot model/runtime

- Time-to-first-token
- Tok/s thuc te
- RAM/VRAM peak
- Do on dinh khi goi tu desktop shell
- Chat luong tieng Viet
- Do tin cay khi can tool-call/coding

## Chua duoc xac nhan

- Chua co benchmark chot trong repo.
- Chua co quyet dinh cuoi cung model nao la default.
- Chua co note xac nhan runtime nao la san sang ship.
- Chua co health-check / auto-detect endpoint trong core.
- Chua co UI de doi provider route va prompt profile.

## Viec agent sau nen lam

1. Chon 1-2 cap model/runtime nho de benchmark that tren may hien tai.
2. Ghi lai so lieu vao file nay.
3. Xac dinh cap local cho `chat` va cap coding cho `coding_agent`.
4. Chi sau do moi de xuat default runtime/model.

## Phu thuoc

- Doc cung:
  - [hardware_constraints.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\hardware_constraints.md)
  - [product_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\product_direction.md)
  - [provider_and_prompt_config.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\provider_and_prompt_config.md)
