"""Run Agentic RAG pipeline using real Gemini LLM and Hybrid Retriever on Dev and Test splits.

Saves full traces adhering to starter/agent_metrics.py expectations.
"""
import json
import sys
import time
from pathlib import Path

day7_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(day7_dir / "src"))
sys.path.insert(0, str(day7_dir / "starter"))

from agentic import run_agent
from retrieval import TfidfRetriever, DenseRetriever, HybridRetriever
from agent import get_default_controller

chunks = json.loads((day7_dir / "data" / "chunks.json").read_text(encoding="utf-8"))
cases = json.loads((day7_dir / "data" / "cases.json").read_text(encoding="utf-8"))
chunk_embeddings = json.loads((day7_dir / "data" / "chunk_embeddings.json").read_text(encoding="utf-8"))
query_cache_path = day7_dir / "data" / "query_embeddings.json"

tfidf_retriever = TfidfRetriever(chunks)
dense_retriever = DenseRetriever(chunks, chunk_embeddings, query_cache_path=query_cache_path)
hybrid_retriever = HybridRetriever(dense_retriever, tfidf_retriever, rrf_k=60)

controller = get_default_controller(temperature=0.0)
print(f"Agent controller initialized: {type(controller).__name__} (Model: {controller.model_name})")

results_base = day7_dir / "starter" / "results"

for split_name in ("dev", "test"):
    split_cases = [c for c in cases if c.get("split") == split_name]
    print(f"\n{'=' * 80}")
    print(f"RUNNING AGENTIC RAG PIPELINE ON {split_name.upper()} ({len(split_cases)} cases)")
    print(f"{'=' * 80}")
    
    traces = []
    out_dir = results_base / f"agent-{split_name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, case in enumerate(split_cases, 1):
        cid = case["id"]
        q_text = case["question"]
        ans_expected = case["answerable"]
        
        print(f"[{idx}/{len(split_cases)}] Case {cid} (Answerable: {ans_expected}): {q_text[:65]}...")
        
        start_time = time.perf_counter()
        try:
            res = run_agent(
                question=q_text,
                controller=controller,
                retriever=hybrid_retriever,
                max_searches=3,
                top_k=3,
                budget=1200
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            res["query_id"] = cid
            res["elapsed_ms"] = elapsed_ms
            traces.append(res)
            
            tool_calls = sum(1 for e in res.get("events", []) if e.get("event") == "search")
            print(f"    Status: {res['status']} | Tool calls: {tool_calls} | Citations: {res['citations']} | Latency: {elapsed_ms:.1f}ms")
            print(f"    Answer: {res['answer'][:120]}...")
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            print(f"    ERROR running agent for {cid}: {e}")
            traces.append({
                "query_id": cid,
                "status": "error",
                "answer": f"Error: {e}",
                "citations": [],
                "events": [],
                "elapsed_ms": elapsed_ms
            })
            
        # Small delay between agent runs to respect API quotas
        time.sleep(2)
        
    traces_file = out_dir / "traces.json"
    traces_file.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(traces)} traces to {traces_file}")

print("\nAgent pipeline execution completed for both Dev and Test splits!")
