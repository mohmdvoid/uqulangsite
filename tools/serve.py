#!/usr/bin/env python3
"""
Development server.

`python3 -m http.server` is not usable for this site: it sends no
Cache-Control, so browsers apply heuristic caching to the HTML. After a change
to an asset filename — the stylesheet carries a content hash — a stale page can
keep asking for a file that no longer exists and render with no styling at all,
which looks like the site is broken when it is not.

This server sends `Cache-Control: no-store` for everything, serves `404.html`
for unknown paths the way the production host does, and logs 404s so a broken
link is visible rather than silent.

    python3 tools/serve.py [--port 4173]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DevHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        # Nothing is cached in development. Production caching lives in _headers.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        """Serve the real 404 page, as the production host does."""
        if code == 404:
            page = ROOT / "404.html"
            if page.exists():
                body = page.read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args) -> None:
        status = str(args[1]) if len(args) > 1 else ""
        if status.startswith(("4", "5")):
            sys.stderr.write(f"  {status}  {args[0]}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the built site for development")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()

    handler = functools.partial(DevHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", args.port), handler) as server:
        print(f"http://localhost:{args.port}  (no-store; 4xx and 5xx logged below)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
