#!/usr/bin/env python3
"""
Prepare a deployment directory: minify, precompress, and enforce a budget.

    python3 tools/postprocess.py                 # build dist/
    python3 tools/postprocess.py --budget-only   # measure, write nothing

The repository holds readable generated HTML — that is what makes a diff
reviewable. What a CDN should serve is the same HTML with the inter-tag
whitespace removed and a .gz and .br sitting next to every text file, so the
edge never compresses anything at request time.

Both are produced here, into dist/, leaving the tracked files alone.

Nothing in this step may change what a page means. The minifier does not touch
the contents of pre, code, textarea, script or style, and it never removes a
space that separates two pieces of text.
"""
from __future__ import annotations

import argparse
import gzip
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import brotli  # optional; the .br files are skipped without it
except ImportError:
    brotli = None

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

# What a deployment contains. Everything else — sources, tooling, the local
# environment — stays out of the served directory.
EXCLUDE_DIRS = {
    ".git", ".github", ".venv", ".claude", "src", "tools", "deploy", "dist",
    "node_modules", "__pycache__",
}
EXCLUDE_FILES = {
    "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
    "PLACEHOLDERS.md", "LICENSE.md", "Makefile", "requirements.txt",
    "netlify.toml", "vercel.json", ".gitignore", ".editorconfig",
}

COMPRESSIBLE = {".html", ".css", ".js", ".json", ".xml", ".svg", ".txt", ".webmanifest"}

# Budget, in bytes over the wire, for the heaviest page. A static site that
# cannot meet this has gone wrong somewhere.
BUDGET = {
    "html_gzip": 16 * 1024,
    "css_gzip": 24 * 1024,
    "js_gzip": 32 * 1024,
    "page_total_gzip": 64 * 1024,
}

# Regions whose whitespace is content, not formatting.
PROTECTED_RE = re.compile(
    r"(<(?P<tag>pre|code|textarea|script|style)\b[^>]*>.*?</(?P=tag)>)",
    re.DOTALL | re.IGNORECASE,
)
COMMENT_RE = re.compile(r"<!--(?!\[if).*?-->", re.DOTALL)
BETWEEN_TAGS_RE = re.compile(r">\s{2,}<")
LEADING_RE = re.compile(r"^[ \t]+", re.MULTILINE)
BLANK_RE = re.compile(r"\n{2,}")


@dataclass
class Report:
    files: int = 0
    raw: int = 0
    minified: int = 0
    gzipped: int = 0
    brotlied: int = 0
    problems: list = field(default_factory=list)


def minify_html(source: str) -> str:
    """Collapse formatting whitespace, keeping every protected region intact."""
    blocks: list = []

    def stash(match: "re.Match[str]") -> str:
        blocks.append(match.group(0))
        return f"\x00{len(blocks) - 1}\x00"

    out = PROTECTED_RE.sub(stash, source)
    out = COMMENT_RE.sub("", out)
    # Only runs of two or more spaces between tags: a single space between two
    # inline elements can be meaningful, so it stays.
    out = BETWEEN_TAGS_RE.sub("><", out)
    out = LEADING_RE.sub("", out)
    out = BLANK_RE.sub("\n", out)
    out = re.sub(r"\x00(\d+)\x00", lambda m: blocks[int(m.group(1))], out)
    return out.strip() + "\n"


def deployable(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDE_DIRS for part in relative.parts):
        return False
    if relative.name in EXCLUDE_FILES:
        return False
    if relative.name.startswith(".") and relative.parts[0] != ".well-known":
        return False
    return True


def compress(target: Path, data: bytes, report: Report) -> None:
    gz = gzip.compress(data, compresslevel=9, mtime=0)
    if len(gz) < len(data):
        target.with_suffix(target.suffix + ".gz").write_bytes(gz)
        report.gzipped += len(gz)

    if brotli is not None:
        br = brotli.compress(data, quality=11)
        if len(br) < len(data):
            target.with_suffix(target.suffix + ".br").write_bytes(br)
            report.brotlied += len(br)


def build_dist() -> Report:
    report = Report()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not deployable(path):
            continue

        relative = path.relative_to(ROOT)
        target = DIST / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        raw = path.read_bytes()
        report.files += 1
        report.raw += len(raw)

        if path.suffix == ".html":
            text = minify_html(raw.decode("utf-8"))
            data = text.encode("utf-8")
            if not verify_minification(raw.decode("utf-8"), text):
                report.problems.append(f"{relative}: minification changed the page's text")
        else:
            data = raw

        target.write_bytes(data)
        report.minified += len(data)

        if path.suffix in COMPRESSIBLE:
            compress(target, data, report)

    return report


def verify_minification(before: str, after: str) -> bool:
    """The visible text must be identical. Anything else is a bug in the minifier."""
    def words(markup: str) -> list:
        protected = PROTECTED_RE.findall(markup)
        body = PROTECTED_RE.sub(" \x00 ", markup)
        body = re.sub(r"<[^>]+>", " ", body)
        return body.split() + ["".join(block[0] for block in protected).split().__len__().__str__()]

    return words(before) == words(after)


def measure_budget(report: Report) -> None:
    """The heaviest page, as a browser would actually fetch it."""
    css = sorted(DIST.glob("assets/css/*.css.gz"))
    js = sorted((DIST / "assets/js").rglob("*.js.gz"))
    css_size = sum(p.stat().st_size for p in css)
    js_size = sum(p.stat().st_size for p in js)

    pages = sorted(DIST.rglob("*.html.gz"))
    if not pages:
        report.problems.append("no compressed pages found")
        return

    heaviest = max(pages, key=lambda p: p.stat().st_size)
    html_size = heaviest.stat().st_size
    total = html_size + css_size + js_size

    checks = [
        ("html_gzip", html_size, f"heaviest page {heaviest.relative_to(DIST)}"),
        ("css_gzip", css_size, "stylesheet"),
        ("js_gzip", js_size, "all JavaScript modules"),
        ("page_total_gzip", total, "heaviest page plus every asset it loads"),
    ]

    print("\n  budget (gzipped, over the wire)")
    for key, value, label in checks:
        limit = BUDGET[key]
        status = "ok " if value <= limit else "OVER"
        print(f"    {status} {value / 1024:7.1f} KB / {limit / 1024:5.0f} KB   {label}")
        if value > limit:
            report.problems.append(f"budget exceeded: {label} is {value} bytes, limit {limit}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare dist/ for deployment")
    parser.add_argument("--budget-only", action="store_true", help="measure without writing dist/")
    args = parser.parse_args()

    if args.budget_only and not DIST.exists():
        print("dist/ does not exist — run without --budget-only first", file=sys.stderr)
        return 1

    report = build_dist() if not args.budget_only else Report()

    if not args.budget_only:
        saved = report.raw - report.minified
        print(f"dist/  {report.files} files")
        print(f"  raw        {report.raw / 1024:8.1f} KB")
        print(f"  minified   {report.minified / 1024:8.1f} KB  (-{saved / 1024:.1f} KB)")
        print(f"  gzip       {report.gzipped / 1024:8.1f} KB")
        if brotli is not None:
            print(f"  brotli     {report.brotlied / 1024:8.1f} KB")
        else:
            print("  brotli     not installed — .br files skipped (pip install brotli)")

    measure_budget(report)

    if report.problems:
        print("\nproblems:", file=sys.stderr)
        for problem in report.problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print("\nready to deploy: dist/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
