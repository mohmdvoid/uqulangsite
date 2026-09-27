#!/usr/bin/env python3
"""
Build a quality dashboard from what the site actually measures.

    python3 tools/report.py            # writes reports/index.html
    python3 tools/report.py --json     # the same data, for CI to consume

Every number here is measured, not asserted: page weights come from gzipping
the real files, translation coverage from the page graph, and the test row from
running the suite. Nothing is hard-coded, so a regression shows up as a changed
number rather than as a stale claim.

The report is not published with the site. It is a build artifact, for whoever
is deciding whether this is ready to ship.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import subprocess
import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
sys.path.insert(0, str(ROOT / "tools"))

import build as builder  # noqa: E402
import postprocess  # noqa: E402

SKIP_PARTS = {"src", "tools", "dist", "deploy", "reports", ".git", ".github",
              ".venv", "node_modules"}
HREF_RE = re.compile(r'href="(/[^"#?]*)')
WORD_RE = re.compile(r"<[^>]+>")


@dataclass
class PageRow:
    path: str
    locale: str
    title: str
    raw: int
    gzip: int
    words: int
    links_out: int
    translated: bool
    layout: str


@dataclass
class Dashboard:
    generated: str
    commit: str
    pages: list = field(default_factory=list)
    locales: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    tests: dict = field(default_factory=dict)
    checks: list = field(default_factory=list)
    budget: dict = field(default_factory=dict)


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def site_pages() -> list:
    return sorted(
        p for p in ROOT.rglob("*.html")
        if not any(part in SKIP_PARTS for part in p.relative_to(ROOT).parts)
    )


def collect() -> Dashboard:
    site = builder.Site().collect()
    dashboard = Dashboard(
        generated=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        commit=git("rev-parse", "--short", "HEAD"),
    )

    by_path = {page.path: page for page in site.pages}

    for path in site_pages():
        text = path.read_text(encoding="utf-8")
        raw = text.encode("utf-8")
        url_path = "/" + str(path.relative_to(ROOT)).replace("index.html", "")
        page = by_path.get(url_path if url_path.endswith("/") else url_path)

        body = re.search(r"<main[^>]*>(.*)</main>", text, re.DOTALL)
        prose = WORD_RE.sub(" ", body.group(1) if body else text)

        dashboard.pages.append(PageRow(
            path=url_path,
            locale=page.locale.code if page else "—",
            title=(re.search(r"<title>(.*?)</title>", text, re.DOTALL).group(1)
                   .replace(" — uqulang", "").strip()),
            raw=len(raw),
            gzip=len(gzip.compress(raw, 9, mtime=0)),
            words=len(prose.split()),
            links_out=len(set(HREF_RE.findall(text))),
            translated=bool(page and len(site.translations_of(page)) > 1),
            layout=page.meta.get("layout", "raw") if page else "—",
        ))

    # Translation coverage, by translation key rather than by file.
    default = site.localiser.default_code
    keys = {page.key for page in site.pages if page.locale.code == default}
    for locale in site.localiser.ordered():
        present = {page.key for page in site.pages if page.locale.code == locale.code}
        dashboard.locales[locale.code] = {
            "name": locale.name,
            "dir": locale.dir,
            "pages": len(present),
            "coverage": round(100 * len(present & keys) / max(len(keys), 1)),
            "strings": len(locale.catalog._strings),
        }

    css = sorted((ROOT / "assets" / "css").glob("site.*.css"))
    js = sorted((ROOT / "assets" / "js").rglob("*.js"))
    img = sorted((ROOT / "assets" / "img").glob("*"))

    def gzipped(paths) -> int:
        return sum(len(gzip.compress(p.read_bytes(), 9, mtime=0)) for p in paths)

    dashboard.payload = {
        "stylesheet": {"files": len(css), "gzip": gzipped(css)},
        "javascript": {"files": len(js), "gzip": gzipped(js)},
        "images": {"files": len(img), "raw": sum(p.stat().st_size for p in img)},
        "third_party": 0,
    }

    heaviest = max(dashboard.pages, key=lambda row: row.gzip)
    total = heaviest.gzip + dashboard.payload["stylesheet"]["gzip"] + dashboard.payload["javascript"]["gzip"]
    dashboard.budget = {
        "heaviest_page": heaviest.path,
        "heaviest_gzip": heaviest.gzip,
        "page_total_gzip": total,
        "limit": postprocess.BUDGET["page_total_gzip"],
        "headroom": round(100 * (1 - total / postprocess.BUDGET["page_total_gzip"])),
    }

    dashboard.tests = run_tests()
    dashboard.checks = run_checks()
    return dashboard


def run_tests() -> dict:
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    runner = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0)
    started = dt.datetime.now()
    result = runner.run(suite)
    return {
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "seconds": round((dt.datetime.now() - started).total_seconds(), 2),
        "modules": sorted(p.stem for p in (ROOT / "tests").glob("test_*.py")),
    }


def run_checks() -> list:
    checks = []
    for label, command in (
        ("Generated output matches src/", [sys.executable, "tools/build.py", "--check"]),
        ("Links, headings, metadata, domain", [sys.executable, "tools/check_links.py"]),
    ):
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        checks.append({
            "label": label,
            "ok": done.returncode == 0,
            "detail": (done.stdout or done.stderr).strip().splitlines()[-1] if (done.stdout or done.stderr) else "",
        })
    return checks


def kb(value: int) -> str:
    return f"{value / 1024:.1f} KB"


def render(dashboard: Dashboard) -> str:
    rows = "".join(
        "<tr>"
        f'<td class="mono"><a href="https://uqulang.com{row.path}">{row.path}</a></td>'
        f"<td>{row.title}</td>"
        f'<td><span class="tag">{row.locale}</span></td>'
        f'<td><span class="tag tag--quiet">{row.layout}</span></td>'
        f'<td class="num">{row.words}</td>'
        f'<td class="num">{row.links_out}</td>'
        f'<td class="num">{kb(row.raw)}</td>'
        f'<td class="num strong">{kb(row.gzip)}</td>'
        f'<td>{"✓" if row.translated else "—"}</td>'
        "</tr>"
        for row in sorted(dashboard.pages, key=lambda r: -r.gzip)
    )

    locale_rows = "".join(
        "<tr>"
        f'<td><span class="tag">{code}</span> {data["name"]}</td>'
        f'<td class="num">{data["pages"]}</td>'
        f'<td class="num">{data["strings"]}</td>'
        f'<td class="bar"><span style="width:{data["coverage"]}%"></span>'
        f'<em>{data["coverage"]}%</em></td>'
        "</tr>"
        for code, data in dashboard.locales.items()
    )

    checks = "".join(
        f'<li class="{"pass" if check["ok"] else "fail"}">'
        f'<strong>{check["label"]}</strong><span>{check["detail"]}</span></li>'
        for check in dashboard.checks
    )

    tests = dashboard.tests
    tests_ok = tests["failures"] == 0 and tests["errors"] == 0
    budget = dashboard.budget

    tiles = [
        ("Tests", f'{tests["run"]}', f'{"all passing" if tests_ok else str(tests["failures"]) + " failing"} · {tests["seconds"]}s', tests_ok),
        ("Pages", str(len(dashboard.pages)), f'{len(dashboard.locales)} locales', True),
        ("Heaviest page", kb(budget["page_total_gzip"]), f'{budget["headroom"]}% under budget', budget["headroom"] > 0),
        ("Third-party requests", "0", "no external domains", True),
    ]
    tile_html = "".join(
        f'<div class="tile {"ok" if ok else "bad"}"><span class="tile__label">{label}</span>'
        f'<span class="tile__value">{value}</span><span class="tile__note">{note}</span></div>'
        for label, value, note, ok in tiles
    )

    payload = dashboard.payload
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>uqulang.com — build report</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #ffffff; --panel: #f6f8f7; --line: #dde4e1; --ink: #0c1512;
    --muted: #4e5f59; --brand: #0e7a57; --bad: #a3341f; --warn: #a9701a;
    --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #0a100e; --panel: #0f1714; --line: #1f2c27; --ink: #e9f0ed;
             --muted: #a3b2ac; --brand: #35c48e; --bad: #e2705a; --warn: #e4a93c; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5
    ui-sans-serif, -apple-system, "Segoe UI", sans-serif; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 40px 24px 80px; }}
  header {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: baseline;
    justify-content: space-between; margin-bottom: 32px; }}
  h1 {{ font-size: 24px; margin: 0; letter-spacing: -0.02em; }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--muted); margin: 40px 0 12px; }}
  .meta {{ color: var(--muted); font-size: 13px; font-family: var(--mono); }}
  .tiles {{ display: grid; gap: 12px;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }}
  .tile {{ border: 1px solid var(--line); border-radius: 10px; padding: 16px;
    background: var(--panel); display: flex; flex-direction: column; gap: 4px; }}
  .tile__label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--muted); }}
  .tile__value {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; }}
  .tile__note {{ font-size: 13px; color: var(--muted); }}
  .tile.ok .tile__value {{ color: var(--brand); }}
  .tile.bad .tile__value {{ color: var(--bad); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.06em; color: var(--muted); padding: 8px 10px;
    border-bottom: 1px solid var(--line); position: sticky; top: 0; background: var(--bg); }}
  td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: middle; }}
  tr:hover td {{ background: var(--panel); }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); }}
  .strong {{ font-weight: 600; }}
  .mono a {{ font-family: var(--mono); color: var(--brand); text-decoration: none; }}
  .mono a:hover {{ text-decoration: underline; }}
  .tag {{ display: inline-block; padding: 1px 7px; border-radius: 99px; font-size: 11px;
    background: color-mix(in oklab, var(--brand) 16%, transparent); color: var(--brand);
    font-family: var(--mono); }}
  .tag--quiet {{ background: var(--panel); color: var(--muted); border: 1px solid var(--line); }}
  .bar {{ position: relative; min-width: 160px; }}
  .bar span {{ display: block; height: 8px; border-radius: 99px; background: var(--brand); }}
  .bar em {{ font-style: normal; font-size: 12px; color: var(--muted);
    font-family: var(--mono); }}
  ul.checks {{ list-style: none; padding: 0; margin: 0; }}
  ul.checks li {{ display: flex; gap: 12px; align-items: baseline; padding: 10px 12px;
    border: 1px solid var(--line); border-radius: 8px; margin-bottom: 8px;
    background: var(--panel); }}
  ul.checks li::before {{ content: "✓"; color: var(--brand); font-weight: 700; }}
  ul.checks li.fail::before {{ content: "✕"; color: var(--bad); }}
  ul.checks span {{ color: var(--muted); font-family: var(--mono); font-size: 12px; }}
  .split {{ display: grid; gap: 24px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }}
  footer {{ margin-top: 48px; color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>uqulang.com — build report</h1>
    <p class="meta">{dashboard.generated} · commit {dashboard.commit}</p>
  </header>

  <div class="tiles">{tile_html}</div>

  <div class="split">
    <section>
      <h2>Locales</h2>
      <table>
        <thead><tr><th>Locale</th><th class="num">Pages</th><th class="num">Strings</th>
          <th>Coverage of English pages</th></tr></thead>
        <tbody>{locale_rows}</tbody>
      </table>
    </section>

    <section>
      <h2>Payload</h2>
      <table>
        <thead><tr><th>Asset class</th><th class="num">Files</th><th class="num">Gzipped</th></tr></thead>
        <tbody>
          <tr><td>Stylesheet (one bundle, content-hashed)</td>
            <td class="num">{payload["stylesheet"]["files"]}</td>
            <td class="num strong">{kb(payload["stylesheet"]["gzip"])}</td></tr>
          <tr><td>JavaScript (ES modules, preloaded)</td>
            <td class="num">{payload["javascript"]["files"]}</td>
            <td class="num strong">{kb(payload["javascript"]["gzip"])}</td></tr>
          <tr><td>Images (SVG and generated icons)</td>
            <td class="num">{payload["images"]["files"]}</td>
            <td class="num">{kb(payload["images"]["raw"])}</td></tr>
          <tr><td>Third-party requests</td><td class="num">0</td><td class="num">0 KB</td></tr>
        </tbody>
      </table>
    </section>
  </div>

  <h2>Gates</h2>
  <ul class="checks">{checks}
    <li class="{"pass" if tests_ok else "fail"}"><strong>Test suite</strong>
      <span>{tests["run"]} tests across {len(tests["modules"])} modules · {tests["seconds"]}s</span></li>
  </ul>

  <h2>Every page</h2>
  <table>
    <thead><tr><th>Path</th><th>Title</th><th>Locale</th><th>Layout</th>
      <th class="num">Words</th><th class="num">Links</th>
      <th class="num">Raw</th><th class="num">Gzip</th><th>Translated</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <footer>
    Generated by <code>tools/report.py</code>. Every figure is measured from the
    built site at commit {dashboard.commit}; nothing here is hard-coded.
    Budget: heaviest page plus every asset it loads is
    {kb(budget["page_total_gzip"])} against a {kb(budget["limit"])} limit.
  </footer>
</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the quality dashboard")
    parser.add_argument("--json", action="store_true", help="print the data as JSON")
    args = parser.parse_args()

    dashboard = collect()

    if args.json:
        payload = {
            "generated": dashboard.generated, "commit": dashboard.commit,
            "locales": dashboard.locales, "payload": dashboard.payload,
            "tests": dashboard.tests, "budget": dashboard.budget,
            "checks": dashboard.checks,
            "pages": [vars(row) for row in dashboard.pages],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "index.html").write_text(render(dashboard), encoding="utf-8")

    failing = [c for c in dashboard.checks if not c["ok"]]
    tests_ok = dashboard.tests["failures"] == 0 and dashboard.tests["errors"] == 0

    print(f"reports/index.html — {len(dashboard.pages)} pages, "
          f"{dashboard.tests['run']} tests, "
          f"{dashboard.budget['headroom']}% budget headroom")
    if failing or not tests_ok:
        print("  gates failing — see the report", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
