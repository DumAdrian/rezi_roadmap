#!/usr/bin/env python3
"""
Parse rezidentiat tematica PDF: books, CAP chapters, subchapters,
book page ranges (from 'p.X-Y' in the bibliography) and PDF page numbers.

Output map shape (see --json):
  books: {
    "book_1" | "book_2" | "book_3": {
      "book_id": int,
      "chapters": [
        {
          "type": "chapter",
          "cap_number": int,
          "title": str,
          "book_page_span": [start, end] | null,   # pages in the cited textbook
          "book_page_count": int | null,           # inclusive span length
          "pdf_pages": [int],                      # PDF page(s) where the CAP line appears
          "tematica_pdf_page_span": [lo, hi] | null,
          "tematica_pdf_page_count": int | null,  # span in this tematica PDF (header + subs)
          "subchapters": [ { ... same fields for each subchapter ... }, ... ]
        },
        ...
      ]
    },
    ...
  }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Install dependencies: pip install -r requirements.txt", file=sys.stderr)
    raise


def extract_lines_per_pdf_page(doc: fitz.Document) -> list[tuple[int, str]]:
    """Return (1-based pdf_page, line) preserving order."""
    out: list[tuple[int, str]] = []
    for i in range(doc.page_count):
        text = doc.load_page(i).get_text("text") or ""
        for raw in text.splitlines():
            line = raw.strip()
            if line:
                out.append((i + 1, line))
    return out


def normalize_continuations_wp(
    lines_with_pages: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Join broken lines; each tuple is (pdf_page_of_first_segment, merged_line)."""
    merged: list[tuple[int, str]] = []
    buf = ""
    buf_page: int | None = None

    def flush() -> None:
        nonlocal buf, buf_page
        if buf.strip() and buf_page is not None:
            merged.append((buf_page, buf.strip()))
        buf = ""
        buf_page = None

    for pno, line in lines_with_pages:
        s = line.strip()
        if not s:
            flush()
            continue

        # Standalone page index lines from the PDF layout (e.g. "4" before the next section)
        if re.fullmatch(r"\d{1,2}", s) and len(s) <= 2:
            flush()
            continue

        if buf and buf_page is not None:
            if re.search(r"p\.\s*\d+\s*-\s*$", buf, re.I) and re.fullmatch(r"\d+", s):
                buf = buf.rstrip() + s
                continue
            if not re.match(
                r"^(CAP\.|\d+\.\s|[oO]\s|--\s)", s
            ) and not s.startswith("De asemenea"):
                if buf.startswith("De asemenea"):
                    flush()
                    buf = s
                    buf_page = pno
                    continue
                buf = buf.rstrip() + " " + s
                continue

        flush()
        buf = s
        buf_page = pno

    flush()
    return merged


# Known book blocks in this tematica (extend if PDF changes)
BOOK_START_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (1, re.compile(r"^1\.\s+Adam\s+Feather", re.I)),
    (2, re.compile(r"^2\.\s+Peter\s+F", re.I)),
    (3, re.compile(r"^3\.\s+Latha\s+Ganti", re.I)),
]


def find_book_for_line(
    line_index: int, book_start_indices: list[tuple[int, int]]
) -> int | None:
    """Return book id for the line at line_index (last book marker at or before index)."""
    current: int | None = None
    for li, bid in book_start_indices:
        if li <= line_index:
            current = bid
        else:
            break
    return current


def parse_page_span_from_suffix(s: str) -> tuple[int, int] | None:
    """
    Extract first book page span from tail like ' - p.172-190' or ' - p.317'.
    Returns (start, end) inclusive in book page numbers.
    """
    m = re.search(
        r"[-–]\s*p\.\s*(\d+)\s*(?:[-–]\s*(\d+))?",
        s,
        re.I,
    )
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    lo, hi = (a, b) if a <= b else (b, a)
    return lo, hi


def page_count(span: tuple[int, int] | None) -> int | None:
    if span is None:
        return None
    return span[1] - span[0] + 1


SUBCHAPTER_RE = re.compile(
    r"^(?:(?P<num>\d+)\.|(?P<bullet>[oO]))\s+(?P<title>.+?)\s*[-–]\s*p\.\s*(?P<a>\d+)(?:\s*[-–]\s*(?P<b>\d+))?",
    re.I,
)

CAP_RE = re.compile(
    r"^CAP\.\s*(?P<num>\d+)\s*[\.–\-]\s*(?P<title>.+?)\s*$",
    re.I,
)


