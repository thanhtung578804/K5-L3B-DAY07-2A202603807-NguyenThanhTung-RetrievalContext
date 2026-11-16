# Báo cáo Day 7

- **Họ và tên:** Nguyễn Thanh Tùng
- **MSSV:** 2A202603807
- **Lớp:** L3B

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - Dùng lại tài liệu từ Day 06 là *Sổ tay sinh viên Đại học Bách khoa Hà Nội 2026* (`data/So tay sinh vien_2026.pdf`, tài liệu hướng dẫn công khai cho sinh viên), gồm 30 trang nội dung chính.
  - Chia thành 283 chunks theo đoạn văn (`by_paragraph`, tối đa 600 ký tự/chunk), lưu tại [data/chunks.json](../../data/chunks.json).
- **Vector store, embedding model, phiên bản và số chiều:**
  - Dùng `gemini-embedding-001` (3072 chiều) cho toàn bộ 283 chunks và lưu vector thật ra file JSON cục bộ ([data/chunk_embeddings.json](../../data/chunk_embeddings.json)) để truy vấn cosine similarity trong bộ nhớ. Lý do chuyển từ Neon DB (Day 06) sang lưu local là để tránh lỗi timeout kết nối DB khi chấm bài và không phải lộ thông tin kết nối DB trong repo.
- **Agent model, cách chạy và phân chia dev/test:**
  - Model điều phối chính: `gpt-4o-mini` (OpenAI API), có hỗ trợ `gemini-3.5-flash-lite`.
  - Bộ benchmark ([data/cases.json](../../data/cases.json)) gồm 24 câu:
    - **Dev (17 câu):** 15 câu có đáp án (`q1`–`q15`) và 2 câu thiếu bằng chứng (`q21_unans`, `q22_unans`).
    - **Test (7 câu):** 5 câu có đáp án (`q16`–`q20`) và 2 câu thiếu bằng chứng (`q23_unans`, `q24_unans`).
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - Câu có bằng chứng được gắn trực tiếp một đoạn trích chuẩn (`gold`) là substring có thật trong chunk, kiểm tra hợp lệ bằng hàm `validate()` của `starter/baseline.py`.
  - Câu thiếu bằng chứng là các câu hỏi ngoài phạm vi sổ tay (ví dụ: học bổng Elon Musk, cơ sở HUST trên Mặt Trăng, trạm vũ trụ).
  - Chấm theo `starter/agent_metrics.py`: Grounded answer (thang 0/1/2), Citation hợp lệ (ID phải nằm trong context đã truy xuất), Abstention đúng với câu không có bằng chứng.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline (Exp 1) | TF-IDF, top-3, không filter, budget 800 | Baseline tìm theo từ khóa | dev | 8/15 (53.33%) | 13/15 (86.67%) | 8/15 (53.33%) | 1.99 ms / \$0.00 |
| Phương pháp 2 (Exp 2) | Dense Gemini (3072d), top-3, cosine, budget 800 | Vector ngữ nghĩa bắt được câu đồng nghĩa | dev | 9/15 (60.00%) | 15/15 (100.0%) | 9/15 (60.00%) | 928.81 ms / \$0.00 |
| Phương pháp 3 (Exp 3) | Hybrid RRF (Dense + TF-IDF, k=60), top-3, budget 800 | Kết hợp từ khóa chính xác và ngữ nghĩa | dev | 11/15 (73.33%) | 14/15 (93.33%) | 11/15 (73.33%) | 60.92 ms / \$0.00 |
| Cải thiện 1 (Exp 4) | Hybrid RRF + Metadata filter (`section`), budget 800 | Lọc theo mục để giảm nhiễu giữa các phần | dev | 11/15 (73.33%) | 14/15 (93.33%) | 11/15 (73.33%) | 47.44 ms / \$0.00 |
| Cải thiện 2 (Exp 5 - Chốt) | Hybrid RRF, top-3, tăng budget lên 1200 ký tự | Giữ thêm được chunk thứ 2 vào context | dev | 11/15 (73.33%) | 14/15 (93.33%) | 12/15 (80.00%) | 42.70 ms / \$0.00 |
| Cấu hình đã chọn | Hybrid RRF, top-3, budget 1200 | Chạy cấu hình chốt trên tập Test | test | 4/5 (80.00%) | 5/5 (100.0%) | 4/5 (80.00%) | 756.84 ms / \$0.00 |
| Baseline | TF-IDF, top-3, budget 800 | Đối chứng trên tập Test | test | 3/5 (60.00%) | 5/5 (100.0%) | 3/5 (60.00%) | 1.17 ms / \$0.00 |

