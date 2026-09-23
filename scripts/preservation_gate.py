#!/usr/bin/env python3
"""Repository-level preservation gate.

Compares the current tree with a Git base ref and fails on deleted files or
removed top-level classes/functions in modified Python files. It does not
forbid additive refactors or new files.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def symbols(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    raw = git("diff", "--name-status", f"{base}...HEAD")
    failures: list[str] = []
    checked = 0

    for line in raw.splitlines():
        if not line:
            continue
        status, *parts = line.split("\t")
        path = parts[-1]
        if status == "D":
            failures.append(f"DELETED_FILE:{path}")
            continue
        if not path.endswith(".py"):
            continue
        if status not in {"M", "R", "C"}:
            continue

        checked += 1
        try:
            before = git("show", f"{base}:{path}")
        except subprocess.CalledProcessError:
            continue
        current_path = Path(path)
        if not current_path.exists():
            failures.append(f"MISSING_CURRENT_FILE:{path}")
            continue
        after = current_path.read_text(encoding="utf-8")

        try:
            removed = sorted(symbols(before) - symbols(after))
        except SyntaxError as exc:
            failures.append(f"SYNTAX_ERROR:{path}:{exc}")
            continue

        if removed:
            failures.append(f"REMOVED_SYMBOLS:{path}:{','.join(removed)}")

    print(f"PRESERVATION_FILES_CHECKED={checked}")
    if failures:
        print("PRESERVATION_FAILURES:")
        for failure in failures:
            print(failure)
        return 1

    print("PRESERVATION_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
