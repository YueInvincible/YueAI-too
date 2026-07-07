# Desktop UI Priority

## Muc dich

Ghi ro ly do vi sao giai doan tiep theo nen uu tien sua desktop UI/UX truoc khi mo rong them core feature.

## Phan hoi dung thu da xac nhan

1. `python -m yue_core serve` khi chay truc tiep trong terminal gan nhu "im lang".
   - Dieu nay khong nhat thiet la loi.
   - Hien tai no la JSONL server cho bridge/UI, nen se dung cho stdin va khong tu in banner/help ro rang.
   - Ve trai nghiem nguoi dung/dev, dieu nay gay cam giac "chua chay duoc".

2. `Yue Desktop Preview` hien tai khong de dung.
   - Khu vuc config qua dai.
   - Zoom nho het co van kho xem het.
   - Chua co co che an/hien, thu gon, hoac chia nhom panel hop ly.
   - Bieu hien visual hien tai chua dep va chua tao cam giac san pham co the dung thu.

## Ket luan uu tien

Trong giai doan ngay tiep theo:

- uu tien desktop shell UI/UX truoc;
- tam thoi khong mo rong them core feature neu khong phuc vu truc tiep viec dung thu UI;
- muc tieu la tao mot shell co the:
  - doc duoc;
  - thu gon/mo rong duoc;
  - nhin ro nhom config;
  - dung thu duoc ma khong can zoom nho cuc doan.

## Cac van de UI can xu ly truoc

### 1. Information architecture

- Tach console thanh cac nhom ro rang, vi du:
  - Chat / activity
  - Tooling / approvals
  - Routing / prompts
  - Provider config
  - Diagnostics
- Moi nhom nen co co che:
  - collapse / expand
  - an/ hien
  - focus mode neu can

### 2. Config density

- Provider config va prompt config dang qua dai tren mot man hinh.
- Can:
  - tabs
  - accordion
  - section folders
  - hoac side navigation + detail pane

### 3. Visual polish

- UI hien tai chua dat muc "co the demo/thu nghiem thoai mai".
- Can nang cap:
  - spacing
  - hierarchy
  - scroll behavior
  - responsive constraints
  - visual grouping

### 4. Empty/idle states

- `yue_core serve` nen co note ro trong docs/prompt rang no dung cho bridge.
- Desktop shell nen co text huong dan ro hon khi:
  - chua attach session
  - chua co provider
  - chua co conversation
  - chua co tool activity

## File nen mo truoc neu sua UI

1. `desktop/index.html`
2. `desktop/src/styles.css`
3. `desktop/src/state.js`
4. `desktop/src/app.js`
5. `desktop/src/runtime.js`
6. `docs/notes/desktop_bridge_status.md`
7. `docs/notes/runtime_flow_map.md`

## Boundary cho agent sau

- Khong rewrite core runtime chi de phuc vu layout/UI.
- Neu can them mot chut state bo tro UI thi giu thay doi hep va mirror sang `runtime.js`.
- Uu tien cai gi giup nguoi dung "thu duoc" truoc:
  - hide/show config
  - chia folder/section
  - panel nao can full width/2-column
  - scroll doc ngang/ doc doc hop ly
