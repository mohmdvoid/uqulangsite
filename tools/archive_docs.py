#!/usr/bin/env python3
"""
Snapshot the current documentation as a pinned version.

    python3 tools/archive_docs.py 0.1        # archive, then bump src/versions.json

Run this when a release is cut and the documentation is about to describe the
next one. It copies every current documentation source into
`src/pages/docs/<version>/`, so:

- `/docs/…` keeps serving the current release and its URLs never change
- `/docs/<version>/…` keeps serving what that release actually documented
- the archived pages are marked noindex and carry a banner pointing readers
  at the current version

The copy rewrites internal documentation links so an archived page links to
other archived pages rather than leaking back into the current version.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "src" / "pages"
VERSIONS = ROOT / "src" / "versions.json"

DOC_LINK_RE = re.compile(r'(\]\(|href=")(/(?:[a-z]{2}/)?docs/)')


def locale_dirs() -> list:
    """Every directory that holds documentation sources, per locale."""
    found = [PAGES / "docs"]
    for child in sorted(PAGES.iterdir()):
        if child.is_dir() and (child / "docs").is_dir() and child.name != "docs":
            found.append(child / "docs")
    return [d for d in found if d.is_dir()]


def archive(version: str, *, dry_run: bool = False) -> int:
    data = json.loads(VERSIONS.read_text(encoding="utf-8"))
    if any(entry["id"] == version and entry["status"] == "archived" for entry in data["versions"]):
        print(f"{version} is already archived", file=sys.stderr)
        return 1

    copied = 0
    for docs_dir in locale_dirs():
        target = docs_dir / version
        if target.exists():
            print(f"{target.relative_to(ROOT)} already exists — remove it first", file=sys.stderr)
            return 1

        sources = [p for p in sorted(docs_dir.rglob("*")) if p.is_file() and version not in p.parts]
        for source in sources:
            relative = source.relative_to(docs_dir)
            if relative.parts and relative.parts[0] in {v["id"] for v in data["versions"]}:
                continue

            destination = target / relative
            text = source.read_text(encoding="utf-8")
            # An archived page links to archived pages.
            text = DOC_LINK_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{version}/", text)

            print(f"  {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(text, encoding="utf-8")
            copied += 1

    if dry_run:
        print(f"\ndry run: {copied} file(s) would be copied")
        return 0

    for entry in data["versions"]:
        if entry["id"] == version:
            entry["status"] = "archived"
    if not any(entry["id"] == version for entry in data["versions"]):
        data["versions"].insert(0, {"id": version, "label": version, "status": "archived"})

    print(f"\n{copied} file(s) archived under version {version}")
    print(f"Now edit {VERSIONS.relative_to(ROOT)}: add the new current version, then run make build.")
    VERSIONS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0


def unarchive(version: str) -> int:
    """Undo an archive. Useful when a release is retracted, and for testing."""
    removed = 0
    for docs_dir in locale_dirs():
        target = docs_dir / version
        if target.exists():
            shutil.rmtree(target)
            removed += 1
            print(f"  removed {target.relative_to(ROOT)}")

    data = json.loads(VERSIONS.read_text(encoding="utf-8"))
    data["versions"] = [v for v in data["versions"] if not (v["id"] == version and v["status"] == "archived")]
    VERSIONS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{removed} directory(ies) removed, {VERSIONS.name} updated")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive the current documentation as a version")
    parser.add_argument("version", help="the version to pin, e.g. 0.1")
    parser.add_argument("--dry-run", action="store_true", help="list what would be copied")
    parser.add_argument("--undo", action="store_true", help="remove an archived version")
    args = parser.parse_args()

    if args.undo:
        return unarchive(args.version)
    return archive(args.version, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
