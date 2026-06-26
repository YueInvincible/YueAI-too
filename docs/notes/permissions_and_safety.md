# Permissions And Safety

## Muc dich

Tach cac yeu cau permissions/safety ra khoi handoff tong de agent sau khong bo sot.

## Dinh huong can giu

- He thong can phan biet ro cac muc:
  - observe;
  - assist;
  - action/admin.
- Hanh dong nguy hiem hoac co tac dong he thong khong duoc auto chay neu chua co xac nhan phu hop.
- Local-first khong co nghia la bo qua privacy va audit trail.

## Cac nhom rui ro can note

- File system writes/deletes
- Process spawn/kill
- Network calls
- Screen capture / OCR / observer data
- Memory luu thong tin nhay cam

## Trang thai hien tai

- Chua thay implementation day du trong repo cho permission pipeline tong the.
- Co the da co tung manh logic roi rac, nhung chua co note xac nhan thong nhat.

## Viec agent sau nen lam

1. Audit cac action co side effect trong desktop/core.
2. Gom thanh mot permission model ro rang.
3. Ghi file nao dang canh bao, file nao da enforce, file nao moi la y tuong.

## Phu thuoc

- [memory_and_observer_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\memory_and_observer_roadmap.md)
- [product_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\product_direction.md)
