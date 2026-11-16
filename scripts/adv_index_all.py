import os
import json
import time
import pymupdf
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types

load_dotenv()

PDF_PATH = "data/20260319_VNM_Bao_cao_thuong_nien_2025_eae619d5f6.pdf"
IMG_DIR = "data/advanced/page_images"
VIS_CACHE = "data/advanced/visual_descriptions.json"
CHUNKS_PATH = "data/advanced/chunks.json"
EMB_PATH = "data/advanced/chunk_embeddings.json"
os.makedirs("data/advanced", exist_ok=True)

client = OpenAI()
gclient = genai.Client()

def extract_visual_descriptions():
    if os.path.exists(VIS_CACHE):
        cache = json.load(open(VIS_CACHE, encoding="utf-8"))
    else:
        cache = {}

    img_files = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".png")])
    for fname in img_files:
        page_num = int(fname.replace("page_", "").replace(".png", ""))
        key = str(page_num)
        if key in cache and len(cache[key].get("description", "")) > 400 and "Xin lỗi" not in cache[key]["description"]:
            continue

        img_path = os.path.join(IMG_DIR, fname)
        with open(img_path, "rb") as f:
            img_bytes = f.read()

        prompt = (
            "Bạn là chuyên gia phân tích tài liệu tài chính và báo cáo thường niên. "
            "Hãy trích xuất CHÍNH XÁC toàn bộ thông tin trực quan có trên trang báo cáo Vinamilk 2025 này bằng tiếng Việt:\n"
            "1. Nếu có BẢNG BIỂU: Trình bày lại rõ từng dòng, từng cột (dạng bảng Markdown), đơn vị tính (tỷ đồng, %, cổ phiếu...) và số liệu chính xác.\n"
            "2. Nếu có BIỂU ĐỒ (cột, tròn, đường): Ghi rõ tên biểu đồ, trục X/Y, chú giải (legend), đơn vị và TẤT CẢ các giá trị số liệu trên từng cột/điểm/phần trăm.\n"
            "3. Nếu có SƠ ĐỒ TỔ CHỨC / CẤU TRÚC / ẢNH THÔNG TIN: Mô tả rõ các cấp bậc, mối quan hệ, tỷ lệ sở hữu, tên đơn vị hoặc thông tin chữ trong hình.\n"
            "Chỉ trích xuất những gì nhìn thấy rõ ràng, tuyệt đối không suy đoán hay bịa số."
        )
        for attempt in range(3):
            try:
                resp = gclient.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                        prompt,
                    ],
                )
                desc = (resp.text or "").strip()
                cache[key] = {
                    "page": page_num,
                    "image_path": img_path.replace("\\", "/"),
                    "description": desc,
                }
                with open(VIS_CACHE, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
                print(f"Gemini Vision extracted page {page_num} ({len(desc)} chars)")
                time.sleep(0.5)
                break
            except Exception as e:
                print(f"Error on page {page_num} attempt {attempt+1}: {e}")
                time.sleep(3)
    return cache

def chunk_text(text, max_chars=900, overlap=150):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            # try break at period or space
            bp = text.rfind(". ", start + max_chars // 2, end)
            if bp == -1:
                bp = text.rfind(" ", start + max_chars // 2, end)
            if bp != -1:
                end = bp + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks

def infer_section(page_num):
    if page_num <= 5:
        return "mo_dau"
    elif page_num <= 24:
        return "thong_tin_chung"
    elif page_num <= 62:
        return "bao_cao_ban_dieu_hanh"
    elif page_num <= 99:
        return "quan_tri_cong_ty"
    elif page_num <= 105:
        return "phat_trien_ben_vung"
    else:
        return "bao_cao_tai_chinh"

def build_chunks(vis_cache):
    doc = pymupdf.open(PDF_PATH)
    all_chunks = []
    empty_pages = []
    for i, page in enumerate(doc):
        p = i + 1
        sec = infer_section(p)
        raw_txt = page.get_text("text").strip()
        if not raw_txt:
            empty_pages.append(p)
        else:
            sub_chunks = chunk_text(raw_txt, max_chars=900, overlap=150)
            for idx, st in enumerate(sub_chunks):
                all_chunks.append({
                    "id": f"vnm2025_p{p:03d}_txt_{idx}",
                    "source_id": "vnm-ar-2025",
                    "source": PDF_PATH,
                    "page": p,
                    "type": "text",
                    "text": st,
                    "metadata": {
                        "section": sec,
                        "modality": "text",
                        "page": p,
                    }
                })
        if str(p) in vis_cache:
            v = vis_cache[str(p)]
            v_chunks = chunk_text(v["description"], max_chars=2800, overlap=200)
            for idx, vt in enumerate(v_chunks):
                all_chunks.append({
                    "id": f"vnm2025_p{p:03d}_vis_{idx}",
                    "source_id": "vnm-ar-2025",
                    "source": PDF_PATH,
                    "page": p,
                    "type": "visual",
                    "image_path": v["image_path"],
                    "text": f"[Trích xuất Trực quan / Bảng / Biểu đồ - Trang {p}] {vt}",
                    "metadata": {
                        "section": sec,
                        "modality": "visual_table_chart",
                        "image_path": v["image_path"],
                        "page": p,
                    }
                })

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"Built {len(all_chunks)} chunks across {len(doc)} pages. Empty text pages: {empty_pages}")
    return all_chunks

def build_embeddings(chunks):
    if os.path.exists(EMB_PATH):
        existing = json.load(open(EMB_PATH, encoding="utf-8"))
    else:
        existing = {}

    todo = [c for c in chunks if c["id"] not in existing]
    if not todo:
        print("Embeddings already complete:", len(existing))
        return

    batch_size = 80
    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        texts = [c["text"] for c in batch]
        resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
        for c, item in zip(batch, resp.data):
            existing[c["id"]] = item.embedding
        print(f"Embedded {min(i + batch_size, len(todo))}/{len(todo)} new chunks")
    # prune old ids not in current chunks
    valid_ids = {c["id"] for c in chunks}
    existing = {k: v for k, v in existing.items() if k in valid_ids}
    with open(EMB_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f)
    print("Saved embeddings to", EMB_PATH, "total:", len(existing))

if __name__ == "__main__":
    vis = extract_visual_descriptions()
    chunks = build_chunks(vis)
    build_embeddings(chunks)