- **Lý do chọn cấu hình:** Chọn Hybrid RRF + budget 1200 vì Hit@1 trên Dev cao hơn hẳn TF-IDF và Dense đơn lẻ (73.33% so với 53.33% và 60%), thời gian chạy cục bộ nhanh (~43 ms), tăng budget lên 1200 giúp Context Evidence Rate tăng từ 73.33% lên 80%. Metadata filter (Exp 4) không làm tăng điểm trên bộ Dev nên không bật mặc định để tránh lọc nhầm khi suy luận section sai.
- **Hai lỗi trên tập Dev:**
  1. `q10` (*"Sinh viên tham gia Tuần sinh hoạt công dân được cộng bao nhiêu điểm rèn luyện?"*): Retriever lấy về 3 đoạn ở trang 10 (`par_2`, `par_0`, `par_7`), nhưng đáp án "+ 10 điểm" nằm ở `par_6`. Do giới hạn budget 800 chỉ nhét vừa đoạn đầu (`par_2`), model không thấy con số nên trả lời không đủ bằng chứng.
  2. `q15` (*"Tỷ lệ sinh viên ĐHBK Hà Nội từng làm gia sư là bao nhiêu phần trăm?"*): Từ "gia sư" chỉ xuất hiện 1 lần ở trang 21 (`par_1`), trong khi các trang 23, 19, 17 có nhiều từ khóa về việc làm/hướng nghiệp nên điểm vector cao hơn và đẩy đoạn ở trang 21 ra ngoài top-3.

## Agent và đánh giá

- **Thiết kế agent:** Dùng tool `search(query, filter)` gọi Hybrid RRF; giới hạn tối đa 2 lượt tìm kiếm (`max_searches = 2`) để tránh lặp vô hạn. Context được khử trùng lặp và cắt theo ngưỡng 1200 ký tự. Khi trả lời, hàm hậu kiểm đối chiếu tất cả `[chunk_id]` với danh sách chunk đã nạp; nếu ID không hợp lệ hoặc context rỗng thì ép về trạng thái từ chối (`abstain`).

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| Agent Dev (`gpt-4o-mini`) | 17/17 (100%) | 1.06 | 0: 2, 1: 2, 2: 11 (TB: 1.60) | 14/14 (100%) | 13/13 (100%) | 2/2 (100%) | 2/15 (13.3%) |
| Agent Test (`gpt-4o-mini`) | 7/7 (100%) | 1.00 | 0: 0, 1: 1, 2: 4 (TB: 1.80) | 5/5 (100%) | 5/5 (100%) | 2/2 (100%) | 0/5 (0.0%) |

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| `q16` | answerable | `search(...)` -> 3 chunks trang 2 | Khởi công khu trường mới trên khuôn viên Đông Dương năm 1961 `[so-tay-sv-hust-2026_p2_par_1]` | Grounded 2 (đúng mốc thời gian 1961) |
| `q17` | answerable | `search(...)` -> 3 chunks trang 7 | Thời gian đào tạo tích hợp Cử nhân - Thạc sĩ là 5,5 năm `[so-tay-sv-hust-2026_p7_par_3]` | Grounded 2 (đúng thời gian 5,5 năm) |
| `q18` | answerable | `search(...)` -> 3 chunks trang 11 | Được cộng 3 điểm rèn luyện khi khai báo cư trú `[so-tay-sv-hust-2026_p11_par_0]` | Grounded 2 (đúng mức 3 điểm) |
| `q19` | answerable | `search(...)` -> 3 chunks trang 18 | Học bổng xét cấp theo từng học kỳ cho SV chính quy `[so-tay-sv-hust-2026_p18_par_0]` | Grounded 2 (đúng đối tượng và kỳ xét) |
| `q20` | answerable | `search(...)` -> 3 chunks trang 23 | Hai trang chính thức: HUST.EDU.VN và CTT-DAOTAO `[so-tay-sv-hust-2026_p23_par_1]` | Grounded 1 (đúng 2 trang thông tin) |
| `q23_unans` | unanswerable | `search(...)` -> 3 chunks học bổng | Không đủ bằng chứng để trả lời. | Abstention 1 (từ chối đúng) |
| `q24_unans` | unanswerable | `search(...)` -> 3 chunks cơ sở | Không đủ bằng chứng để trả lời. | Abstention 1 (từ chối đúng) |

