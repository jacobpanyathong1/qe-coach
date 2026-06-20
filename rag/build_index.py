"""One-time extraction of text chunks from the QE source books for /ask retrieval.

Run with: python3 rag/build_index.py
Produces rag/chunks.json: a list of {book, page, text} chunks.
"""
import json
import os
import re
from pathlib import Path

import pdfplumber

OUT_PATH = Path(__file__).parent / "chunks.json"
HOME = Path.home()

# Directories the source books are likely to live in (searched in order).
SEARCH_DIRS = [
    HOME / "Documents",
    HOME / "Documents" / "macOS",
    HOME / "Downloads",
    HOME / "Desktop",
]

# (display name, list of lowercase substrings that must ALL appear in the filename).
# Books are resolved by searching SEARCH_DIRS, so this survives files being moved.
SOURCE_SPECS = [
    ("GD&T Study Guide (Cogorno)", ["studyguidegdt"]),
    ("GM 7-Diamond Problem Solving Guide", ["quality_guide"]),
    ("Eines Vision Systems Training Course", ["eines_training_course"]),
    ("FMEA Handbook", ["failure mode", "fmea handbook"]),
    ("SPC Training Guide (Evans)", ["statistical process control", "spc"]),
    ("Advanced Quality Planning (AQP/APQP, Stamatis)", ["advanced quality planning"]),
    ("Giant Molecules: Materials Science (Carraher)", ["giant molecules"]),
    ("Teach Yourself Electricity and Electronics (Gibilisco)", ["teach yourself electricity"]),
]


def resolve_source(substrings):
    """Find the first PDF under SEARCH_DIRS whose name contains all substrings."""
    for d in SEARCH_DIRS:
        if not d.is_dir():
            continue
        for root, _dirs, files in os.walk(d):
            for fn in files:
                low = fn.lower()
                if low.endswith(".pdf") and all(s in low for s in substrings):
                    return Path(root) / fn
    return None


def build_sources():
    sources = []
    for name, substrings in SOURCE_SPECS:
        path = resolve_source(substrings)
        if path is None:
            print(f"SKIP (not found): {name} (looked for {substrings})")
            continue
        sources.append((name, str(path)))
    return sources

MAX_WORDS = 220
MIN_WORDS = 30


def chunk_page_text(text: str):
    """Split a page's text into ~MAX_WORDS chunks, breaking on blank lines where possible."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], []
    word_count = 0
    for p in paragraphs:
        words = p.split()
        if word_count + len(words) > MAX_WORDS and buf:
            chunks.append(" ".join(buf))
            buf, word_count = [], 0
        buf.append(p)
        word_count += len(words)
    if buf:
        chunks.append(" ".join(buf))
    return [c for c in chunks if len(c.split()) >= MIN_WORDS]


def main():
    all_chunks = []
    for name, path in build_sources():
        p = Path(path)
        if not p.exists():
            print(f"SKIP (not found): {name} -> {path}")
            continue
        print(f"Processing: {name} ({p.name})")
        try:
            with pdfplumber.open(p) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue
                    for chunk in chunk_page_text(text):
                        all_chunks.append({"book": name, "page": i, "text": chunk})
        except Exception as e:
            print(f"  ERROR processing {name}: {e}")
            continue
        print(f"  -> {sum(1 for c in all_chunks if c['book'] == name)} chunks")

    OUT_PATH.write_text(json.dumps(all_chunks, indent=1))
    print(f"\nWrote {len(all_chunks)} chunks to {OUT_PATH}")


if __name__ == "__main__":
    main()
