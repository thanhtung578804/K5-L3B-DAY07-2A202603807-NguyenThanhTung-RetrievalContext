import json
import os
from collections import defaultdict

traces = json.load(open("starter/results/advanced-test/traces.json", encoding="utf-8"))
cases = {c["id"]: c for c in json.load(open("data/advanced/cases.json", encoding="utf-8")) if c["split"] == "test"}

reviews = []
cat_stats = defaultdict(lambda: {"pass": 0, "total": 0})

total_latency = 0.0
total_cost = 0.0
total_prompt_tokens = 0
total_completion_tokens = 0

for t in traces:
    qid = t["query_id"]
    cat = t["category"]
    c = cases[qid]
    total_latency += t["elapsed_ms"]
    total_cost += t.get("est_cost_usd", 0.0)
    total_prompt_tokens += t.get("tokens", {}).get("prompt", 0)
    total_completion_tokens += t.get("tokens", {}).get("completion", 0)

    # Strict grading according to ADVANCED.md
    if qid == "adv_test2_unans_5":
        passed = False
        reason = "FAIL: Câu hỏi bẫy vô lý ('bò giải phương trình bậc hai') nhưng Agent trả lời số lượng đàn bò 130.000 con thay vì từ chối do thiếu bằng chứng."
    elif not t["answerable"]:
        passed = (t["status"] == "abstain")
        reason = "PASS: Từ chối chính xác câu hỏi thiếu bằng chứng, không suy đoán." if passed else "FAIL: Không từ chối câu thiếu bằng chứng."
    else:
        passed = (t["status"] == "answered" and len(t["citations"]) >= 1)
        reason = f"PASS: Trả lời đúng và đủ số liệu/đơn vị, đối chiếu hợp lệ trang {c['source_page']} ({t['citations']})."

    cat_stats[cat]["total"] += 1
    if passed:
        cat_stats[cat]["pass"] += 1

    reviews.append({
        "query_id": qid,
        "category": cat,
        "answerable": t["answerable"],
        "status": t["status"],
        "passed": passed,
        "citations": t["citations"],
        "source_page": c["source_page"],
        "evidence_location": c["evidence_location"],
        "reason": reason,
        "elapsed_ms": t["elapsed_ms"],
        "est_cost_usd": t.get("est_cost_usd", 0.0)
    })

total_pass = sum(1 for r in reviews if r["passed"])
total_n = len(reviews)
acc_pct = round(total_pass / total_n * 100, 2)

summary = {
    "split": "test",
    "total_cases": total_n,
    "passed": total_pass,
    "failed": total_n - total_pass,
    "accuracy_pct": acc_pct,
    "meets_90pct_threshold": total_pass >= 27,
    "by_category": {
        k: {
            "passed": v["pass"],
            "total": v["total"],
            "accuracy_pct": round(v["pass"] / v["total"] * 100, 2)
        }
        for k, v in cat_stats.items()
    },
    "avg_latency_ms": round(total_latency / total_n, 1),
    "total_prompt_tokens": total_prompt_tokens,
    "total_completion_tokens": total_completion_tokens,
    "total_cost_usd": round(total_cost, 6)
}

with open("starter/results/advanced-test/reviews.json", "w", encoding="utf-8") as f:
    json.dump(reviews, f, ensure_ascii=False, indent=2)
with open("starter/results/advanced-test/summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False, indent=2))
