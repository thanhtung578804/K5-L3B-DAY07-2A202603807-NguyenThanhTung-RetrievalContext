import argparse
import json
import os
import re
import time
import math
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

import sys
sys.path.insert(0, os.path.abspath("."))
from src.retrieval import TfidfRetriever, pack_context

load_dotenv()

CHUNKS_PATH = "data/advanced/chunks.json"
EMB_PATH = "data/advanced/chunk_embeddings.json"
CASES_PATH = "data/advanced/cases.json"

def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

class AdvancedHybridRetriever:
    def __init__(self, chunks: List[Dict[str, Any]], embeddings: Dict[str, List[float]]):
        self.chunks = chunks
        self.chunk_map = {c["id"]: c for c in chunks}
        self.embeddings = embeddings
        self.tfidf = TfidfRetriever(chunks)
        self.client = OpenAI()

    def search(self, query: str, top_k: int = 6, page_hint: Optional[int] = None) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []
        # Optional page filter if user explicitly asks "trang X" or agent passes page_hint
        candidates = self.chunks
        if page_hint is not None:
            filtered = [c for c in self.chunks if c.get("page") == page_hint]
            if filtered:
                candidates = filtered

        # 1. Lexical TF-IDF scores
        lex_hits = self.tfidf.search(query, top_k=min(len(self.chunks), 40))
        if page_hint is not None:
            lex_hits = [h for h in lex_hits if h.get("page") == page_hint] or lex_hits
        lex_rank = {h["id"]: rank + 1 for rank, h in enumerate(lex_hits)}

        # 2. Dense OpenAI embedding
        q_emb = None
        for _ in range(3):
            try:
                q_emb = self.client.embeddings.create(model="text-embedding-3-small", input=[query]).data[0].embedding
                break
            except Exception:
                time.sleep(2)
        if q_emb is None:
            q_emb = self.client.embeddings.create(model="text-embedding-3-small", input=[query]).data[0].embedding
        dense_scored = []
        for c in candidates:
            emb = self.embeddings.get(c["id"])
            if emb:
                dense_scored.append((cosine_sim(q_emb, emb), c))
        dense_scored.sort(key=lambda x: x[0], reverse=True)
        dense_rank = {c["id"]: rank + 1 for rank, (_, c) in enumerate(dense_scored[:40])}

        # 3. RRF Fusion (k=60) + slight boost for visual/table chunks if query mentions bảng/biểu đồ/sơ đồ
        visual_boost = any(w in query.lower() for w in ["bảng", "biểu đồ", "sơ đồ", "tỷ lệ", "cổ phần", "triệu vnd", "tỷ đồng", "tổng tài sản"])
        all_ids = set(lex_rank.keys()) | set(dense_rank.keys())
        fused = []
        for cid in all_ids:
            rrf = 0.0
            if cid in lex_rank:
                rrf += 1.0 / (60 + lex_rank[cid])
            if cid in dense_rank:
                rrf += 1.0 / (60 + dense_rank[cid])
            c = dict(self.chunk_map[cid])
            if visual_boost and c.get("type") == "visual":
                rrf *= 1.12
            c["score"] = rrf
            c["strategy"] = "adv_hybrid_rrf"
            fused.append(c)

        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:top_k]

