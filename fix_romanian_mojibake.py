#!/usr/bin/env python3
"""Fix Romanian mojibake in parse_result.json and parse_result.txt."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fix_romanian_text(s: str) -> str:
    """Undo common corruption from mixed encodings / PDF extraction."""
    # ÔÇô / ÔÇØ triples (UTF-8 smart punctuation mis-decoded); fix before other steps
    s = s.replace("\u00d4\u00c7\u00f4", "\u2013")  # en dash
    s = s.replace("\u00d4\u00c7\u00d8", '"')  # mangled smart quotes -> ASCII
    # â from ├ó pattern (U+251C + U+00F3)
    s = s.replace("\u251c\u00f3", "\u00e2")
    # Ă / ă from box-drawing + vowel
    s = s.replace("\u2500\u00e9", "\u0102")
    s = s.replace("\u2500\u00e2", "\u0103")
    # Ș ș ț from U+255A + second byte
    s = s.replace("\u255a\xff", "\u0218")
    s = s.replace("\u255a\xd6", "\u0219")
    s = s.replace("\u255a\xf8", "\u021b")
    return s


def fix_json_structure(obj: object) -> object:
    if isinstance(obj, str):
        return fix_romanian_text(obj)
    if isinstance(obj, dict):
        return {k: fix_json_structure(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fix_json_structure(x) for x in obj]
    return obj


def main() -> None:
    root = Path(__file__).resolve().parent
    json_path = root / "parse_result.json"
    txt_path = root / "parse_result.txt"

    if json_path.is_file():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        fixed = fix_json_structure(data)
        json_path.write_text(
            json.dumps(fixed, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {json_path}")

    if txt_path.is_file():
        text = txt_path.read_text(encoding="utf-8")
        txt_path.write_text(fix_romanian_text(text), encoding="utf-8")
        print(f"Wrote {txt_path}")


if __name__ == "__main__":
    main()
