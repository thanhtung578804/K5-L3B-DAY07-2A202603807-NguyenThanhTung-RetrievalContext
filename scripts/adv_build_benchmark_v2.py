import json
import os
from collections import Counter

# Load existing Dev cases so Dev remains unchanged
old_cases = json.load(open("data/advanced/cases.json", encoding="utf-8"))
dev_cases = [c for c in old_cases if c["split"] == "dev"]

# Brand-new independent 30 Test cases (Test v2)
test_v2 = [
    # --- TABLE (6) ---
    {
        "id": "adv_test2_tbl_1",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "Theo bảng Các chỉ tiêu tài chính quan trọng (trang 11), Hệ số nợ trên Vốn chủ sở hữu của Vinamilk năm 2022 và năm 2025 lần lượt là bao nhiêu phần trăm?",
        "expected_answer": "Năm 2022 là 15,0% và năm 2025 là 27,4%",
        "source_page": 11,
        "evidence_location": "data/advanced/page_images/page_011.png | Bảng: Các chỉ tiêu tài chính quan trọng -> Dòng: Hệ số nợ/Vốn chủ sở hữu -> Cột 2022 và 2025",
        "reason": "Tra đúng hàng Hệ số nợ/VCSH và 2 cột năm."
    },
    {
        "id": "adv_test2_tbl_2",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "Theo bảng Các chỉ tiêu tài chính quan trọng (trang 11), Vòng quay hàng tồn kho của Vinamilk năm 2023 và năm 2025 lần lượt là bao nhiêu?",
        "expected_answer": "Năm 2023 là 6,14 và năm 2025 là 5,98",
        "source_page": 11,
        "evidence_location": "data/advanced/page_images/page_011.png | Bảng: Các chỉ tiêu tài chính quan trọng -> Dòng: Vòng quay hàng tồn kho -> Cột 2023 và 2025",
        "reason": "Tra đúng dòng Vòng quay hàng tồn kho năm 2023 và 2025."
    },
    {
        "id": "adv_test2_tbl_3",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "Theo danh sách cổ đông lớn trên trang 12, Platinum Victory Pte., Ltd nắm giữ bao nhiêu cổ phần và tỷ lệ sở hữu bao nhiêu phần trăm?",
        "expected_answer": "125.761.922 cổ phần, tỷ lệ sở hữu 6,02%",
        "source_page": 12,
        "evidence_location": "data/advanced/page_images/page_012.png | Bảng danh sách 20 cổ đông -> Dòng 3: Platinum Victory Pte., Ltd",
        "reason": "Tra đúng dòng cổ đông Platinum Victory Pte., Ltd."
    },
    {
        "id": "adv_test2_tbl_4",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "Theo Bảng 1 (Theo Báo cáo tài chính riêng tại trang 72), Tổng nợ vay ngắn hạn và dài hạn của Vinamilk tại ngày 31/12/2025 là bao nhiêu tỷ đồng?",
        "expected_answer": "8.841 tỷ đồng",
        "source_page": 72,
        "evidence_location": "data/advanced/page_images/page_072.png | Bảng 1: Theo BCTC riêng -> Dòng: Tổng nợ vay ngắn hạn và dài hạn -> Cột 31/12/2025",
        "reason": "Phân biệt đúng Bảng 1 (riêng) với Bảng 2 (hợp nhất)."
    },
    {
        "id": "adv_test2_tbl_5",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "Theo Báo cáo tình hình tài chính hợp nhất (trang 108), Tiền và các khoản tương đương tiền của Vinamilk tại ngày 31/12/2025 là bao nhiêu triệu VND?",
        "expected_answer": "1.794.880 triệu VND",
        "source_page": 108,
        "evidence_location": "data/advanced/page_images/page_108.png | Bảng 1: Tài sản -> Dòng: Tiền và các khoản tương đương tiền -> Cột 31/12/2025",
        "reason": "Tra đúng dòng Tiền và tương đương tiền cùng đơn vị triệu VND."
    },
    {
        "id": "adv_test2_tbl_6",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "Theo Báo cáo kết quả hoạt động kinh doanh hợp nhất (trang 109), Giá vốn hàng bán và dịch vụ cung cấp năm 2025 của Vinamilk là bao nhiêu triệu VND?",
        "expected_answer": "38.706.720 triệu VND",
        "source_page": 109,
        "evidence_location": "data/advanced/page_images/page_109.png | Bảng KQKD -> Dòng: Giá vốn hàng bán và dịch vụ cung cấp -> Cột 2025",
        "reason": "Tra đúng dòng Giá vốn hàng bán năm 2025."
    },

    # --- IMAGE / DIAGRAM (5) ---
    {
        "id": "adv_test2_img_1",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "Theo sơ đồ Lịch sử hình thành (trang 7), vào năm 2003 Vinamilk đã cổ phần hóa và đổi tên thành gì?",
        "expected_answer": "Công ty Cổ phần Sữa Việt Nam",
        "source_page": 7,
        "evidence_location": "data/advanced/page_images/page_007.png | Sơ đồ timeline Lịch sử hình thành -> Mốc 2003",
        "reason": "Đọc mốc lịch sử năm 2003 từ sơ đồ timeline."
    },
    {
        "id": "adv_test2_img_2",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "Theo trang 15 (Nhân sự chủ chốt Hội đồng Quản trị), ông Nguyễn Hạnh Phúc giữ những chức vụ gì tại Vinamilk?",
        "expected_answer": "Chủ tịch HĐQT, Chủ tịch Ủy ban Nhân sự, Thành viên Ủy ban Lương thưởng, Thành viên độc lập HĐQT",
        "source_page": 15,
        "evidence_location": "data/advanced/page_images/page_015.png | Hồ sơ Ông Nguyễn Hạnh Phúc",
        "reason": "Đọc thông tin chức vụ trên trang sơ đồ nhân sự HĐQT."
    },
    {
        "id": "adv_test2_img_3",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "Theo trang 40 (Dự án Trang trại bò sữa công nghệ cao), dự án trang trại này có quy mô bao nhiêu con và dự kiến đi vào hoạt động vào thời gian nào?",
        "expected_answer": "Quy mô 4.000 con, dự kiến đi vào hoạt động Quý III/2026",
        "source_page": 40,
        "evidence_location": "data/advanced/page_images/page_040.png | Khối thông tin số liệu góc trên bên trái",
        "reason": "Đọc thông tin quy mô và thời gian dự kiến từ infographic trang 40."
    },
    {
        "id": "adv_test2_img_4",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "Theo trang 39 (Giấy chứng nhận GLOBAL S.I.P. / GLOBALG.A.P.), giấy chứng nhận có số đăng ký BVC-VN VT25008 được cấp cho đơn vị nào và có ngày hết hạn là ngày nào?",
        "expected_answer": "Cấp cho VIET NAM DAIRY COW ONE-MEMBER COMPANY LIMITED (Công ty TNHH MTV Bò sữa Việt Nam), ngày hết hạn 26/11/2026",
        "source_page": 39,
        "evidence_location": "data/advanced/page_images/page_039.png | Ảnh Giấy chứng nhận bên trái (BVC-VN VT25008)",
        "reason": "Đọc chính xác thông tin từ ảnh chụp chứng nhận bên trái."
    },
    {
        "id": "adv_test2_img_5",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "Theo trang 14 (Cấu trúc tập đoàn Vinamilk), Vinamilk có bao nhiêu chi nhánh văn phòng bán hàng trong nước và đặt tại những thành phố nào?",
        "expected_answer": "03 chi nhánh văn phòng bán hàng tại Hà Nội, Đà Nẵng và Cần Thơ",
        "source_page": 14,
        "evidence_location": "data/advanced/page_images/page_014.png | Sơ đồ Cấu trúc tập đoàn Vinamilk",
        "reason": "Đọc chi tiết tên 3 thành phố của chi nhánh bán hàng từ sơ đồ."
    },

    # --- CHART (5) ---
    {
        "id": "adv_test2_cht_1",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "Theo biểu đồ Lợi nhuận từ HĐKD giai đoạn 2021 - 2025 (trang 10), lợi nhuận từ HĐKD của Vinamilk năm 2025 đạt bao nhiêu tỷ đồng?",
        "expected_answer": "11.660 tỷ đồng",
        "source_page": 10,
        "evidence_location": "data/advanced/page_images/page_010.png | Biểu đồ 3: Lợi nhuận từ HĐKD (tỷ đồng) -> Năm 2025",
        "reason": "Đọc giá trị cột năm 2025 trên biểu đồ Lợi nhuận từ HĐKD."
    },
    {
        "id": "adv_test2_cht_2",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "Theo biểu đồ Lợi nhuận trước thuế giai đoạn 2021 - 2025 (trang 10), lợi nhuận trước thuế năm 2021 và năm 2025 lần lượt là bao nhiêu tỷ đồng?",
        "expected_answer": "Năm 2021 là 12.922 tỷ đồng và năm 2025 là 11.650 tỷ đồng",
        "source_page": 10,
        "evidence_location": "data/advanced/page_images/page_010.png | Biểu đồ 4: Lợi nhuận trước thuế (tỷ đồng) -> Năm 2021 và 2025",
        "reason": "Đọc 2 giá trị đầu-cuối trên biểu đồ Lợi nhuận trước thuế."
    },
    {
        "id": "adv_test2_cht_3",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "Theo biểu đồ Tổng tài sản giai đoạn 2021 - 2025 (trang 10), tổng tài sản của Vinamilk năm 2025 đạt bao nhiêu tỷ đồng?",
        "expected_answer": "53.312 tỷ đồng",
        "source_page": 10,
        "evidence_location": "data/advanced/page_images/page_010.png | Biểu đồ 1: Tổng tài sản (tỷ đồng) -> Năm 2025",
        "reason": "Đọc giá trị cột 2025 trên biểu đồ Tổng tài sản."
    },
    {
        "id": "adv_test2_cht_4",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "Theo biểu đồ tròn Cơ cấu cổ đông (trong nước vs nước ngoài) trên trang 12, nhóm cổ đông nào chiếm tỷ lệ cao hơn và chiếm bao nhiêu phần trăm?",
        "expected_answer": "Cổ đông nước ngoài chiếm tỷ lệ cao hơn với 50,9% (so với cổ đông trong nước 49,1%)",
        "source_page": 12,
        "evidence_location": "data/advanced/page_images/page_012.png | Biểu đồ tròn: Cơ cấu cổ đông (trong nước / nước ngoài)",
        "reason": "So sánh 2 phần trên biểu đồ tròn."
    },
    {
        "id": "adv_test2_cht_5",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "Theo Biểu đồ 2: Biến động giá và Khối lượng giao dịch cổ phiếu VNM (trang 11), đường giá đóng cửa dao động trong khoảng biên độ bao nhiêu VNĐ trong năm 2025?",
        "expected_answer": "Khoảng 52.000 đến 65.100 VNĐ/cổ phiếu",
        "source_page": 11,
        "evidence_location": "data/advanced/page_images/page_011.png | Biểu đồ 2 & thông tin giá đóng cửa điều chỉnh",
        "reason": "Đọc biên độ dao động đường giá trên biểu đồ và trục Y phải."
    },

    # --- MULTI-HOP (4) ---
    {
        "id": "adv_test2_mh_1",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Theo biểu đồ Lợi nhuận từ HĐKD (trang 10), lợi nhuận từ HĐKD năm 2025 tăng thêm bao nhiêu tỷ đồng so với năm 2024?",
        "expected_answer": "Tăng 66 tỷ đồng (11.660 - 11.594)",
        "source_page": 10,
        "evidence_location": "data/advanced/page_images/page_010.png | Biểu đồ 3: Lợi nhuận từ HĐKD 2025 (11.660) và 2024 (11.594)",
        "reason": "Đọc hai cột 2024, 2025 và tính hiệu số."
    },
    {
        "id": "adv_test2_mh_2",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Kết hợp trang 10 và trang 11, mục tiêu cắt giảm phát thải khí nhà kính (Phạm vi 1 và 2) vào năm 2035 của Vinamilk là bao nhiêu phần trăm, và giá cổ phiếu VNM thấp nhất trong năm 2025 là bao nhiêu đồng?",
        "expected_answer": "Cắt giảm 63% vào năm 2035 (trang 10); giá cổ phiếu VNM thấp nhất năm 2025 là 52.000 đồng/cổ phiếu (trang 11)",
        "source_page": 10,
        "evidence_location": "data/advanced/page_images/page_010.png & page_011.png",
        "reason": "Tổng hợp thông tin từ trang 10 và trang 11."
    },
    {
        "id": "adv_test2_mh_3",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Theo Bảng 1 (trang 72) và trang 110, Nợ thuần / (Thặng dư tiền) theo BCTC riêng tại ngày 31/12/2025 là bao nhiêu tỷ đồng, và Lợi nhuận trước thuế hợp nhất năm 2025 theo Báo cáo lưu chuyển tiền tệ là bao nhiêu triệu VND?",
        "expected_answer": "Thặng dư tiền BCTC riêng tại 31/12/2025 là 8.587 tỷ đồng (ghi (8.587) tỷ đồng ở trang 72); Lợi nhuận trước thuế hợp nhất năm 2025 là 10.741.612 triệu VND (trang 110)",
        "source_page": 72,
        "evidence_location": "data/advanced/page_images/page_072.png & page_110.png",
        "reason": "Kết hợp số liệu từ Bảng 1 trang 72 và Bảng LCTT trang 110."
    },
    {
        "id": "adv_test2_mh_4",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Kết hợp thông tin từ trang 26 và trang 47, ngành sữa Việt Nam năm 2025 tăng trưởng bao nhiêu phần trăm, và doanh thu xuất khẩu thương mại của Vinamilk năm 2025 đạt bao nhiêu tỷ đồng?",
        "expected_answer": "Ngành sữa Việt Nam năm 2025 tăng trưởng -2,4% (trang 26); doanh thu xuất khẩu thương mại đạt 6.546 tỷ đồng (trang 47)",
        "source_page": 26,
        "evidence_location": "data/advanced/page_images/page_026.png & page_047.png",
        "reason": "Kết hợp bối cảnh ngành trang 26 và kết quả xuất khẩu trang 47."
    },

    # --- TEXT (4) ---
    {
        "id": "adv_test2_txt_1",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "Theo trang 8 (Mô hình & chiến lược kinh doanh), phát biểu Tầm nhìn của Vinamilk là gì?",
        "expected_answer": "Trở thành biểu tượng niềm tin hàng đầu Việt Nam về sản phẩm dinh dưỡng và sức khỏe phục vụ cuộc sống con người",
        "source_page": 8,
        "evidence_location": "Trang 8 | Mục Tầm nhìn",
        "reason": "Trích xuất đúng câu Tầm nhìn của Vinamilk."
    },
    {
        "id": "adv_test2_txt_2",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "Theo trang 52 (Đơn vị thành viên), lợi nhuận trước thuế năm 2025 của công ty con Driftwood tại Mỹ so với kế hoạch và cùng kỳ như thế nào?",
        "expected_answer": "Lợi nhuận trước thuế tăng mạnh so với kế hoạch và so với cùng kỳ",
        "source_page": 52,
        "evidence_location": "Trang 52 | Mục 1. Driftwood",
        "reason": "Tìm đánh giá lợi nhuận trước thuế của Driftwood."
    },
    {
        "id": "adv_test2_txt_3",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "Theo trang 106 (Thông tin về Công ty), Giấy chứng nhận đăng ký doanh nghiệp lần đầu (ngày 20/11/2003) của Vinamilk mang số hiệu bao nhiêu?",
        "expected_answer": "4103001932",
        "source_page": 106,
        "evidence_location": "Trang 106 | Mục 1. Giấy Chứng nhận Đăng ký Doanh nghiệp",
        "reason": "Tìm đúng số đăng ký kinh doanh ban đầu năm 2003."
    },
    {
        "id": "adv_test2_txt_4",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "Theo trang 102 (Phát triển bền vững), các nhà máy của Vinamilk vận hành hệ thống xử lý nước thải tập trung đạt tiêu chuẩn quy chuẩn kỹ thuật quốc gia nào?",
        "expected_answer": "Đạt hoặc cao hơn QCVN 40:2011/BTNMT",
        "source_page": 102,
        "evidence_location": "Trang 102 | Phần môi trường & nước thải",
        "reason": "Tìm mã tiêu chuẩn môi trường QCVN của hệ thống xử lý nước thải."
    },

    # --- UNANSWERABLE (6) ---
    {
        "id": "adv_test2_unans_1",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "Tổng quỹ lương thưởng dự kiến cho năm 2028 của riêng khối Marketing Vinamilk là bao nhiêu tỷ đồng?",
        "expected_answer": "Không đủ bằng chứng để trả lời.",
        "source_page": None,
        "evidence_location": "Không có kế hoạch quỹ lương năm 2028 trong báo cáo",
        "reason": "Dữ liệu nằm ngoài phạm vi thời gian báo cáo 2025."
    },
    {
        "id": "adv_test2_unans_2",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "Trong năm 2025, Vinamilk đã mua lại bao nhiêu phần trăm cổ phần của hãng xe điện Tesla?",
        "expected_answer": "Không đủ bằng chứng để trả lời.",
        "source_page": None,
        "evidence_location": "Không có giao dịch nào liên quan đến Tesla trong báo cáo",
        "reason": "Sự kiện giả định không có trong báo cáo."
    },
    {
        "id": "adv_test2_unans_3",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "Bảng thống kê doanh số bán hàng tại tỉnh Bắc Cực ở trang 120 của báo cáo ghi nhận kết quả bao nhiêu tỷ đồng?",
        "expected_answer": "Không đủ bằng chứng để trả lời.",
        "source_page": None,
        "evidence_location": "Tài liệu chỉ có 112 trang, không có trang 120",
        "reason": "Trang không tồn tại và địa danh không hợp lệ."
    },
    {
        "id": "adv_test2_unans_4",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "Mã PIN thẻ ngân hàng doanh nghiệp của Công ty Cổ phần Sữa Việt Nam được công bố ở mục nào?",
        "expected_answer": "Không đủ bằng chứng để trả lời.",
        "source_page": None,
        "evidence_location": "Thông tin bảo mật ngân hàng không tồn tại trong báo cáo",
        "reason": "Thông tin bảo mật không công khai."
    },
    {
        "id": "adv_test2_unans_5",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "Có bao nhiêu con bò tại trang trại Vinamilk biết giải phương trình bậc hai trong năm 2025?",
        "expected_answer": "Không đủ bằng chứng để trả lời.",
        "source_page": None,
        "evidence_location": "Thông tin phi lý không tồn tại trong tài liệu",
        "reason": "Câu hỏi bẫy vô lý."
    },
    {
        "id": "adv_test2_unans_6",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "Tỷ lệ cổ tức bằng tiền mặt của Vinamilk cho quý 4 năm 2027 là bao nhiêu phần trăm?",
        "expected_answer": "Không đủ bằng chứng để trả lời.",
        "source_page": None,
        "evidence_location": "Chưa có số liệu năm 2027 trong báo cáo 2025",
        "reason": "Thời điểm tương lai ngoài phạm vi báo cáo."
    }
]

all_v2 = dev_cases + test_v2
with open("data/advanced/cases.json", "w", encoding="utf-8") as f:
    json.dump(all_v2, f, ensure_ascii=False, indent=2)

print("Saved updated cases.json! Total:", len(all_v2))
print("Test v2 categories:", dict(Counter(c["category"] for c in test_v2)))
