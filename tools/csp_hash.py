#!/usr/bin/env python3
"""
Print the CSP hash for the one inline <script> in the built pages.

The site has exactly one inline script: the theme guard in <head> that runs
before first paint. Everything else is an external module. Hashing it keeps the
Content-Security-Policy free of 'unsafe-inline'.

    python3 tools/csp_hash.py        # paste the output into _headers
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INLINE_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL)


def main() -> int:
    page = ROOT / "index.html"
    if not page.exists():
        print("index.html not found — run tools/build.py first", file=sys.stderr)
        return 1

    scripts = INLINE_RE.findall(page.read_text(encoding="utf-8"))
    if not scripts:
        print("no inline <script> found; remove the hash from _headers", file=sys.stderr)
        return 1

    for body in scripts:
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        print(f"'sha256-{base64.b64encode(digest).decode('ascii')}'")

    if len(scripts) > 1:
        print(f"\n{len(scripts)} inline scripts found — all hashes are listed above.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
