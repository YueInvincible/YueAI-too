# Hardware Constraints

## Muc dich

Gom lai cac rang buoc may chay thuc te de agent sau khong de xuat huong qua nang.

## Rang buoc da biet

- May hien tai:
  - CPU: Intel Core i5-13450HX
  - RAM kha dung: khoang 28 GB
  - GPU dong RTX 3050 laptop, VRAM thuc te duoc nhac den trong handoff cu la muc 6 GB
- Workspace khong nen mac dinh theo huong nhieu mo hinh nang chay dong thoi.
- Muc tieu la local-first nen uu tien stack nhe, de khoi dong, de kill, de debug.

## He qua ky thuat

- Model mac dinh nen uu tien nhom 4B hoac quy mo tuong duong neu can chay on dinh tren may nay.
- Nhom 7B/8B chi nen duoc xem la tuy chon theo tac vu, can benchmark thuc te truoc khi chot.
- Vision/TTS/renderer can thiet ke theo kieu on-demand, khong auto giu tai nguyen nen.
- Avatar/VRM neu quay lai sau nay phai uu tien renderer nhe, khong gia dinh du GPU cho pipeline nang.

## Chua chac chan

- Chua thay benchmark chinh thuc trong repo cho:
  - throughput tok/s;
  - RAM/VRAM peak;
  - startup time;
  - do on dinh khi chay cung desktop shell.
- Neu agent sau chay benchmark that, cap nhat file nay va chi ghi ket luan khi co so lieu.

## File/huong lien quan

- Xem them:
  - [model_runtime_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\model_runtime_direction.md)
  - [product_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\product_direction.md)
