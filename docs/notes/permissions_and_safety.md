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
- Da co scoped capability/resource grant dau tien:
  - transport method `permissions.capability_grants.get`;
  - transport method `permissions.capability_grants.set`;
  - transport method `permissions.capability_grants.revoke`;
  - moi grant co `id`, `capability`, `resource`, `lifetime`, `scope_id`, `uses_remaining`;
  - lifetime da enforce trong core: `once`, `run`, `conversation`, `session`;
  - `once` tu consume sau lan allow dau tien;
  - `run` yeu cau `scope_id` va chi match dung `run_id`;
  - grant khong xuyen qua boundary profile `observe`;
  - `actor=model` khong duoc tu set/revoke grant.
- Da co resource scope taxonomy contract dau tien trong core:
  - `global`;
  - `workspace.path`;
  - `filesystem.path`;
  - `shell.cwd`;
  - `network.domain`;
  - `network.local_port`;
  - `app`;
  - `screen.region`;
  - `memory.namespace`.
- Tool denied result gio co metadata co cau truc:
  - `denied_by_policy`;
  - `denied_by_user`;
  - `denied_by_missing_scope`;
  - `denied_by_approval_unavailable`;
  - `resource_scope` di kem trong `ToolResult.metadata.permission`;
  - tool activity uu tien metadata nay thay vi doan error text.
- Desktop shell da render ro hon contract nay:
  - panel toggle co note ro grant chi anh huong model shell tools trong session hien tai;
  - permission center trong Ops drawer hien scoped capability grants cua session hien tai;
  - permission center co refresh va revoke tung grant qua `permissions.capability_grants.get/revoke`;
  - permission center co recent risky actions/audit preview tu `audit.recent`;
  - permission center va Run inspector hien denial metadata ro hon:
    `denial_category`, `resource_scope`, `rule_id`, `outcome`, va `reason`;
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
- Audit log da co read surface:
  - `AuditLog.recent(...)`;
  - JSONL method `audit.recent`;
  - desktop protocol/mock/runtime wrappers.
- Boundary workspace da duoc enforce cho file tools.
- Tool co side effect ra host/process/network da co `dry_run` path de test va plan an toan hon trong moi truong bi han che.

## Viec agent sau nen lam

1. Thiet ke plugin install/manifest/trust lifecycle truoc khi mo community tools.
2. Mo rong resource taxonomy va inference cho browser/app/screen/memory khi cac tool do bat dau duoc thiet ke.
3. Audit tiep cac action co side effect trong desktop/core de xem con duong nao chua di qua permission engine.
4. Tach ro phan nao la approval UI/runtime, phan nao la enforcement core.

## Latest verification

Re-check ngay 2026-07-09 cho permission center UI:

- `node --check desktop/src/app.js`
- `node --check desktop/src/runtime.js`
- `node --check desktop/src/state.js`
- `node --test desktop/tests/protocol.test.js`

Ket qua: desktop JS syntax pass, protocol test pass 17/17.

Re-check ngay 2026-07-09 cho audit preview:

- `PYTHONPATH=src python -m unittest tests.test_transport -v`
- `node --check desktop/src/app.js`
- `node --check desktop/src/runtime.js`
- `node --check desktop/src/state.js`
- `node --test desktop/tests/protocol.test.js`

Ket qua: transport tests pass 31/31, desktop JS syntax pass, protocol tests pass 17/17.

Re-check ngay 2026-07-09 cho denied metadata display:

- `node --check desktop/src/app.js`
- `node --check desktop/src/runtime.js`
- `node --check desktop/src/state.js`
- `node --test desktop/tests/protocol.test.js`

Ket qua: desktop JS syntax pass, protocol tests pass 17/17.

## Phu thuoc

- [memory_and_observer_roadmap.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\memory_and_observer_roadmap.md)
- [product_direction.md](C:\Users\Yue\Downloads\YueAI-main\YueAI-main\docs\notes\product_direction.md)
