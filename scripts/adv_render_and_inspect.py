import os
import fitz

PDF_PATH = "data/20260319_VNM_Bao_cao_thuong_nien_2025_eae619d5f6.pdf"
OUT_DIR = "data/advanced/page_images"
os.makedirs(OUT_DIR, exist_ok=True)

doc = fitz.open(PDF_PATH)
print("Opened PDF, total pages:", len(doc))

# Render key visual, chart, diagram, and table pages (1-indexed)
key_pages = [
    7, 8, 11, 12, 13, 14, 15, 21, 24,
    26, 27, 38, 39, 40, 41, 42, 47, 52,
    64, 72, 101, 102, 103, 104, 106, 107, 108, 109, 110
]

for p in key_pages:
    page = doc[p - 1]
    pix = page.get_pixmap(dpi=130)
    out_path = os.path.join(OUT_DIR, f"page_{p:03d}.png")
    pix.save(out_path)
    print(f"Saved {out_path} ({pix.width}x{pix.height})")
