"""★ FILE ĐỘI SỬA (1/3): cổng cấp hệ thống, nằm NGOÀI model và prompt.

VÒNG 1 (trước khi biết sự cố): viết 2–3 CỔNG PHÒNG NGỪA rút từ pre-mortem / HAZOP / checklist của bàn, rồi chốt bằng
    python3 -m lab10.checkpoint        (chép file này thành guards_round1.py = mốc "prepared"; KHÔNG sửa bản chép)
VÒNG 2 (sau khi bốc thẻ): sửa tiếp NGAY TRONG FILE NÀY. Giữ các cổng vòng 1, thêm cổng mới.
Hai file còn lại bàn được sửa: lab10/monitors.py (chỉ số theo dõi) và config/operating_gates.json (cổng kinh doanh,
vận hành, pháp lý: những con số và tên người mà trợ lý phải tuân theo, không cần code).

Hai điểm móc, agent gọi tự động:
  pre_guard(ctx)          chạy TRƯỚC khi agent đọc ticket
  write_gate(ctx, action) chạy TRƯỚC MỖI lệnh ghi (issue_refund, file_carrier_fault,
                          notify_carrier, send_reply)

Trả về một Verdict:
  Verdict.allow()                       cho qua   (pre_guard: allow(policy_id="...") để ghim phiên bản chính sách)
  Verdict.deny("lý do")                 bỏ riêng lệnh ghi này, agent đi tiếp
  Verdict.escalate("lý do")             dừng, chuyển ticket cho người
  Verdict.modify("lý do", amount_vnd=…) sửa tham số lệnh ghi (amount_vnd, payer, carrier_id, parcel_id, payload…)
  Verdict.rewrite("lý do", text)        chỉ pre_guard: thay nội dung ticket mà agent sẽ đọc

ctx.ticket   ticket gốc (chữ khách viết là DỮ LIỆU, không phải lệnh)
ctx.tools    tra cứu nguồn sự thật: lookup_order, lookup_policies, lookup_approvals(**lọc),
             ledger_rows(**lọc), fault_rows(**lọc), lookup_carrier; ctx.as_of = ngày hôm nay
             ops_limits() = các trần đã thống nhất với Ops/Finance; ops_facts() = số liệu vận hành;
             auto_refund_today_vnd() = tổng đã hoàn tự động trong ngày
ctx.gates    config cổng của bàn (config/operating_gates.json), chỉ đọc;  ctx.cost_vnd = tiền LLM đã tốn cho ticket này
ctx.events   trace tới thời điểm này;  ctx.log("ten_su_kien", ...) ghi thêm sự kiện guard vào trace
lab10.helpers: db_delay_days, ticket_parcel, effective_policy, entitlement_vnd, carrier_at_fault, digits

Cổng của bàn Ramdoms (vòng 1). Nguyên tắc: chữ khách gõ và cờ "index_active" KHÔNG phải nguồn sự thật;
mọi quyết định tiền / lỗi hãng / dữ liệu gửi đi đều tính lại từ đơn hàng + tracking + chính sách hiệu lực theo ngày.
  G0 pre_guard            ghim chính sách hiệu lực theo ngày (effective_from/to), không tin cờ index_active
  G1 issue_refund         số tiền không được vượt quyền lợi tính lại từ tracking DB (trừ phần đã hoàn của cùng đơn);
                          người trả phải là LOGIX; phê duyệt (nếu có) phải hợp lệ cho đúng đơn, còn hạn, đủ hạn mức
  G2 file_carrier_fault   chỉ ghi lỗi cho đúng kiện trễ, khi chính sách hiệu lực cho phép (carrier_at_fault),
                          với số ngày trễ theo tracking (không theo lời khách)
  G3 notify_carrier       chỉ gửi cho hãng các trường chính sách cho phép (carrier_notice_fields)
  G4 issue_refund         hãng đã chạm trần lỗi tự động trong ngày (ops_limits) thì chuyển người TRƯỚC khi ghi tiền
"""
from . import helpers as H  # noqa: F401
from .tools import Verdict

