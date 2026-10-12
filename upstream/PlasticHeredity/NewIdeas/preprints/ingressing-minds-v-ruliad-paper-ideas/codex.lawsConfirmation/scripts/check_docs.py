#!/usr/bin/env python3
"""Fail when a local Markdown link in this workspace has no target."""

from __future__ import annotations

from pathlib import Path
import re


LINK = re.compile(r"\[[^]]*\]\(([^)]+)\)")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    broken: list[tuple[Path, str]] = []
    checked = 0
    for document in sorted(root.rglob("*.md")):
        text = document.read_text(encoding="utf-8")
        for raw_target in LINK.findall(text):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            path = Path(target)
            resolved = path if path.is_absolute() else document.parent / path
            checked += 1
            if not resolved.exists():
                broken.append((document.relative_to(root), raw_target))
    for document, target in broken:
        print(f"BROKEN {document}: {target}")
    print(f"checked {checked} local Markdown links; broken {len(broken)}")
    return int(bool(broken))


if __name__ == "__main__":
    raise SystemExit(main())
