"""Retrieval pipelines for Day 7: Lexical (TF-IDF), Dense (Gemini Embedding), and Hybrid (RRF).

Complies with Day 7 benchmark schema, reproducible offline once embeddings are saved.
"""
import json
import math
import os
import re
import statistics
import time
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def tokenize(text: str) -> list[str]:
    """Tokenize Vietnamese text with NFC normalization and lowercase."""
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())


def hit(chunk: dict[str, Any], gold: list[dict[str, Any]]) -> bool:
    """Check if any gold evidence is satisfied by this chunk (correct source, page, and exact substring)."""
    return any(
        chunk.get("source_id") == g.get("source_id")
        and chunk.get("page") == g.get("page")
        and g.get("evidence", "") in chunk.get("text", "")
        for g in gold
    )


def pack_context(results: list[dict[str, Any]], budget: int = 800) -> tuple[str, list[str]]:
    """Pack top retrieved chunks into context within character budget, deduplicating chunks."""
    blocks, ids, seen = [], [], set()
    for c in results:
        cid = c["id"]
        if cid in seen:
            continue
        seen.add(cid)
        block = f"[{cid} | {c.get('source', '')} | page {c.get('page', '')}]\n{c.get('text', '')}"
        candidate_context = "\n\n".join(blocks + [block])
        if len(candidate_context) <= budget:
            blocks.append(block)
            ids.append(cid)
    return "\n\n".join(blocks), ids