def build_structure(
    lines_with_pages: list[tuple[int, str]],
) -> dict[str, Any]:
    lines_wp = normalize_continuations_wp(lines_with_pages)
    lines = [ln for _, ln in lines_wp]
    line_pdf_pages = [p for p, _ in lines_wp]

    book_start_indices: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        for bid, pat in BOOK_START_PATTERNS:
            if pat.match(line):
                book_start_indices.append((i, bid))
                break
    book_start_indices.sort(key=lambda x: x[0])

    books_map: dict[str, Any] = {}
    for bid, _ in BOOK_START_PATTERNS:
        books_map[f"book_{bid}"] = {
            "book_id": bid,
            "chapters": [],
        }

    current_chapter: dict[str, Any] | None = None

    for i, line in enumerate(lines):
        if line.startswith("--"):
            continue
        if line.startswith("De asemenea"):
            current_chapter = None
            continue

        if any(pat.match(line) for _, pat in BOOK_START_PATTERNS):
            current_chapter = None
            continue

        cap_m = CAP_RE.match(line)
        if cap_m:
            bid = find_book_for_line(i, book_start_indices)
            if bid is None:
                bid = 1

            title = cap_m.group("title").strip()
            span = parse_page_span_from_suffix(line)
            ch = {
                "type": "chapter",
                "cap_number": int(cap_m.group("num")),
                "title": title,
                "book_page_span": list(span) if span else None,
                "book_page_count": page_count(span),
                "pdf_pages": None,
                "subchapters": [],
            }
            ch["pdf_pages"] = [line_pdf_pages[i]]

            books_map[f"book_{bid}"]["chapters"].append(ch)
            current_chapter = ch
            continue

        sub_m = SUBCHAPTER_RE.match(line)
        if sub_m and current_chapter is not None:
            title = sub_m.group("title").strip()
            a = int(sub_m.group("a"))
            b = int(sub_m.group("b")) if sub_m.group("b") else a
            lo, hi = (a, b) if a <= b else (b, a)
            span = (lo, hi)
            sub = {
                "type": "subchapter",
                "number": sub_m.group("num"),
                "bullet": bool(sub_m.group("bullet")),
                "title": title,
                "book_page_span": [lo, hi],
                "book_page_count": page_count(span),
                "pdf_pages": [],
            }
            sub["pdf_pages"] = [line_pdf_pages[i]]
            current_chapter["subchapters"].append(sub)
            continue

    # Fill chapter book_page_count from subchapters if missing
    for bk in books_map.values():
        for ch in bk["chapters"]:
            if ch["book_page_count"] is None and ch["subchapters"]:
                spans = [
                    tuple(sc["book_page_span"])  # type: ignore[arg-type]
                    for sc in ch["subchapters"]
                    if sc.get("book_page_span")
                ]
                if spans:
                    lo = min(s[0] for s in spans)
                    hi = max(s[1] for s in spans)
                    ch["book_page_span"] = [lo, hi]
                    ch["book_page_count"] = page_count((lo, hi))

            pdf_pages: set[int] = set()
            for p in ch.get("pdf_pages") or []:
                pdf_pages.add(p)
            for sc in ch["subchapters"]:
                for p in sc.get("pdf_pages") or []:
                    pdf_pages.add(p)
            if pdf_pages:
                lo, hi = min(pdf_pages), max(pdf_pages)
                ch["tematica_pdf_page_span"] = [lo, hi]
                ch["tematica_pdf_page_count"] = hi - lo + 1
            else:
                ch["tematica_pdf_page_span"] = None
                ch["tematica_pdf_page_count"] = None
            for sc in ch["subchapters"]:
                pp = sc.get("pdf_pages") or []
                if pp:
                    lo = hi = pp[0]
                    sc["tematica_pdf_page_span"] = [lo, hi]
                    sc["tematica_pdf_page_count"] = 1
                else:
                    sc["tematica_pdf_page_span"] = None
                    sc["tematica_pdf_page_count"] = None

    return {"books": books_map, "source_line_count": len(lines)}


def print_structure(data: dict[str, Any]) -> None:
    books: dict[str, Any] = data["books"]
    for key in sorted(books.keys(), key=lambda k: int(k.split("_")[1])):
        bk = books[key]
        print(f"\n=== {key} (id={bk['book_id']}) ===")
        for ch in bk["chapters"]:
            cap = ch["cap_number"]
            bp = ch.get("book_page_count")
            span = ch.get("book_page_span")
            print(
                f"  CAP.{cap} | {ch['title'][:70]}{'...' if len(ch['title']) > 70 else ''}"
            )
            print(
                f"    book_pages={span} count={bp} "
                f"tematica_pdf={ch.get('tematica_pdf_page_span')} "
                f"tematica_count={ch.get('tematica_pdf_page_count')}"
            )
            for sc in ch["subchapters"]:
                label = sc["number"] or ("o" if sc["bullet"] else "?")
                t = sc["title"]
                if len(t) > 65:
                    t = t[:65] + "..."
                print(
                    f"    [{label}] {t}  book_pages={sc['book_page_span']} "
                    f"count={sc['book_page_count']} "
                    f"tematica_pdf={sc.get('tematica_pdf_page_span')} "
                    f"tematica_count={sc.get('tematica_pdf_page_count')}"
                )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pdf",
        nargs="?",
        default="rezidentiat-M-2026.pdf",
        type=Path,
        help="Path to tematica PDF",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of human-readable tree",
    )
    args = parser.parse_args()
    path = args.pdf
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(path)
    try:
        lines_wp = extract_lines_per_pdf_page(doc)
        data = build_structure(lines_wp)
    finally:
        doc.close()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_structure(data)


if __name__ == "__main__":
    main()
