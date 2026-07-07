# Tool Activity Reconnect Issue

## Trang thai

Da sua cho reconnect/resume co bootstrap snapshot co cau truc cho tool activity.

Desktop shell gio khong con phu thuoc hoan toan vao event stream tu dau run moi dung lai duoc `Run inspector`.

## Nguyen nhan cu

- Bootstrap truoc day chi lay:
  - `desktop.state`
  - `approval.pending.list`
  - cac snapshot config/provider/tool catalog
- Tool activity timeline trong frontend hien duoc xay chu yeu tu event stream:
  - `conversation.tool.requested`
  - `tool.started`
  - `approval.pending`
  - `approval.responded`
  - `tool.finished`
  - `conversation.tool.completed`
- Neu desktop attach muon hon sau khi mot vai event da da phat, frontend khong co persisted snapshot nao cho tool activity de replay.

## Cach sua da ap dung

- Core co them `ToolActivityStore` subscribe cac event:
  - `conversation.*`
  - `approval.*`
  - `tool.*`
- JSONL transport co them method:
  - `tool.activity.snapshot`
- Frontend bootstrap (`app.js` va `runtime.js`) gio hydrate them tool activity snapshot sau khi lay pending approvals.
- Frontend state co them helper snapshot rieng de clone an toan:
  - `applyToolActivitySnapshot(...)`

## Payload snapshot hien tai

- `items[]` gom cac truong:
  - `run_id`
  - `conversation_id`
  - `request_id`
  - `tool_call_id`
  - `tool_name`
  - `arguments`
  - `status`
  - `approval_id`
  - `output`
  - `error`
- `status` la dong tong ket hien tai cho panel.

## Verify da chay

- `node --check desktop/src/app.js`
- `node --check desktop/src/runtime.js`
- `node --test desktop/tests/protocol.test.js`
- `$env:PYTHONPATH='src'; python -m pytest tests/test_transport.py`

## Phan con lai

- Da co jump hai chieu giua `Run inspector` va message log:
  - tool item co the jump toi assistant turn/tool-result lien quan
  - run summary row co the `Focus inspector` nguoc lai vao tool item moi nhat cua run
- Da hop nhat approval + tool activity thanh mot `Run inspector`.
- `Run inspector` hien tai da co them:
  - group theo `run_id`
  - collapse/expand doc lap voi message log
  - `Open run` o header de nhay sang run group trong message log
- Phan chua lam tiep theo neu can:
  - export/replay/retry action co y nghia hon o run-level
  - test end-to-end reconnect/resume bang packaged bridge thay vi moi protocol/unit flow

## Luu y verify

- Phan reconnect snapshot da verify bang:
  - `node --check desktop/src/app.js`
  - `node --check desktop/src/runtime.js`
  - `node --test desktop/tests/protocol.test.js`
  - `$env:PYTHONPATH='src'; python -m pytest tests/test_transport.py`
- Cac thay doi UI moi nhat sau do quanh group/collapse/open-run chua duoc verify lai vi user uu tien tiep tuc code.