class TfidfRetriever:
    """Lexical retrieval using TF-IDF and Cosine Similarity."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        counts = [Counter(tokenize(c["text"])) for c in chunks]
        df = Counter(term for row in counts for term in row)
        self.idf = {term: math.log((1 + len(chunks)) / (1 + count)) + 1 for term, count in df.items()}
        self.vectors = [self._vector(row) for row in counts]

    def _vector(self, counts: Counter) -> dict[str, float]:
        vector = {term: count * self.idf[term] for term, count in counts.items() if term in self.idf}
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        return {term: v / norm for term, v in vector.items()}

    def search(
        self,
        query: str,
        top_k: int = 3,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        query_vec = self._vector(Counter(tokenize(query)))
        results = []
        for chunk, vector in zip(self.chunks, self.vectors):
            if filters:
                match = True
                meta = chunk.get("metadata", {})
                for k, v in filters.items():
                    if k == "section" and meta.get("section") != v:
                        match = False
                        break
                    elif k == "page" and chunk.get("page") != v:
                        match = False
                        break
                if not match:
                    continue

            score = sum(val * vector.get(term, 0.0) for term, val in query_vec.items())
            if score > 0:
                results.append({**chunk, "score": float(score), "strategy": "tfidf"})

        return sorted(results, key=lambda c: (-c["score"], c["id"]))[:top_k]


class DenseRetriever:
    """Dense vector retrieval using real embeddings (Gemini embedding-001) and Cosine Similarity."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        chunk_embeddings: dict[str, list[float]],
        api_key: str | None = None,
        query_cache_path: Path | None = None
    ) -> None:
        self.chunks = chunks
        self.chunk_embeddings = chunk_embeddings
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment or .env file.")
        self.query_cache_path = query_cache_path
        self.query_cache: dict[str, list[float]] = {}
        if query_cache_path and query_cache_path.exists():
            try:
                self.query_cache = json.loads(query_cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.query_cache = {}

        # Precompute norms for speed
        self.chunk_norms = {}
        for cid, vec in self.chunk_embeddings.items():
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            self.chunk_norms[cid] = norm

    def embed_query(self, query: str) -> list[float]:
        cleaned = query.strip()
        if cleaned in self.query_cache:
            return self.query_cache[cleaned]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={self.api_key}"
        data = json.dumps({
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": cleaned}]}
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        # Retry with backoff
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    vec = res_json["embedding"]["values"]
                    self.query_cache[cleaned] = vec
                    if self.query_cache_path:
                        self.query_cache_path.write_text(json.dumps(self.query_cache), encoding="utf-8")
                    return vec
            except Exception as e:
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Failed to embed query: {query}")

    def search(
        self,
        query: str,
        top_k: int = 3,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        query_vec = self.embed_query(query)
        q_norm = math.sqrt(sum(x * x for x in query_vec)) or 1.0

        results = []
        for chunk in self.chunks:
            cid = chunk["id"]
            if cid not in self.chunk_embeddings:
                continue

            if filters:
                match = True
                meta = chunk.get("metadata", {})
                for k, v in filters.items():
                    if k == "section" and meta.get("section") != v:
                        match = False
                        break
                    elif k == "page" and chunk.get("page") != v:
                        match = False
                        break
                if not match:
                    continue

            d_vec = self.chunk_embeddings[cid]
            d_norm = self.chunk_norms[cid]
            dot = sum(q * d for q, d in zip(query_vec, d_vec))
            sim = dot / (q_norm * d_norm)
            results.append({**chunk, "score": float(sim), "strategy": "dense"})

        return sorted(results, key=lambda c: (-c["score"], c["id"]))[:top_k]


class HybridRetriever:
    """Hybrid Retrieval combining Dense and TF-IDF via Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        tfidf_retriever: TfidfRetriever,
        rrf_k: int = 60
    ) -> None:
        self.dense = dense_retriever
        self.tfidf = tfidf_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
        candidate_pool: int = 20
    ) -> list[dict[str, Any]]:
        dense_results = self.dense.search(query, top_k=candidate_pool, filters=filters)
        tfidf_results = self.tfidf.search(query, top_k=candidate_pool, filters=filters)

        scores: dict[str, float] = {}
        chunk_map: dict[str, dict[str, Any]] = {}

        for rank, c in enumerate(dense_results, start=1):
            cid = c["id"]
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))
            chunk_map[cid] = c

        for rank, c in enumerate(tfidf_results, start=1):
            cid = c["id"]
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = c

        combined = []
        for cid, score in scores.items():
            base = dict(chunk_map[cid])
            base["score"] = float(score)
            base["strategy"] = "hybrid_rrf"
            combined.append(base)

        return sorted(combined, key=lambda c: (-c["score"], c["id"]))[:top_k]


def evaluate_pipeline(
    retriever: Any,
    questions: list[dict[str, Any]],
    top_k: int = 3,
    budget: int = 800,
    strategy_name: str = "retriever",
    use_filters: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Evaluate retrieval pipeline on a split of questions, returning summary and traces."""
    traces = []
    times = []

    for q in questions:
        start = time.perf_counter()
        filters = q.get("filter") if use_filters else None
        results = retriever.search(q["question"], top_k=top_k, filters=filters)
        context, ids = pack_context(results, budget=budget)
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)

        gold = q.get("gold", [])
        marked_results = [{**c, "hit": hit(c, gold)} for c in results]
        h1 = bool(marked_results and marked_results[0]["hit"])
        h3 = any(c["hit"] for c in marked_results[:3])
        c_hit = any(c["hit"] and c["id"] in ids for c in marked_results)

        traces.append({
            "query_id": q["id"],
            "split": q.get("split", "dev"),
            "question": q["question"],
            "strategy": strategy_name,
            "top_k": top_k,
            "budget_chars": budget,
            "gold": gold,
            "results": marked_results,
            "context": context,
            "context_ids": ids,
            "context_chars": len(context),
            "elapsed_ms": elapsed_ms,
            "hit1": h1,
            "hit3": h3,
            "context_hit": c_hit
        })

    n = len(traces)
    summary = {
        "strategy": strategy_name,
        "split": questions[0].get("split", "dev") if questions else "unknown",
        "n": n,
        "hit1": sum(t["hit1"] for t in traces),
        "hit1_pct": round((sum(t["hit1"] for t in traces) / n) * 100, 2) if n else 0,
        "hit3": sum(t["hit3"] for t in traces),
        "hit3_pct": round((sum(t["hit3"] for t in traces) / n) * 100, 2) if n else 0,
        "context_hit": sum(t["context_hit"] for t in traces),
        "context_hit_pct": round((sum(t["context_hit"] for t in traces) / n) * 100, 2) if n else 0,
        "avg_context_chars": round(statistics.mean(t["context_chars"] for t in traces), 1) if n else 0,
        "median_ms": round(statistics.median(times), 2) if times else 0,
        "service_cost_usd": 0.0
    }
    return summary, traces