def run_agent_case(case: Dict[str, Any], retriever: AdvancedHybridRetriever, client: OpenAI, max_searches: int = 3, budget_chars: int = 5200) -> Dict[str, Any]:
    t0 = time.perf_counter()
    events = []
    context_map: Dict[str, Dict[str, Any]] = {}
    context_order: List[str] = []

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Tìm kiếm thông tin trong Báo cáo thường niên Vinamilk 2025 (gồm văn bản, bảng tài chính, biểu đồ, sơ đồ). Có thể truyền page_hint nếu câu hỏi nhắc rõ số trang.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Từ khóa hoặc câu truy vấn tìm kiếm."},
                        "page_hint": {"type": "integer", "description": "Số trang PDF cụ thể nếu câu hỏi có nêu rõ (tùy chọn)."}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    system_prompt = (
        "Bạn là chuyên gia phân tích Báo cáo thường niên Vinamilk 2025 (112 trang). "
        "LUẬT BẮT BUỘC:\n"
        "1. LUÔN gọi tool `search` trước khi trả lời. Nếu câu hỏi hỏi về nhiều phần hoặc 2 trang khác nhau (multi-hop), hãy gọi `search` nhiều lần (tối đa 3 lần) để thu thập đủ bằng chứng.\n"
        "2. Nếu câu hỏi có nêu rõ số trang (ví dụ 'trang 11', 'trang 72'), hãy truyền `page_hint` tương ứng để lấy chính xác bảng/biểu đồ trang đó.\n"
        "3. Trả lời đầy đủ mọi ý được hỏi, CHÍNH XÁC tuyệt đối các con số, đơn vị (tỷ đồng, triệu VND, %, cổ phần, TEUs) và thực hiện phép tính cẩn thận nếu câu hỏi yêu cầu.\n"
        "4. BẮT BUỘC trích dẫn nguồn bằng đúng ID chunk theo định dạng `[chunk_id]` (ví dụ `[vnm2025_p011_vis_0]`). Chỉ dùng ID có trong ngữ cảnh đã tìm được.\n"
        "5. KIỂM TRA THỰC THỂ NGHIÊM NGẶT: Chỉ được trả lời khi ngữ cảnh tìm được CÓ NHẮC TRỰC TIẾP đến đúng đối tượng/sự kiện/thời điểm trong câu hỏi. Nếu ngữ cảnh không nhắc tới thực thể/sự kiện được hỏi (ví dụ hỏi về một giải đấu, tổ chức, sản phẩm, trang > 112, hoặc năm không có trong tài liệu), TUYỆT ĐỐI KHÔNG ĐOÁN MÒ — hãy từ chối ngay bằng câu: \"Không đủ bằng chứng để trả lời.\""
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": case["question"]}
    ]

    search_count = 0
    final_text = ""
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for step in range(5):
        use_tools = tools if search_count < max_searches else None
        kwargs: Dict[str, Any] = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.0,
        }
        if use_tools:
            kwargs["tools"] = use_tools
            if step == 0:
                kwargs["tool_choice"] = {"type": "function", "function": {"name": "search"}}

        resp = None
        for _ in range(3):
            try:
                resp = client.chat.completions.create(**kwargs)
                break
            except Exception:
                time.sleep(2)
        if resp is None:
            resp = client.chat.completions.create(**kwargs)
        if resp.usage:
            total_prompt_tokens += resp.usage.prompt_tokens
            total_completion_tokens += resp.usage.completion_tokens

        msg = resp.choices[0].message
        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls]
            })
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                q = args.get("query", case["question"])
                ph = args.get("page_hint")
                if search_count >= max_searches:
                    res = []
                else:
                    search_count += 1
                    res = retriever.search(q, top_k=8, page_hint=ph)

                for item in res:
                    if item["id"] not in context_map:
                        context_map[item["id"]] = item
                        context_order.append(item["id"])

                # Pack results of current search call within budget so multi-hop searches each deliver fresh evidence
                packed_ctx, packed_ids = pack_context(res, budget=budget_chars)
                events.append({
                    "event": "search",
                    "query": q,
                    "page_hint": ph,
                    "results_count": len(res),
                    "top_ids": [r["id"] for r in res],
                    "packed_ids": packed_ids,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": packed_ctx if packed_ctx else "Không tìm thấy kết quả phù hợp."
                })
        else:
            final_text = (msg.content or "").strip()
            break

    # Verify citations
    valid_ids = set(context_map.keys())
    raw_cits = re.findall(r"\[([A-Za-z0-9_.\-]+)\]", final_text)
    verified_cits = [c for c in raw_cits if c in valid_ids]
    # Deduplicate preserving order
    seen = set()
    verified_cits = [c for c in verified_cits if not (c in seen or seen.add(c))]

    is_abstain = ("không đủ bằng chứng" in final_text.lower()) or (len(verified_cits) == 0)
    status = "abstain" if is_abstain else "answered"
    if status == "abstain" and "không đủ bằng chứng" not in final_text.lower():
        final_text = "Không đủ bằng chứng để trả lời."
        verified_cits = []

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    est_cost_usd = round((total_prompt_tokens * 0.15 + total_completion_tokens * 0.60) / 1_000_000, 6)

    return {
        "query_id": case["id"],
        "split": case["split"],
        "category": case["category"],
        "answerable": case["answerable"],
        "question": case["question"],
        "expected_answer": case["expected_answer"],
        "status": status,
        "answer": final_text,
        "citations": verified_cits,
        "events": events,
        "search_calls": search_count,
        "elapsed_ms": elapsed_ms,
        "tokens": {"prompt": total_prompt_tokens, "completion": total_completion_tokens},
        "est_cost_usd": est_cost_usd,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    chunks = json.load(open(CHUNKS_PATH, encoding="utf-8"))
    embeddings = json.load(open(EMB_PATH, encoding="utf-8"))
    cases = [c for c in json.load(open(CASES_PATH, encoding="utf-8")) if c["split"] == args.split]

    retriever = AdvancedHybridRetriever(chunks, embeddings)
    client = OpenAI()

    traces = []
    for idx, c in enumerate(cases, 1):
        tr = run_agent_case(c, retriever, client)
        traces.append(tr)
        print(f"[{idx}/{len(cases)}] {tr['query_id']} ({tr['category']}) -> {tr['status']} | cits={tr['citations']} | {tr['elapsed_ms']}ms")

    out_traces = os.path.join(args.out_dir, "traces.json")
    with open(out_traces, "w", encoding="utf-8") as f:
        json.dump(traces, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(traces)} traces to {out_traces}")

if __name__ == "__main__":
    main()
