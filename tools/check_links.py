#!/usr/bin/env python3
"""
Link and markup checker for the generated site.

Run it after `build.py`, and in CI. It catches the failures that actually reach
visitors on a static site: a href pointing at a file that was never generated,
a fragment pointing at an id that does not exist, a duplicate id, an image
without alt text, a page without a title or meta description.

    python3 tools/check_links.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"src", "tools", ".git", ".claude", "node_modules"}

HREF_RE = re.compile(r'(?:href|src)="([^"]+)"')
ID_RE = re.compile(r'\bid="([^"]+)"')
IMG_RE = re.compile(r"<img\b(?![^>]*\balt=)[^>]*>", re.IGNORECASE)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>", re.IGNORECASE)
MACRO_RE = re.compile(r"\{\{[^}\n]{1,60}\}\}")
# Any absolute link back to this site must use the canonical domain. A stale
# one is invisible in the browser and only shows up in structured data,
# install commands and share cards.
STALE_DOMAIN_RE = re.compile(r"https?://(?!uqulang\.com|get\.uqulang\.com|portal\.uqulang\.com|support\.uqulang\.com)[\w.-]*uqulang\.[\w.]+")
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"')


def html_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.html")
        if not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)
    )


def resolve(target: str) -> Path | None:
    """Map a site-absolute URL path to the file that should serve it."""
    clean = target.split("?")[0].split("#")[0]
    if not clean or not clean.startswith("/"):
        return None
    candidate = ROOT / clean.lstrip("/")
    if clean.endswith("/"):
        return candidate / "index.html"
    return candidate


def main() -> int:
    files = html_files()
    if not files:
        print("no HTML found — run tools/build.py first")
        return 1

    ids_by_page: dict[str, set[str]] = {}
    problems: list[str] = []

    for path in files:
        rel = "/" + str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")

        ids = ID_RE.findall(text)
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            problems.append(f"{rel}: duplicate id(s) {sorted(duplicates)}")
        ids_by_page[rel] = set(ids)

        if not TITLE_RE.search(text):
            problems.append(f"{rel}: missing <title>")
        description = DESC_RE.search(text)
        if not description or len(description.group(1)) < 50:
            problems.append(f"{rel}: missing or too-short meta description")
        for tag in IMG_RE.findall(text):
            problems.append(f"{rel}: <img> without alt — {tag[:70]}")
        if 'lang="' not in text.split("\n")[1]:
            problems.append(f"{rel}: <html> without a lang attribute")

        # Exactly one h1, and no skipped levels — the outline screen readers
        # and search engines actually consume.
        levels = [int(level) for level in HEADING_RE.findall(text)]
        h1_count = levels.count(1)
        if h1_count != 1:
            problems.append(f"{rel}: expected exactly one <h1>, found {h1_count}")

        previous = None
        for level in levels:
            if previous is not None and level > previous + 1:
                problems.append(f"{rel}: heading jumps from h{previous} to h{level}")
                break
            previous = level

        for macro in MACRO_RE.findall(text):
            problems.append(f"{rel}: unresolved template macro {macro}")

        for stale in set(STALE_DOMAIN_RE.findall(text)):
            problems.append(f"{rel}: non-canonical uqulang domain {stale}")

    # Second pass: every internal link must resolve to a file, every fragment to an id.
    for path in files:
        rel = "/" + str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")

        for target in HREF_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "data:", "tel:")):
                continue

            if target.startswith("#"):
                if target[1:] and target[1:] not in ids_by_page[rel]:
                    problems.append(f"{rel}: fragment {target} has no matching id")
                continue

            destination = resolve(target)
            if destination is None:
                problems.append(f"{rel}: relative link {target!r} — use site-absolute paths")
                continue
            if not destination.exists():
                problems.append(f"{rel}: broken link {target} -> {destination.relative_to(ROOT)}")
                continue

            if "#" in target and destination.suffix == ".html":
                fragment = target.split("#", 1)[1]
                dest_rel = "/" + str(destination.relative_to(ROOT))
                dest_ids = ids_by_page.get(dest_rel)
                if dest_ids is not None and fragment and fragment not in dest_ids:
                    problems.append(f"{rel}: {target} — no id {fragment!r} on that page")

    by_kind: dict[str, int] = defaultdict(int)
    for problem in problems:
        by_kind[problem.split(": ", 1)[1].split(" ")[0]] += 1

    if problems:
        print(f"{len(problems)} problem(s) in {len(files)} page(s):\n")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"ok — {len(files)} pages, no broken links, no duplicate ids, no missing metadata")
    return 0


if __name__ == "__main__":
    sys.exit(main())
