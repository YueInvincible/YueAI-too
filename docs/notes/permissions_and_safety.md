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

- Da co permission engine co ban trong core cho tool execution.
- Shell tooling (`shell.exec`, `shell.run`, `shell.session`) hien chay qua shell argv no-profile/no-rc de giam output rac tu host shell truoc khi tra ket qua cho agent.
- Da co profile:
  - `observe`: cho read-only tool nhu `file.read`, `file.list`, `file.search`, `process.list`, `git.status`, `git.diff`.
  - `assist`: auto-allow read/edit workflow (`file.write`, `file.edit`, `file.move`) va bat approval cho action nguy hiem nhu `file.delete`, `shell.exec`, `process.kill`, `package.install`.
  - `admin`: allow toan bo capability da dang ky.
- Lop tool alias moi cung da di qua permission engine cung cach:
  - read-only: `workspace.list`, `workspace.read`, `workspace.search`, `workspace.grep`, `todo.update`, `approval.request`, `ask_user_approval`;
  - read/edit workflow: `workspace.write`, `workspace.edit`, `workspace.ops`;
  - action nguy hiem: `shell.run`, `shell.session`.
- Da co luong approval explicit rieng:
  - tool `approval.request`;
  - transport method `approval.request`;
  - runtime goi thang `ApprovalProvider` thay vi bat agent suy doan approval qua mot tool nguy hiem gia.
- Da co session grant runtime cho `allow-all-cmd`:
  - transport method `permissions.allow_all_cmd.set`;
  - transport method `permissions.allow_all_cmd.get`;
  - grant nay chi mo cho model shell tools (`shell.exec`, `shell.run`, `shell.session`) trong session duoc chi dinh;
  - grant khong xuyen qua boundary profile `observe`;
  - transport core gio da enforce ro: `actor=model` khong duoc tu bat grant nay, chi non-model actor moi doi duoc grant.
- Desktop shell da render ro hon contract nay:
  - panel toggle co note ro grant chi anh huong model shell tools trong session hien tai;
  - tool contract panel show `parallel_safe`, `mutates_state`, `output_kind`;
  - shell tools hien them note rang `allow-all-cmd` chi mo trong `assist`/`admin`, `observe` van bi chan.
- Luong approval va shell session da co them event/audit trail ro hon:
  - `approval.requested` / `approval.resolved`;
  - `shell.session.started` / `shell.session.read` / `shell.session.listed` / `shell.session.stopped`;
  - `permission.grant.updated`;
  - audit categories tuong ung cho approval va shell session actions.
- Da co phan biet `actor` co ban:
  - `model` chi duoc phep workflow an toan;
  - `user/ui` moi di vao nhom action co the xin approval.
- Audit log da ghi:
  - `tool.request`
  - `permission.decision`
  - `tool.result`
- Boundary workspace da duoc enforce cho file tools.
- Tool co side effect ra host/process/network da co `dry_run` path de test va plan an toan hon trong moi truong bi han che.

## Viec agent sau nen lam

1. Audit tiep cac action co side effect trong desktop/core de xem con duong nao chua di qua permission engine.
2. Noi tool-result UX voi approval UX de user thay ngay tool nao dang bi chan boi profile, tool nao dang doi approval, tool nao da duoc session-grant.
3. Can nhac bo sung policy chi tiet hon theo actor/session thay vi chi theo profile va tool name.
4. Tach ro phan nao la approval UI/runtime, phan nao la enforcement core.

## Phu thuoc

- [memory_and_observer_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\memory_and_observer_roadmap.md)
- [product_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\product_direction.md)