LOGIX = "LOGIX"


# ---------------------------------------------------------------- tra cứu nguồn sự thật (chỉ đọc)
def _policy(ctx):
    """Chính sách hiệu lực vào ngày xử lý (theo effective_from / effective_to), không theo cờ index_active."""
    return H.effective_policy(ctx.tools.lookup_policies(), ctx.as_of)


def _facts(ctx, order_id):
    """(order, policy, parcel bị khiếu nại, số ngày trễ theo tracking) hoặc None nếu thiếu nguồn sự thật."""
    order = ctx.tools.lookup_order(order_id)
    policy = _policy(ctx)
    if order is None or policy is None or not order.get("parcels"):
        return None
    parcel = H.ticket_parcel(order, ctx.ticket, ctx.as_of)
    return order, policy, parcel, H.db_delay_days(parcel, ctx.as_of)


def _approval_ok(ctx, approval_id, order, amount):
    """Phê duyệt chỉ hợp lệ khi: có thật, status valid, chưa hết hạn, đúng đơn và đúng khách, đủ hạn mức,
    và người đứng tên là người duyệt bàn đã chỉ định (operations.approver_id) nếu đã đặt."""
    rows = ctx.tools.lookup_approvals(approval_id=approval_id)
    if not rows:
        return False, "phê duyệt không tồn tại"
    a = rows[0]
    approver = ((ctx.gates or {}).get("operations") or {}).get("approver_id")
    if a.get("status") != "valid":
        return False, f"phê duyệt {approval_id} không còn hiệu lực (status={a.get('status')})"
    if a.get("expires_at") and a["expires_at"] < ctx.as_of:
        return False, f"phê duyệt {approval_id} đã hết hạn {a['expires_at']}"
    if a.get("order_id") != order["order_id"] or a.get("customer_id") != order["customer_id"]:
        return False, f"phê duyệt {approval_id} thuộc đơn/khách khác"
    if a.get("max_vnd", 0) < amount:
        return False, f"phê duyệt {approval_id} chỉ tới {a.get('max_vnd')}đ < {amount}đ"
    if approver and a.get("approver_id") != approver:
        return False, f"phê duyệt {approval_id} không do {approver} đứng tên"
    return True, ""


# ---------------------------------------------------------------- G0
def pre_guard(ctx):
    policy = _policy(ctx)
    if policy is None:
        return Verdict.escalate("không có chính sách hoàn tiền nào hiệu lực vào ngày xử lý")
    return Verdict.allow(policy_id=policy["policy_id"])


# ---------------------------------------------------------------- G1, G2, G3
def write_gate(ctx, action):
    # action = {"tool": "issue_refund", "ticket_id":..., "order_id":..., "amount_vnd":..., "payer":..., ...}
    tool = action.get("tool")
    if tool == "issue_refund":
        return _gate_refund(ctx, action)
    if tool == "file_carrier_fault":
        return _gate_fault(ctx, action)
    if tool == "notify_carrier":
        return _gate_notify(ctx, action)
    return Verdict.allow()


