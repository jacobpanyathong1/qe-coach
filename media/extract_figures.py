"""Extract real figures from the QE source books.

Run with: python3 media/extract_figures.py
Writes PNGs into media/book_figures/ and a manifest figures_manifest.json
mapping each saved image to {book, kind, page, file}.

Two modes:
  - embedded : pull raster images embedded in the PDF (works for normal PDFs
               that carry figures as images: FMEA, SPC, GD&T, vision, physics).
  - page     : render whole pages to images (for scanned / image-only books
               like the APQP guide, whose every page IS a picture). Curated
               page numbers live in RENDER_PAGES once we've eyeballed them.
"""
import json
import sys
from pathlib import Path

import pymupdf  # PyMuPDF (a.k.a. fitz)

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "rag"))
from build_index import resolve_source, SOURCE_SPECS  # reuse the robust resolver

OUT_DIR = Path(__file__).parent / "book_figures"
MANIFEST = Path(__file__).parent / "figures_manifest.json"

MIN_W, MIN_H = 220, 220     # ignore icons, rules, tiny logos
MAX_PER_BOOK = 16
RENDER_DPI = 150

# Scanned/image-only books: render these specific 1-based pages instead of
# trying to pull embedded images. Filled in after inspecting probe output.
RENDER_PAGES = {
    # "advanced quality planning": [12, 18, 25, ...],
}


def slug(name):
    keep = "".join(c if c.isalnum() else "-" for c in name.lower())
    return "-".join(filter(None, keep.split("-")))[:40]


def avg_text_per_page(doc, sample=20):
    pages = min(len(doc), sample)
    if pages == 0:
        return 0
    total = sum(len(doc[i].get_text().strip()) for i in range(pages))
    return total / pages


def extract_embedded(doc, book, prefix, manifest):
    seen, saved = set(), 0
    for pno in range(len(doc)):
        if saved >= MAX_PER_BOOK:
            break
        for img in doc[pno].get_images(full=True):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.width < MIN_W or pix.height < MIN_H:
                    continue
                if pix.n - pix.alpha >= 4:           # CMYK -> RGB
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                out = OUT_DIR / f"{prefix}-p{pno + 1}-x{xref}.png"
                pix.save(out)
                manifest.append({"book": book, "kind": "embedded",
                                 "page": pno + 1, "file": str(out.relative_to(BASE))})
                saved += 1
                if saved >= MAX_PER_BOOK:
                    break
            except Exception as e:
                print(f"    ! xref {xref} p{pno+1}: {e}")
    return saved


def render_pages(doc, book, prefix, pages, manifest):
    saved = 0
    for pno in pages:
        if pno < 1 or pno > len(doc):
            continue
        pix = doc[pno - 1].get_pixmap(dpi=RENDER_DPI)
        out = OUT_DIR / f"{prefix}-page{pno}.png"
        pix.save(out)
        manifest.append({"book": book, "kind": "page",
                         "page": pno, "file": str(out.relative_to(BASE))})
        saved += 1
    return saved


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, substrings in SOURCE_SPECS:
        path = resolve_source(substrings)
        if path is None:
            print(f"SKIP (not found): {name}")
            continue
        doc = pymupdf.open(path)
        prefix = slug(name)
        atp = avg_text_per_page(doc)
        key = next((s for s in RENDER_PAGES if any(s in ss for ss in substrings)
                    or s in name.lower()), None)
        if key:
            n = render_pages(doc, name, prefix, RENDER_PAGES[key], manifest)
            print(f"{name}: rendered {n} curated pages  (avg text/pg ~{atp:.0f})")
        else:
            n = extract_embedded(doc, name, prefix, manifest)
            tag = "  <- looks SCANNED, may need RENDER_PAGES" if atp < 80 and n == 0 else ""
            print(f"{name}: {n} embedded figures  (avg text/pg ~{atp:.0f}){tag}")
        doc.close()

    MANIFEST.write_text(json.dumps(manifest, indent=1))
    print(f"\nWrote {len(manifest)} figures; manifest -> {MANIFEST.relative_to(BASE)}")


if __name__ == "__main__":
    main()