- **Trace, nhãn và lệnh chạy:**
  - File kết quả Test: [traces.json](../../starter/results/agent-test/traces.json), [reviews.json](../../starter/results/agent-test/reviews.json), [summary.json](../../starter/results/agent-test/summary.json).
  - Lệnh đánh giá: `python starter/agent_metrics.py --cases data/cases.json --traces starter/results/agent-test/traces.json --reviews starter/results/agent-test/reviews.json --split test --output starter/results/agent-test/summary.json`
- **Đánh đổi và giới hạn:** Tăng budget lên 1200 giúp Agent có đủ ngữ cảnh hơn nhưng tăng nhẹ số token đầu vào mỗi lượt. Nếu câu hỏi rơi vào bảng biểu dài hoặc bị ngắt đoạn giữa trang (như `q10`), chunking theo đoạn văn bản thuần túy vẫn có thể bỏ sót ô số liệu.

## Thử thách nâng cao

- **Tài liệu, nguồn, số trang:** Sử dụng *Báo cáo thường niên Vinamilk 2025* ([PDF 112 trang](../../data/20260319_VNM_Bao_cao_thuong_nien_2025_eae619d5f6.pdf)), tài liệu công bố thông tin chính thức năm 2026 của Vinamilk.
- **Cách xử lý và phạm vi index:**
  - Index toàn bộ 112 trang thành 789 chunks (`text-embedding-3-small`, 1536 chiều).
  - Với 42 trang chứa bảng tài chính, biểu đồ, sơ đồ tổ chức và giấy chứng nhận, hệ thống render ảnh PNG (`data/advanced/page_images/`) và dùng `gemini-3.5-flash-lite` Vision để đọc bảng Markdown và số liệu trục biểu đồ, sau đó đối chiếu lại với bản gốc.
  - Trang 112 là trang bìa sau không có chữ nên không có chunk (không ảnh hưởng nội dung).
- **Benchmark và cấu hình đã chốt:**
  - Bộ 48 câu hỏi ([data/advanced/cases.json](../../data/advanced/cases.json)) chia trước khi chạy: Dev 18 câu (đạt 18/18), Test độc lập 30 câu.
  - Cấu hình chốt trên Dev: Hybrid RRF kết hợp chunk trực quan (tối đa 2800 ký tự/chunk), `top_k = 8`, `budget_chars = 5200`, tối đa 3 lượt `search` cho câu multi-hop, dùng `gpt-4o-mini` kèm kiểm tra thực thể trước khi trả lời.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---:|---:|---|
| Bảng | 6 / 6 | 100.0% | Tra đúng hàng, cột, năm và đơn vị |
| Ảnh, sơ đồ | 5 / 5 | 100.0% | Đọc đúng sơ đồ tổ chức, timeline, ảnh chứng nhận |
| Biểu đồ | 5 / 5 | 100.0% | Đọc đúng giá trị cột, biểu đồ tròn, xu hướng đường, trục kép |
| Multi-hop | 4 / 4 | 100.0% | Gọi search đa lượt ghép thông tin 2 trang và tính hiệu số đúng |
| Text | 4 / 4 | 100.0% | Trích xuất đúng tầm nhìn, điều kiện và quy chuẩn |
| Thiếu bằng chứng | 5 / 6 | 83.33% | 5/6 từ chối đúng; câu `adv_test2_unans_5` hỏi bẫy về "bò giải phương trình" bị model trả lời nhầm bằng tổng số lượng đàn bò (130.000 con) |
| **Toàn bộ** | **29 / 30** | **96.67%** | Đạt ngưỡng >= 90% (27/30) |

- **Trace, chi phí và cách chạy lại:**
  - Kết quả Test nâng cao: [traces.json](../../starter/results/advanced-test/traces.json), [reviews.json](../../starter/results/advanced-test/reviews.json), [summary.json](../../starter/results/advanced-test/summary.json).
  - Độ trễ trung bình trên 30 câu Test là 2.942 ms/câu; tổng lượng token là 99.628 prompt + 2.737 completion tokens, chi phí khoảng \$0.017.
  - Chạy lại bằng 3 lệnh:
    ```bash
    python scripts/adv_index_all.py
    python scripts/adv_run_pipeline.py --split test --out-dir starter/results/advanced-test
    python scripts/adv_grade_and_summarize.py
    ```
