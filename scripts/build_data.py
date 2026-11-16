import json
import sys
from pathlib import Path

day7_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(day7_dir / "starter"))
from baseline import validate

chunks = json.loads((day7_dir / "data" / "chunks.json").read_text(encoding="utf-8"))
day6_bm = json.loads(Path(r"C:\Users\tungh\K5-L3B-DAY06-NguyenThanhTung-26A202603807-DataIngestion\benchmark\benchmark.json").read_text(encoding="utf-8"))

# Evidence overrides for the 4 questions that had minor formatting/ellipsis differences
EVIDENCE_OVERRIDES = {
    "q11": "Theo Thông tư số 40/2026/TT-BGDĐT, có 4 hình thức xử lý kỷ luật sinh viên gồm:\n1. Khiển trách;\n2. Cảnh cáo;\n3. Đình chỉ học tập có thời hạn;\n4. Buộc thôi học.",
    "q15": "làm gia sư các môn như Toán, Lý, Hóa, Tiếng Anh, Tin học",
    "q17": "c chương trình tích hợp cử nhân - thạc sĩ sẽ học chương trình 4 năm và được nhận được bằng tốt nghiệp cử nhân; sau đó nếu học tiếp 1,5 năm theo chương trình thạc sĩ tích hợp sẽ được cấp bằng tốt nghiệp",
    "q20": "HUST.EDU.VN CTT.HUST.EDU.VN Đây là trang thông tin chính thức của Đại học"
}

# 1. Build questions.json (answerable questions with gold evidence)
questions = []
for q in day6_bm:
    ev = EVIDENCE_OVERRIDES.get(q["id"], q["evidence_quote"])
    gold = [{
        "source_id": q["gold_source_id"],
        "page": q["gold_page"],
        "evidence": ev
    }]
    item = {
        "id": q["id"],
        "split": q["split"],
        "question": q["question"],
        "gold": gold,
        "expected_answer": q["expected_answer"]
    }
    if q.get("filter"):
        item["filter"] = q["filter"]
    questions.append(item)

# 2. Build cases.json (24 benchmark cases: 17 dev + 7 test)
unanswerable_cases = [
    {
        "id": "q21_unans",
        "split": "dev",
        "question": "Hạn cuối đăng ký tham gia chương trình trao đổi sinh viên tại Đại học Tokyo Nhật Bản trong học kỳ 1 năm học 2026-2027 là ngày nào?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Sổ tay sinh viên ĐHBK Hà Nội chỉ giới thiệu các ban ngành và hoạt động chung, không có thông tin chi tiết về thời hạn chương trình trao đổi cụ thể với Đại học Tokyo."
    },
    {
        "id": "q22_unans",
        "split": "dev",
        "question": "Mức học phí chính xác của khóa học lái xe ô tô hạng B2 dành cho sinh viên Bách khoa là bao nhiêu tiền?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Tài liệu chỉ đề cập các hỗ trợ hướng nghiệp và kỹ năng, không có quy định về biểu phí khóa học lái xe ô tô."
    },
    {
        "id": "q23_unans",
        "split": "test",
        "question": "Thủ tục đăng ký tạm trú cho sinh viên quốc tế tại ký túc xá Bách khoa cần nộp giấy khám sức khỏe của bệnh viện nào?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Sổ tay sinh viên 2026 không quy định chi tiết về danh sách bệnh viện khám sức khỏe cho sinh viên quốc tế tại ký túc xá."
    },
    {
        "id": "q24_unans",
        "split": "test",
        "question": "Thời gian mở cửa phục vụ xuyên đêm 24/7 của thư viện Tạ Quang Bửu trong mùa thi bắt đầu từ mấy giờ?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Tài liệu giới thiệu thư viện Tạ Quang Bửu nhưng không có thông tin về dịch vụ mở cửa xuyên đêm 24/7."
    }
]

cases = []
for q in questions:
    cases.append({
        "id": q["id"],
        "split": q["split"],
        "question": q["question"],
        "answerable": True,
        "expected_behavior": "search_and_answer",
        "expected_answer": q["expected_answer"]
    })
cases.extend(unanswerable_cases)

# Save files
q_path = day7_dir / "data" / "questions.json"
q_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(questions)} answerable questions to {q_path}")

cases_path = day7_dir / "data" / "cases.json"
cases_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(cases)} benchmark cases to {cases_path}")

# Run validation on dev and test questions
dev_questions = [q for q in questions if q["split"] == "dev"]
test_questions = [q for q in questions if q["split"] == "test"]

print("\n--- Validating dev questions ---")
validate(chunks, dev_questions)
print(f"Dev questions validation PASSED! ({len(dev_questions)} questions)")

print("\n--- Validating test questions ---")
validate(chunks, test_questions)
print(f"Test questions validation PASSED! ({len(test_questions)} questions)")

print(f"\nBenchmark summary:")
print(f"  Dev cases: {sum(1 for c in cases if c['split'] == 'dev')} (Answerable: {sum(1 for c in cases if c['split'] == 'dev' and c['answerable'])}, Unanswerable: {sum(1 for c in cases if c['split'] == 'dev' and not c['answerable'])})")
print(f"  Test cases: {sum(1 for c in cases if c['split'] == 'test')} (Answerable: {sum(1 for c in cases if c['split'] == 'test' and c['answerable'])}, Unanswerable: {sum(1 for c in cases if c['split'] == 'test' and not c['answerable'])})")
print(f"  Total cases: {len(cases)}")
