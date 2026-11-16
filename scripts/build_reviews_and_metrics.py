import json
import subprocess
import sys
from pathlib import Path

day7_dir = Path(__file__).resolve().parents[1]

# 1. Build test reviews
test_reviews = [
    {
        "query_id": "q16",
        "answer_grade": 1,
        "citation_support": [True],
        "comment": "Trúng sự kiện khu trường mới nhưng nhầm lẫn giữa năm khởi công 1960 và khánh thành 1965."
    },
    {
        "query_id": "q17",
        "answer_grade": 2,
        "citation_support": [True],
        "comment": "Trả lời hoàn toàn chính xác và đầy đủ: Cử nhân 4 năm, Thạc sĩ 1.5 năm, tổng 5.5 năm."
    },
    {
        "query_id": "q18",
        "answer_grade": 2,
        "citation_support": [True],
        "comment": "Chính xác tuyệt đối: cộng 4 điểm rèn luyện."
    },
    {
        "query_id": "q19",
        "answer_grade": 2,
        "citation_support": [True],
        "comment": "Chính xác và đầy đủ đối tượng sinh viên hệ đại học chính quy."
    },
    {
        "query_id": "q20",
        "answer_grade": 2,
        "citation_support": [True],
        "comment": "Chính xác đầy đủ cả 2 trang thông tin điện tử HUST.EDU.VN và CTT.HUST.EDU.VN."
    },
    {
        "query_id": "q23_unans",
        "abstention_correct": True,
        "citation_support": [],
        "comment": "Từ chối chính xác: Sổ tay sinh viên 2026 không quy định danh sách bệnh viện khám sức khỏe cho sinh viên quốc tế."
    },
    {
        "query_id": "q24_unans",
        "abstention_correct": True,
        "citation_support": [],
        "comment": "Từ chối chính xác: Thư viện Tạ Quang Bửu không có dịch vụ mở cửa xuyên đêm 24/7."
    }
]

test_rev_file = day7_dir / "starter" / "results" / "agent-test" / "reviews.json"
test_rev_file.write_text(json.dumps(test_reviews, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved test reviews to {test_rev_file}")

# 2. Build dev reviews
dev_reviews = [
    {"query_id": "q01", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q02", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q03", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q04", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q05", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q06", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q07", "answer_grade": 1, "citation_support": [True]},
    {"query_id": "q08", "answer_grade": 1, "citation_support": [True]},
    {"query_id": "q09", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q10", "answer_grade": 0, "citation_support": []},
    {"query_id": "q11", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q12", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q13", "answer_grade": 2, "citation_support": [True]},
    {"query_id": "q14", "answer_grade": 2, "citation_support": [True, True]},
    {"query_id": "q15", "answer_grade": 0, "citation_support": []},
    {"query_id": "q21_unans", "abstention_correct": True, "citation_support": []},
    {"query_id": "q22_unans", "abstention_correct": True, "citation_support": []}
]

dev_rev_file = day7_dir / "starter" / "results" / "agent-dev" / "reviews.json"
dev_rev_file.write_text(json.dumps(dev_reviews, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved dev reviews to {dev_rev_file}")

# 3. Run starter/agent_metrics.py on Test and Dev
sys.path.insert(0, str(day7_dir / "starter"))
from agent_metrics import aggregate

cases = json.loads((day7_dir / "data" / "cases.json").read_text(encoding="utf-8"))

for split in ("dev", "test"):
    sp_cases = [c for c in cases if c.get("split") == split]
    sp_traces = json.loads((day7_dir / "starter" / "results" / f"agent-{split}" / "traces.json").read_text(encoding="utf-8"))
    sp_revs = json.loads((day7_dir / "starter" / "results" / f"agent-{split}" / "reviews.json").read_text(encoding="utf-8"))
    
    summary = {"split": split, **aggregate(sp_cases, sp_traces, sp_revs)}
    out_file = day7_dir / "starter" / "results" / f"agent-{split}" / "summary.json"
    out_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n--- Summary for AGENT {split.upper()} ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
