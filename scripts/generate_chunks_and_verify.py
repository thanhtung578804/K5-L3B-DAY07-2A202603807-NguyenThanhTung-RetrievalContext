import json
import sys
from pathlib import Path

# Add Day 6 starter to sys.path
day6_src = Path(r"C:\Users\tungh\K5-L3B-DAY06-NguyenThanhTung-26A202603807-DataIngestion\starter")
sys.path.insert(0, str(day6_src))

from src.ingestion import load_pdf
from src.chunking import by_paragraph

day7_dir = Path(__file__).resolve().parents[1]
pdf_path = day7_dir / "data" / "So tay sinh vien_2026.pdf"

print(f"Loading PDF from {pdf_path}...")
pages = load_pdf(pdf_path, document_id="so-tay-sv-hust-2026", source="data/So tay sinh vien_2026.pdf")
print(f"Loaded {len(pages)} pages.")

chunks = []
for p in pages:
    chunks.extend(by_paragraph(p, max_size=600))
print(f"Generated {len(chunks)} chunks.")

# Format chunks to Day 7 schema
day7_chunks = []
for c in chunks:
    day7_chunks.append({
        "id": c.chunk_id,
        "source_id": c.document_id,
        "source": c.source,
        "page": c.page,
        "text": c.text,
        "metadata": c.metadata
    })

chunks_out = day7_dir / "data" / "chunks.json"
chunks_out.write_text(json.dumps(day7_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(day7_chunks)} chunks to {chunks_out}")

# Now let's check Day 6 benchmark questions against these chunks
day6_bm_file = Path(r"C:\Users\tungh\K5-L3B-DAY06-NguyenThanhTung-26A202603807-DataIngestion\benchmark\benchmark.json")
raw_questions = json.loads(day6_bm_file.read_text(encoding="utf-8"))

sys.path.insert(0, str(day7_dir / "starter"))
from convert_day6 import convert_question
from baseline import validate, hit

converted_questions = [convert_question(q) for q in raw_questions]

# Test each question against the chunks
missing_evidence = []
for q in converted_questions:
    matched = False
    for g in q['gold']:
        matching_chunks = [c for c in day7_chunks if hit(c, [g])]
        if matching_chunks:
            matched = True
            break
    if not matched:
        missing_evidence.append(q['id'])

if missing_evidence:
    print(f"WARNING: The following questions could not find evidence in chunks: {missing_evidence}")
else:
    print("ALL 20 Day 6 questions successfully matched evidence in the chunks!")
