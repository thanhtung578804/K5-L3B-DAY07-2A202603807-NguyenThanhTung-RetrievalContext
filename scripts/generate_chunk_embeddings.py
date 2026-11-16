import json
import os
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

day7_dir = Path(__file__).resolve().parents[1]
load_dotenv(day7_dir / ".env")
chunks_path = day7_dir / "data" / "chunks.json"
chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
out_path = day7_dir / "data" / "chunk_embeddings.json"

results = {}
if out_path.exists():
    try:
        results = json.loads(out_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(results)} existing embeddings from {out_path.name}")
    except Exception:
        results = {}

if len(results) == len(chunks):
    print(f"All {len(chunks)} embeddings already generated!")
    exit(0)

key = os.getenv("GEMINI_API_KEY", "")
if not key:
    raise RuntimeError("Missing GEMINI_API_KEY in environment or .env")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={key}"

batch_size = 35

unembedded = [c for c in chunks if c["id"] not in results]
print(f"Total chunks: {len(chunks)}, Remaining to embed: {len(unembedded)}")

for i in range(0, len(unembedded), batch_size):
    batch = unembedded[i:i + batch_size]
    batch_num = i // batch_size + 1
    total_batches = (len(unembedded) + batch_size - 1) // batch_size
    print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
    
    requests = []
    for c in batch:
        text = f"Trang {c['page']} | Chủ đề {c.get('metadata', {}).get('section', '')}\n{c['text']}"
        requests.append({
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": text[:1500]}]}
        })
    
    req = urllib.request.Request(
        url,
        data=json.dumps({"requests": requests}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    # Retry with long backoff for 429
    success = False
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                embeddings = data.get("embeddings", [])
                if len(embeddings) != len(batch):
                    raise ValueError(f"Expected {len(batch)} embeddings, got {len(embeddings)}")
                for c, emb in zip(batch, embeddings):
                    results[c["id"]] = emb["values"]
                success = True
                print(f"  Batch {batch_num} completed successfully ({len(results)}/{len(chunks)} total).")
                # Immediately save progress to disk
                out_path.write_text(json.dumps(results), encoding="utf-8")
                break
        except urllib.error.HTTPError as e:
            wait_time = 15 * (attempt + 1)
            print(f"  HTTP {e.code} ({e.reason}) on attempt {attempt + 1}. Backing off for {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            wait_time = 5 * (attempt + 1)
            print(f"  Error {e} on attempt {attempt + 1}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
    if not success:
        print(f"Could not complete batch {batch_num} after multiple retries. Halting.")
        break
        
    # Respect rate limit by sleeping 6s between requests
    print("  Sleeping 6s before next batch...")
    time.sleep(6)

print(f"\nFinal status: {len(results)}/{len(chunks)} embeddings saved to {out_path}.")
