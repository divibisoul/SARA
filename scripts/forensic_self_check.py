#!/usr/bin/env python3
"""Forensic static gate for SARA source.

This is deliberately conservative: it does not execute arbitrary application code.
It detects unfinished markers, unsafe suppression patterns and documents explicit
infrastructure gates without treating them as failures.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "src", ROOT / "tests", ROOT / "scripts")
TEXT_SUFFIXES = {".py", ".toml", ".yml", ".yaml", ".md"}

UNFINISHED = re.compile(r"\b(?:TODO|FIXME|XXX)\b")
UNSAFE = re.compile(r"#\s*type:\s*ignore\b|\bcontinue-on-error\s*:\s*true\b")


def main() -> int:
    findings: list[dict[str, str | int]] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            findings.append({"kind": "missing_scan_root", "path": str(root)})
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                findings.append({"kind": "undecodable_text", "path": str(path)})
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if UNFINISHED.search(line):
                    findings.append({"kind": "unfinished_marker", "path": str(path.relative_to(ROOT)), "line": line_no})
                if UNSAFE.search(line):
                    findings.append({"kind": "unsafe_suppression", "path": str(path.relative_to(ROOT)), "line": line_no})

    if findings:
        print("FORENSIC_SELF_CHECK=FAIL")
        for finding in findings:
            print(f" - {finding}")
        return 1

    print("FORENSIC_SELF_CHECK=PASS")
    print("unfinished_markers=0")
    print("unsafe_suppressions=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
