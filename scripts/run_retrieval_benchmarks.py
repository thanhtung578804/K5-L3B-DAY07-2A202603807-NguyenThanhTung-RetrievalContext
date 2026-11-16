"""Run retrieval experiments and benchmarks on Dev split for all 3 methods + 2 improvements.

Produces summary.json and traces.json in starter/results/ for each configuration.
"""
import json
import sys
from pathlib import Path

day7_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(day7_dir / "src"))

from retrieval import (
    TfidfRetriever,
    DenseRetriever,
    HybridRetriever,
    evaluate_pipeline
)

chunks = json.loads((day7_dir / "data" / "chunks.json").read_text(encoding="utf-8"))
questions = json.loads((day7_dir / "data" / "questions.json").read_text(encoding="utf-8"))
chunk_embeddings = json.loads((day7_dir / "data" / "chunk_embeddings.json").read_text(encoding="utf-8"))
query_cache_path = day7_dir / "data" / "query_embeddings.json"

dev_questions = [q for q in questions if q.get("split") == "dev"]
test_questions = [q for q in questions if q.get("split") == "test"]

print(f"Loaded {len(chunks)} chunks, {len(dev_questions)} dev questions, {len(test_questions)} test questions.")

# Initialize retrievers
tfidf_retriever = TfidfRetriever(chunks)
dense_retriever = DenseRetriever(chunks, chunk_embeddings, query_cache_path=query_cache_path)
hybrid_retriever = HybridRetriever(dense_retriever, tfidf_retriever, rrf_k=60)

results_dir = day7_dir / "starter" / "results"
results_dir.mkdir(parents=True, exist_ok=True)

experiments = [
    {
        "id": "exp1_dev_tfidf",
        "name": "Method 1: TF-IDF Lexical Baseline",
        "retriever": tfidf_retriever,
        "questions": dev_questions,
        "top_k": 3,
        "budget": 800,
        "use_filters": False
    },
    {
        "id": "exp2_dev_dense",
        "name": "Method 2: Gemini Dense Retrieval",
        "retriever": dense_retriever,
        "questions": dev_questions,
        "top_k": 3,
        "budget": 800,
        "use_filters": False
    },
    {
        "id": "exp3_dev_hybrid",
        "name": "Method 3: Hybrid Retrieval (Dense + TF-IDF RRF)",
        "retriever": hybrid_retriever,
        "questions": dev_questions,
        "top_k": 3,
        "budget": 800,
        "use_filters": False
    },
    {
        "id": "exp4_dev_hybrid_filter",
        "name": "Improvement 1: Hybrid RRF + Metadata Filtering",
        "retriever": hybrid_retriever,
        "questions": dev_questions,
        "top_k": 3,
        "budget": 800,
        "use_filters": True
    },
    {
        "id": "exp5_dev_hybrid_budget1200",
        "name": "Improvement 2: Hybrid RRF + Budget 1200",
        "retriever": hybrid_retriever,
        "questions": dev_questions,
        "top_k": 3,
        "budget": 1200,
        "use_filters": False
    }
]

benchmark_summaries = {}

print("\n" + "=" * 90)
print(f"{'Config ID':<25} | {'Hit@1':<12} | {'Hit@3':<12} | {'Context Hit':<14} | {'Med ms':<8} | {'Avg chars':<10}")
print("-" * 90)

for exp in experiments:
    exp_dir = results_dir / exp["id"]
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    summary, traces = evaluate_pipeline(
        retriever=exp["retriever"],
        questions=exp["questions"],
        top_k=exp["top_k"],
        budget=exp["budget"],
        strategy_name=exp["name"],
        use_filters=exp["use_filters"]
    )
    
    (exp_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (exp_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    
    benchmark_summaries[exp["id"]] = summary
    
    h1_str = f"{summary['hit1']}/{summary['n']} ({summary['hit1_pct']}%)"
    h3_str = f"{summary['hit3']}/{summary['n']} ({summary['hit3_pct']}%)"
    ctx_str = f"{summary['context_hit']}/{summary['n']} ({summary['context_hit_pct']}%)"
    
    print(f"{exp['id']:<25} | {h1_str:<12} | {h3_str:<12} | {ctx_str:<14} | {summary['median_ms']:<8.2f} | {summary['avg_context_chars']:<10.1f}")

print("=" * 90 + "\n")

# Now evaluate on Test split for Baseline vs Best Selected Config (Hybrid RRF Budget 1200)
test_exps = [
    {
        "id": "exp_test_tfidf",
        "name": "Baseline Test: TF-IDF",
        "retriever": tfidf_retriever,
        "questions": test_questions,
        "top_k": 3,
        "budget": 800,
        "use_filters": False
    },
    {
        "id": "exp_test_selected_hybrid",
        "name": "Selected Config Test: Hybrid RRF Budget 1200",
        "retriever": hybrid_retriever,
        "questions": test_questions,
        "top_k": 3,
        "budget": 1200,
        "use_filters": False
    }
]

print("=" * 90)
print(f"{'Test Config ID':<25} | {'Hit@1':<12} | {'Hit@3':<12} | {'Context Hit':<14} | {'Med ms':<8} | {'Avg chars':<10}")
print("-" * 90)

for exp in test_exps:
    exp_dir = results_dir / exp["id"]
    exp_dir.mkdir(parents=True, exist_ok=True)
    summary, traces = evaluate_pipeline(
        retriever=exp["retriever"],
        questions=exp["questions"],
        top_k=exp["top_k"],
        budget=exp["budget"],
        strategy_name=exp["name"],
        use_filters=exp["use_filters"]
    )
    (exp_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (exp_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    benchmark_summaries[exp["id"]] = summary
    h1_str = f"{summary['hit1']}/{summary['n']} ({summary['hit1_pct']}%)"
    h3_str = f"{summary['hit3']}/{summary['n']} ({summary['hit3_pct']}%)"
    ctx_str = f"{summary['context_hit']}/{summary['n']} ({summary['context_hit_pct']}%)"
    print(f"{exp['id']:<25} | {h1_str:<12} | {h3_str:<12} | {ctx_str:<14} | {summary['median_ms']:<8.2f} | {summary['avg_context_chars']:<10.1f}")

print("=" * 90 + "\n")

# Save combined summary comparison
(results_dir / "retrieval_comparison.json").write_text(
    json.dumps(benchmark_summaries, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print("All retrieval benchmark artifacts saved to starter/results/!")
