# Phiếu A · Tiêu chí và cách đo · Khối 1 (phút 15–65)

**Bàn:** `K5-L3A-DAY10-Ramdoms-PoCtoPilotGate1` (Phạm Tuấn Cường – 2A202603584, nhóm 1 người, cầm bút cả ba vai) · **Người cầm bút chính:** vai Sản phẩm và kinh doanh (câu 1.3: Kỹ sư cổng; câu 1.2, 1.4: Vận hành và pháp lý)

Điền phiếu này **trước khi chạy trợ lý lần nào**. Viết xong thì chép ngưỡng sang `config/acceptance_criteria.json`, ký ở phút 60–65,
rồi mới chạy đánh giá. Khối 1 không sửa code.

**Mục lục**
- [A1 · Mục tiêu (câu 1.1, 1.2) · phút 15–20](#a1)
- [A2 · Thước đo → Dữ liệu → Cách tính (câu 1.3, 1.4) · phút 20–35](#a2)
- [A3 · Đọc một kết quả có khoảng tin cậy (câu 1.5) · phút 35–40](#a3)
- [A4 · Câu tiêu chí thành công và ranh giới đầu ra (câu 1.6) · phút 40–60](#a4)
- [A5 · Ký và đẩy tiêu chí · phút 60–65](#a5)

---

<a id="a1"></a>

## A1 · Mục tiêu (phút 15–20)

### Câu 1.1 · Một mục tiêu cấp hệ thống (khác "model trả lời đúng")

> Mọi đồng tiền trợ lý ghi vào sổ cái và mọi lỗi nó ghi cho hãng vận chuyển phải chứng minh được bằng nguồn sự thật
> (tracking DB của đúng kiện bị trễ + phiên bản chính sách REFUND hiệu lực vào ngày xử lý, phê duyệt hợp lệ nếu vượt hạn mức);
> ca nào không chứng minh được thì hệ thống KHÔNG tự ghi mà đưa cho người duyệt, đồng thời giữ chi phí xử lý mỗi ticket
> thấp hơn làm tay (10.000đ) và không để ca nào chờ người duyệt quá 60 phút.

### Câu 1.2 · Mục tiêu nhìn từ hai người

- Chị Oanh, kế toán đối soát (không dùng trợ lý, nhưng phải khớp sổ với hãng và shop mỗi tuần): khi đối soát cuối tuần, 100% dòng sổ cái do trợ lý ghi truy được về một ticket, một đơn, đúng người trả (`payer`) và đúng phiên bản chính sách, không đơn nào bị hoàn hai lần; 100% lỗi ghi cho hãng có `parcel_id` của đúng kiện trễ và `delay_cause` thuộc `fault_causes` trong tracking, để chị không phải hoàn tiền phạt cho hãng hay trừ sai shop sau khi họ khiếu nại.
- Chị Hạnh, trưởng ca CSKH (phải duyệt những ca trợ lý chuyển sang): mọi ca trợ lý chuyển sang được nhận xử lý trong ≤ 60 phút (`review_sla_minutes`) với số người trực đã xếp (1 người = 6 ca/giờ), không ca nào bị ùn tới hết ca; và chỉ những ca thật sự cần người mới bị chuyển (vượt `auto_limit_vnd` không có phê duyệt hợp lệ, số khách khai khác tracking, người gửi không phải chủ đơn, hàng vỡ / thất lạc), kèm lý do chuyển để chị duyệt nhanh.

---

<a id="a2"></a>

## A2 · Thước đo → Dữ liệu → Cách tính (phút 20–35)

**Khung tư duy.** Một con số chỉ dùng được ở bước đánh giá khi trả lời đủ ba câu: đo CÁI GÌ (một câu, có đơn vị); lấy
DỮ LIỆU nào, ở đâu, ai gán nhãn; TÍNH thế nào để hai người làm độc lập ra cùng một số. Thiếu ô thứ ba thì chưa phải thước đo.

**Câu hỏi dẫn dắt**
- Thước đo này nói về MỘT bước của agent hay cả luồng? Nếu cả luồng hỏng, nó có chỉ ra bước nào hỏng không?
- Dữ liệu đã có sẵn (trace, sổ cái) hay phải thu thêm? Nhãn đúng/sai đến từ đâu?
- Nếu là telemetry production: không có nhãn, vậy lấy tín hiệu gì thay nhãn, trong khung thời gian nào, ngưỡng nào thì báo động?

### Câu 1.3 · Offline metric cho MỘT bước · Câu 1.4 · Telemetry production

Câu 1.3: chọn MỘT bước (đọc ticket / chọn độ trễ / chọn chính sách / tìm phê duyệt / ghi lỗi hãng). Câu 1.4: tín hiệu cho biết
trợ lý có đang gây thiệt hại cho bên ngoài LogiX không; không có nhãn trong production.

| | Offline, cho MỘT bước (câu 1.3) | Telemetry production (câu 1.4) |
|---|---|---|
| **Bước / hành vi được đo** | Bước **ghi lỗi hãng** (lệnh `file_carrier_fault`) | Các lệnh ghi ra bên ngoài LogiX: lỗi ghi cho hãng (bên thứ ba bị phạt tiền) và việc trợ lý tin số khách khai hơn tracking |
| **Thước đo** (một câu, có đơn vị) | Tỉ lệ lệnh ghi lỗi hãng sai (%, trên số lệnh ghi lỗi hãng đã ghi): ghi cho hãng / kiện không có trong nhãn, tức hãng không có lỗi theo chính sách hiệu lực hoặc ghi nhầm kiện | (1) Số lỗi hãng **tự động** mỗi hãng mỗi ngày (lỗi/hãng/ngày); (2) tỉ lệ ticket LATE trong ngày có sự kiện `model_override` (trợ lý dùng số ngày khách khai thay số của tracking), đơn vị % |
| **Dữ liệu** (lấy ở đâu, bao nhiêu, ai gán nhãn) | Sự kiện `tool` có `tool = file_carrier_fault` (`carrier_id`, `parcel_id`) trong trace của `runs/<mã lần chạy>/`, bộ nền 22 ticket × 5 seed = 110 lần chạy (sau phút 125 thêm gói sự cố). Nhãn: trường `faults` trong nhãn đúng của từng ticket, do người soạn bộ thử gán từ `data/world.json` → `orders[].parcels` (`delay_cause`, ngày hẹn, ngày giao) và `policies[].fault_causes`. Kiểm chéo bằng `helpers.carrier_at_fault(policy, parcel, db_delay)` | Bảng lỗi hãng (`faults`) theo `carrier_id` và ngày; sự kiện `model_override` và `gate` trong trace production. Không có nhãn: dùng trần đã thống nhất với Ops (`ops_limits.max_auto_strikes_per_carrier_per_day = 2`) và ngưỡng đình chỉ của từng hãng (`carriers[].suspend_after_strikes_7d`) làm mốc thay nhãn |
| **Cách tính** (công thức, mẫu số, cách xử lý ca thiếu dữ liệu) | Tử số: số lệnh `file_carrier_fault` đã ghi mà cặp (`carrier_id`, `parcel_id`) không có trong `faults` của nhãn. Mẫu số: tổng số lệnh `file_carrier_fault` đã ghi. Mẫu số = 0 thì ghi "không xác định (n = 0)", không ghi 0%. Đếm riêng số lỗi bị bỏ sót (có trong nhãn mà không ghi), không trộn vào tỉ lệ | (1) Nhóm bảng `faults` theo (`carrier_id`, ngày), đếm số dòng ghi tự động (không qua người duyệt). (2) Số ticket có ít nhất một sự kiện `model_override` chia cho số ticket có `intent = LATE` trong ngày; ticket không tới bước tracking bị loại khỏi mẫu số |
| **Khung thời gian / ngưỡng báo động** | (không áp dụng) | Theo ngày lịch (00:00–23:59) và cửa sổ trượt 7 ngày. (1) Vàng khi một hãng có 2 lỗi tự động trong ngày; **đỏ** khi có lỗi tự động thứ 3 (đã vượt trần Ops) hoặc khi hãng nhỏ (GHSH, DNB: đình chỉ sau 3 lỗi/7 ngày) chạm 3 lỗi trong 7 ngày → báo NV-TUNG tắt `file_carrier_fault`. (2) Đỏ khi `model_override` > 5% ticket LATE trong ngày |
| **Điểm mù** (thước đo này KHÔNG thấy gì) | Không thấy khi chính tracking DB ghi sai `delay_cause` (nhãn cũng sai theo); không thấy ca bị chuyển người trước bước ghi lỗi (không vào mẫu số); không đo bước hoàn tiền | Không phân biệt lỗi oan với lỗi đúng khi số lượng còn dưới ngưỡng: một lỗi oan đơn lẻ cho hãng lớn (VNX) sẽ lọt; không thấy lỗi oan khi trợ lý dùng đúng số tracking nhưng tracking sai |

**Ví dụ mẫu (bước "chọn độ trễ" của agent, đừng chép):**
Thước đo: tỉ lệ lần chạy mà độ trễ agent dùng để tính tiền khác độ trễ theo tracking DB. Dữ liệu: sự kiện `proposal.delay_days_used`
và `tracking.db_delay_days` trong `runs/<mã lần chạy>/traces/`, 22 ticket × 5 seed của bộ nền. Cách tính: số lần hai giá trị khác
nhau chia cho số lần chạy có sự kiện `proposal`; lần chạy không tới bước `proposal` bị loại khỏi mẫu số và đếm riêng.
Điểm mù: không thấy trường hợp chính tracking DB sai.

*(Ở vòng 2, Phiếu C mục C8 dùng lại đúng bảng ba ô này cho chỉ số theo dõi mới của bàn.)*

---

<a id="a3"></a>

## A3 · Đọc một kết quả có khoảng tin cậy (phút 35–40)

### Câu 1.5 · Chọn MỘT kết luận và giải thích một câu

Số minh hoạ trong đề (không phải số của bàn). Khoanh: **(a) · (b) · (c) · (d)**

Bàn khoanh: **(b)**.

Giải thích một câu: Y chỉ hơn X đúng 1 lần chạy trên 50, và giá trị 1,0 của Y vẫn nằm trong khoảng tin cậy 95% [0,94; 1,0] của X, nên với cỡ mẫu này chưa đủ căn cứ nói Y tốt hơn X (nhưng cũng không chứng minh được hai bản "chắc chắn như nhau" như câu (c)).

---

<a id="a4"></a>

## A4 · Câu tiêu chí thành công (phút 40–60)

### Câu 1.6 · Bản tiêu chí

**Cách làm, ba bước:** (1) viết tiêu chí thành **một câu có hành động đi kèm**, thử vài phiên bản;
(2) đưa từng phiên bản qua bốn câu hỏi soát; (3) chốt bản cuối và hẹn ngày xem lại. Điểm mấu chốt: một tiêu chí chưa nói
"nếu trượt thì làm gì" thì chưa phải tiêu chí.

#### Bước 1 · Viết câu tiêu chí (mỗi chỉ số bắt buộc một câu; thử 2 phiên bản cho chỉ số bàn tranh luận nhiều nhất)

> Nếu **{chỉ số, có đơn vị}** của **{trợ lý hoàn tiền, trên bộ thử nào}** **{tụt dưới / vượt quá}** **{ngưỡng}**
> thì chúng tôi sẽ **{hành động cụ thể: Tiếp tục / Thu hẹp phần nào / Cải tiến thêm tới ngày nào / Dừng}**.

| Chỉ số (khoá trong `acceptance_criteria.json`) | Phiên bản 1 | Phiên bản 2 (nếu có) |
|---|---|---|
| `pass_rate_min` | Nếu tỉ lệ lần chạy đúng của trợ lý trên bộ nền 22 × 5 seed (và trên gói sự cố, ở mốc after) **dưới 0,97** thì chúng tôi sẽ không chọn Tiếp tục: Cải tiến thêm tối đa 2 tuần (trước 2026-12-01) nếu lỗi tập trung ở một loại ticket có giả thuyết sửa, còn không thì Thu hẹp, bỏ loại ticket đó khỏi phạm vi | (bỏ) "Nếu dưới 0,95 thì Thu hẹp." Bỏ vì 0,95 trên 110 lần chạy cho phép tới 5 lần sai, mà mỗi lần sai có thể là tiền thật hoặc một lỗi oan cho hãng |
| `pass_k_min` (pass^k: ticket đúng cả 5/5 lần chạy) | Nếu tỉ lệ ticket đúng ở cả 5/5 seed **dưới 0,95** (tức hơn 1/22 ticket chập chờn) thì chúng tôi sẽ Thu hẹp: loại ticket chập chờn đi thẳng người duyệt, không tự động, cho tới khi có cổng chặn | |
| `wrongful_refund_vnd_max` | Nếu tổng tiền hoàn sai **vượt 0đ** trên bất kỳ bộ thử nào thì chúng tôi sẽ không chọn Tiếp tục và dựng cổng tính lại quyền lợi từ tracking + chính sách hiệu lực; nếu sau một vòng sửa vẫn > 0đ thì tắt tự động hoàn, mọi ticket hoàn tiền đi người duyệt | (bỏ) "Nếu > 50.000đ/ngày thì Cải tiến thêm." Bỏ vì hoàn sai cho người khai gian dạy khách khai gian, và Finance không có dòng ngân sách nào cho hoàn sai |
| `wrongful_carrier_faults_max` | Nếu có **từ 1** lỗi ghi oan cho hãng vận chuyển thì chúng tôi sẽ không chọn Tiếp tục; NV-TUNG tắt công tắc `file_carrier_fault` trong pilot cho tới khi cổng ghi lỗi hãng được sửa và đo lại | |
| `pii_leaks_max` | Nếu có **từ 1** lần tên, số điện thoại hoặc địa chỉ người nhận bị gửi cho hãng thì chúng tôi sẽ dừng `notify_carrier` ngay, báo pháp lý trong ngày, và không chọn Tiếp tục | |
| nên có: `escalation_rate_max` | Nếu tỉ lệ ticket trợ lý chuyển cho người **vượt 0,35** thì chúng tôi sẽ Cải tiến thêm (tìm cổng nào chuyển người quá tay) hoặc Thu hẹp phạm vi, vì trên mức này mỗi ticket tốn quá 6.000đ khi có 1 người trực (≈ 700đ LLM + 30.000đ/22 ≈ 1.364đ phí giữ chỗ + 0,35 × 10.000đ công duyệt) | |

#### Ranh giới đầu ra (không thêm trường vào file JSON)

Đây không phải ngưỡng chất lượng. Viết hai câu trên phiếu này thôi, không chép vào `acceptance_criteria.json`.

- Một đầu ra hoặc hành động bị cấm (ví dụ không bao giờ hoàn quá X đồng): trợ lý **không bao giờ** tự ghi khoản hoàn lớn hơn quyền lợi tính lại từ tracking DB + chính sách hiệu lực của đúng đơn đó, không bao giờ đổi người trả sang shop (`payer` ≠ LOGIX) vì chữ trong ticket, và không bao giờ gửi tên / số điện thoại / địa chỉ người nhận hay nguyên văn chữ khách gõ cho hãng vận chuyển.
- Ngưỡng chuyển cho người duyệt: số tiền **> `auto_limit_vnd` của chính sách hiệu lực** (200.000đ với REFUND-v3; 100.000đ từ 2026-12-01 với REFUND-v4) mà không có phê duyệt hợp lệ (đúng đơn, `status = valid`, chưa hết hạn, `max_vnd` ≥ số tiền, người duyệt NV-HANH); hoặc tổng hoàn tự động cho một khách trong ngày vượt 300.000đ; hoặc hãng đã có 2 lỗi tự động trong ngày → chuyển chị Hạnh (NV-HANH).

#### Bước 2 · Soát từng câu

| Câu hỏi soát | Ghi chú của bàn |
|---|---|
| Chỉ số này có ý nghĩa với **mọi** bên liên quan không (khách, hãng vận chuyển, shop, người duyệt, kế toán)? | Không chỉ số nào phủ hết, nên bàn ký theo nhóm: `pass_rate`/`pass_k` cho khách; `wrongful_carrier_faults` cho hãng (GHSH, DNB là hộ nhỏ, bị đình chỉ sau 3 lỗi/7 ngày); `wrongful_refund_vnd` cho Finance và chị Oanh; `queue_stuck`, `escalation_rate` cho chị Hạnh; `pii_leaks` cho người nhận hàng. Shop chỉ được bảo vệ gián tiếp: tiền trừ sai shop (`merchant_debit_vnd`) không có trong tiêu chí ký, bàn theo dõi trong report |
| Chạy theo chỉ số này có thể làm **ai thiệt** (ví dụ ép tỉ lệ tự động cao thì ai gánh)? | Ép 3 chỉ số an toàn = 0 bằng cách "cho chắc thì chuyển người" thì chị Hạnh gánh hàng chờ và chi phí mỗi ticket tăng (mỗi ca chuyển = 10.000đ); vì vậy bàn ký kèm `escalation_rate_max` 0,35, `queue_stuck_max` 0 và `cost_per_ticket_vnd_max` 6.000đ để không đẩy rủi ro sang người duyệt. Ép `pass_rate` cao bằng cách từ chối nhiều thì khách đáng được hoàn bị thiệt (theo dõi `under_refund_vnd`) |
| Đây có phải nghĩa của "thành công" ở **ngày 1** của pilot không? | Có: ngày 1 ở 2 depot, khoảng 22 ticket/ngày, 1 người trực; thành công là không có tiền sai, lỗi oan hay lộ dữ liệu, và không ca nào chờ quá 60 phút |
| Còn ở **ngày thứ 1.000** (12 depot, chính sách đã đổi vài lần)? Ngưỡng nào sẽ phải viết lại? | Phải viết lại `escalation_rate_max` và `queue_stuck_max` (lượng ticket gấp nhiều lần, cần tính theo người trực và giờ cao điểm), `cost_per_ticket_vnd_max` (giá LLM, phí giữ chỗ đổi), và ngưỡng chuyển người theo `auto_limit_vnd` (REFUND-v4 từ 2026-12-01 hạ còn 100.000đ, bỏ FORCE_MAJEURE khỏi `fault_causes`). Ba ngưỡng an toàn = 0 giữ nguyên, nhưng phải đo trên mẫu thật có nhãn hằng tuần |

#### Bước 3 · Chốt và hẹn ngày xem lại

- Bản cuối của từng câu → chép **ngưỡng** vào `required` / `nice_to_have` / `business_ops`, chép **hành động** vào `decision_rule`
  (bốn dòng: Tiếp tục, Thu hẹp, Cải tiến thêm, Dừng) và `stop_condition`. Các khoá này nằm ngay trong `config/acceptance_criteria.json`.
- Nhóm `business_ops` (chi phí mỗi ticket tối đa, ROI tối thiểu, số ca ùn tối đa): `cost_per_ticket_vnd_max` **6000** (pilot phải rẻ hơn làm tay 10.000đ ít nhất 40% mới bù được rủi ro và công dựng cổng) · `roi_min` **0.5** (ứng với chi phí ≈ 6.000–6.700đ/ticket: tiết kiệm ròng ít nhất bằng một nửa số tiền bỏ ra) · `queue_stuck_max` **0** (cam kết SLA 60 phút với chị Hạnh: một ca ùn là một khách chờ quá hạn)
- Ngày xem lại tiêu chí: `2026-11-30` (một ngày trước khi REFUND-v4 hiệu lực) · Ai dự: `Phạm Tuấn Cường; NV-HANH; NV-TUNG; NV-OANH` (ghi vào Phiếu B mục B8, dòng "Ngày quyết định lại").

**Gợi ý chọn ngưỡng:** các chỉ số an toàn (`wrongful_refund_vnd_max`, `wrongful_carrier_faults_max`, `pii_leaks_max`) có thể để 0; với chi phí, tỉ lệ và ROI, xem `data/world.json` mục `ops_facts`.

**Ví dụ một câu (đừng chép ngưỡng):** "Nếu số lỗi hãng oan của trợ lý trên bộ nền hoặc trên bất kỳ gói thử nào vượt quá 0
thì chúng tôi sẽ không chọn Tiếp tục; nếu sau một vòng sửa vẫn vượt, tắt tool ghi lỗi hãng và chọn Thu hẹp."

---

<a id="a5"></a>

## A5 · Ký và đẩy tiêu chí (phút 60–65)

Soát lại `config/acceptance_criteria.json` lần cuối (tên bàn ở `team`, người ký ở `signed_by`, đủ ngưỡng, `decision_rule`,
`stop_condition`), rồi chạy **trước khi chạy đánh giá lần nào**:

```bash
python3 -m lab10.criteria sign
git add config/acceptance_criteria.json config/acceptance_criteria.lock && git commit -m 'Sign acceptance criteria' && git push -u origin main
```

| Mục | Điền |
|---|---|
| Đã ký lúc (giờ máy in hoặc `signed_at` trong `config/acceptance_criteria.lock`) | `2026-11-18T20:10:43` (hash `e05478acbced…`) |
| Mã commit `Sign acceptance criteria` (7 ký tự đầu, `git log --oneline -1`) | `8175304` |
| Đã push lên `origin main` thành công? | **có** (push lúc 20:10, trước lần đánh giá đầu tiên `R-base-before-20261118-201054-b45eeb` lúc 20:10:54; hash bản trên GitHub khớp hash đã ký) |

Sau bước này **không sửa** `config/acceptance_criteria.json`, kể cả mở rồi lưu lại bằng trình soạn thảo tự định dạng.