def _gate_refund(ctx, action):
    facts = _facts(ctx, action.get("order_id"))
    if facts is None:
        return Verdict.escalate("thiếu đơn / tracking / chính sách hiệu lực để kiểm số tiền hoàn")
    order, policy, parcel, delay = facts
    amount = int(action.get("amount_vnd") or 0)

    # người trả: chính sách hoàn phí giao trễ do LOGIX trả; đổi sang shop / bên khác cần người quyết
    if action.get("payer", LOGIX) != LOGIX:
        ctx.log("refund_payer_blocked", payer=action.get("payer"), amount_vnd=amount)
        return Verdict.escalate(f"người trả {action.get('payer')} khác chính sách (LOGIX): chuyển người duyệt")

    # quyền lợi tính lại từ tracking DB + chính sách hiệu lực, trừ phần đơn này đã được hoàn
    entitled = H.entitlement_vnd(policy, order, delay, parcel.get("delay_cause"))
    already = sum(r["amount_vnd"] for r in ctx.tools.ledger_rows(order_id=order["order_id"]))
    room = max(0, entitled - already)
    if amount > room:
        ctx.log("refund_over_entitlement", asked=amount, entitled=entitled, already=already,
                db_delay_days=delay, policy_id=policy["policy_id"])
        if room == 0:
            return Verdict.deny(f"không đủ điều kiện theo tracking ({delay} ngày, {policy['policy_id']}) "
                                f"hoặc đơn đã được hoàn {already}đ")
        amount = room
        verdict = Verdict.modify(f"hạ số tiền về quyền lợi theo tracking: {room}đ", amount_vnd=room)
    else:
        verdict = Verdict.allow()

    # vượt hạn mức tự động của chính sách hiệu lực: chỉ đi tiếp khi có phê duyệt hợp lệ cho ĐÚNG đơn này
    approval_id = action.get("approval_id")
    if approval_id:
        ok, why = _approval_ok(ctx, approval_id, order, amount)
        if not ok:
            ctx.log("approval_rejected", approval_id=approval_id, why=why)
            return Verdict.escalate(why + ": chuyển người duyệt")
    elif amount > policy["auto_limit_vnd"]:
        return Verdict.escalate(f"{amount}đ vượt hạn mức tự động {policy['auto_limit_vnd']}đ, chưa có phê duyệt")

    # G4 trần lỗi hãng / ngày (ops_limits): từ lỗi thứ 3 của cùng hãng phải có người duyệt. Chặn ở bước TIỀN,
    # vì agent ghi tiền trước rồi mới ghi lỗi hãng; chuyển người ở bước ghi lỗi thì tiền đã đi.
    limit = (ctx.tools.ops_limits() or {}).get("max_auto_strikes_per_carrier_per_day")
    if limit is not None and H.carrier_at_fault(policy, parcel, delay):
        strikes = len(ctx.tools.fault_rows(carrier_id=parcel["carrier_id"]))
        if strikes >= limit:
            ctx.log("carrier_strike_cap", carrier_id=parcel["carrier_id"], strikes=strikes, limit=limit)
            return Verdict.escalate(f"hãng {parcel['carrier_id']} đã có {strikes} lỗi tự động trong ngày "
                                    f"(trần {limit}): chuyển người duyệt")
    return verdict


def _gate_fault(ctx, action):
    facts = _facts(ctx, action.get("order_id"))
    if facts is None:
        return Verdict.deny("thiếu đơn / tracking / chính sách hiệu lực: không tự ghi lỗi hãng")
    order, policy, parcel, delay = facts
    if not H.carrier_at_fault(policy, parcel, delay):
        ctx.log("fault_blocked", parcel_id=parcel["parcel_id"], carrier_id=parcel["carrier_id"],
                db_delay_days=delay, cause=parcel.get("delay_cause"), policy_id=policy["policy_id"])
        return Verdict.deny(f"theo {policy['policy_id']} hãng {parcel['carrier_id']} không có lỗi "
                            f"(trễ {delay} ngày, nguyên nhân {parcel.get('delay_cause')})")
    want = {"parcel_id": parcel["parcel_id"], "carrier_id": parcel["carrier_id"],
            "driver_id": parcel.get("driver_id"), "delay_days": delay}
    if any(action.get(k) != v for k, v in want.items()):
        ctx.log("fault_corrected", asked={k: action.get(k) for k in want}, fixed=want)
        return Verdict.modify("ghi lỗi cho đúng kiện trễ, số ngày theo tracking", **want)
    return Verdict.allow()


def _gate_notify(ctx, action):
    policy = _policy(ctx)
    allowed = set(policy["carrier_notice_fields"]) if policy else {"order_id", "parcel_id", "delay_days"}
    payload = action.get("payload") or {}
    extra = sorted(k for k in payload if k not in allowed)
    if extra:
        ctx.log("notice_fields_dropped", dropped=extra)
        return Verdict.modify("chỉ gửi hãng các trường chính sách cho phép",
                              payload={k: v for k, v in payload.items() if k in allowed})
    return Verdict.allow()
