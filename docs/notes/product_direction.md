# Product Direction

## Mục tiêu

- Xây một desktop AI companion local-first.
- Avatar là UI chính.
- Console tích hợp là bề mặt điều khiển chính.
- Hỗ trợ coding-agent workflow qua file/tools/build/test.

## Quyết định đã chốt

- Không quay lại:
  - floating icon;
  - Godot launcher cũ;
  - GPT-SoVITS;
  - VTube Studio.
- Desktop stack ưu tiên:
  - Tauri;
  - Three.js;
  - `@pixiv/three-vrm`.
- Core agent logic phải ở `yue_core`, không dồn vào renderer/UI.

## Cái đang bị hoãn

- Voice:
  - STT;
  - TTS;
  - voice cloning;
  - streaming audio pipeline.
- VRM/render hoàn chỉnh.
- System observer/process watcher đầy đủ.

## Ràng buộc kỹ thuật

- Máy mục tiêu không phù hợp để giữ nhiều model nặng đồng thời.
- UI/avatar phải nhẹ.
- Model/tool/provider nên tách rời để không làm vỡ core process.
- Mọi tool side effect phải có permission rõ ràng.

## Điều agent sau không nên làm

- Không tự mở rộng lại các nhánh kiến trúc UI cũ.
- Không note hoàn thành nếu chưa có verify pass.
- Không mô tả packaged release hay runtime hoàn chỉnh nếu chỉ mới verify debug path.
