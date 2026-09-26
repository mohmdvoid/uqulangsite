#!/usr/bin/env python3
"""
uqulang.org static site generator.

Deliberately small: Python standard library only, no dependencies, no cache, no
watch mode. It exists for one reason — the header, footer, navigation, sitemap
and search index must never drift out of sync across pages.

    python3 tools/build.py            # write the site
    python3 tools/build.py --check    # verify output is up to date (CI)

The generated *.html files are the deployable artifact. Commit them; a deploy
never needs Python.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover - environment problem, not a code path
    raise SystemExit(
        "The Markdown package is required to build.\n"
        "  make setup          (creates .venv and installs it)\n"
        "  pip install -r requirements.txt"
    )

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PAGES = SRC / "pages"
CSS_SRC = SRC / "css"
CSS_OUT = ROOT / "assets" / "css"

# Concatenation order matters: tokens define the custom properties everything
# else reads, and utilities come last so they can override a component.
CSS_LAYERS = [
    "tokens.css",
    "base.css",
    "layout.css",
    "components.css",
    "docs.css",
    "utilities.css",
]

# The ES modules the entry point pulls in. Preloading them turns a three-round-
# trip import waterfall into one parallel fetch.
JS_MODULES = [
    "core/App.js",
    "core/Component.js",
    "core/EventBus.js",
    "core/Store.js",
    "components/ThemeToggle.js",
    "components/NavDrawer.js",
    "components/TabGroup.js",
    "components/CodeBlock.js",
    "components/PlatformDetector.js",
    "components/TableOfContents.js",
    "components/HeadingAnchors.js",
    "components/DocsSearch.js",
    "lang/Highlighter.js",
    "lang/grammars.js",
]

# --- Site configuration ---------------------------------------------------
# BASE is the path the site is served from. "" means the domain root
# (https://uqulang.org/). Set it to "/uqulang" to deploy under a sub-path.
SITE_URL = "https://uqulang.com"
BASE = ""

# Commercial product: licensed to universities and research institutions.
# These four constants are the only places these destinations are written down.
PORTAL_URL = "https://portal.uqulang.com"          # licence portal + downloads
SUPPORT_URL = "https://support.uqulang.com"        # ticketed support for licensees
CONTACT_URL = "/universities/#contact"             # request a campus licence
CONTACT_EMAIL = "universities@uqulang.com"

BUILD_DATE = dt.date.today().isoformat()

NAV_EN = [
    ("docs", "Documentation", "/docs/"),
    ("install", "Install", "/install/"),
    ("universities", "For universities", "/universities/"),
    ("blog", "Blog", "/blog/"),
]

NAV_AR = [
    ("docs", "التوثيق", "/docs/"),
    ("install", "التثبيت", "/install/"),
    ("universities", "للجامعات", "/universities/"),
    ("blog", "المدونة", "/blog/"),
]

FOOTER_EN = [
    ("Learn", [
        ("Getting started", "/docs/getting-started/"),
        ("Language tour", "/docs/tour/"),
        ("Compiler CLI", "/docs/cli/"),
        ("All documentation", "/docs/"),
    ]),
    ("Product", [
        ("Install", "/install/"),
        ("Release notes", "/blog/"),
        ("Roadmap", "/universities/#roadmap"),
        ("What is included", "/universities/#included"),
    ]),
    ("Institutions", [
        ("Campus licensing", "/universities/"),
        ("Request a licence", "/universities/#contact"),
        ("Licence portal", PORTAL_URL),
        ("Support", SUPPORT_URL),
    ]),
]

FOOTER_AR = [
    ("تعلّم", [
        ("البداية السريعة", "/docs/getting-started/"),
        ("جولة في اللغة", "/docs/tour/"),
        ("أداة المترجم", "/docs/cli/"),
        ("كل التوثيق", "/docs/"),
    ]),
    ("المنتج", [
        ("التثبيت", "/install/"),
        ("ملاحظات الإصدار", "/blog/"),
        ("خطة الطريق", "/universities/#roadmap"),
        ("ما الذي يشمله الترخيص", "/universities/#included"),
    ]),
    ("للمؤسسات", [
        ("تراخيص الجامعات", "/universities/"),
        ("اطلب ترخيصاً", "/universities/#contact"),
        ("بوابة التراخيص", PORTAL_URL),
        ("الدعم الفني", SUPPORT_URL),
    ]),
]

STRINGS = {
    "en": {
        "dir": "ltr",
        "og_locale": "en",
        "skip_label": "Skip to content",
        "nav_label": "Main",
        "menu_label": "Open menu",
        "home_label": "home",
        "home_suffix": "",
        "footer_about": (
            "<p>A compiled systems language for teaching and research, licensed to "
            "universities and research institutions.</p>"
            "<p class=\"footer-etymology\"><span lang=\"ar\" dir=\"rtl\">عقل</span> "
            "<span class=\"footer-etymology__gloss\">ʿaql — the reasoning mind</span></p>"
        ),
        "footer_legal": f"© {dt.date.today().year} uqulang. All rights reserved. Use of the compiler and toolchain is governed by your institution’s licence agreement.",
        "footer_made": "صُنع في السعودية · Made in Saudi Arabia",
    },
    "ar": {
        "dir": "rtl",
        "og_locale": "ar",
        "skip_label": "تجاوز إلى المحتوى",
        "nav_label": "الرئيسية",
        "menu_label": "فتح القائمة",
        "home_label": "الصفحة الرئيسية",
        "home_suffix": "ar/",
        "footer_about": (
            "<p>لغة برمجة مترجَمة للأنظمة، مخصّصة للتعليم والبحث، ومرخّصة للجامعات "
            "والمؤسسات البحثية.</p>"
            "<p class=\"footer-etymology\"><span lang=\"ar\" dir=\"rtl\">عقل</span> "
            "<span class=\"footer-etymology__gloss\">أصل التسمية</span></p>"
        ),
        "footer_legal": f"© {dt.date.today().year} uqulang. جميع الحقوق محفوظة. يخضع استخدام المترجم والأدوات لاتفاقية الترخيص الخاصة بمؤسستك.",
        "footer_made": "صُنع في السعودية",
    },
}

# Docs sidebar: one tree, rendered on every docs page with the current entry
# marked. Add a page here and it appears everywhere it should.
DOCS_TREE = [
    ("Start here", [
        ("Overview", "/docs/"),
        ("Getting started", "/docs/getting-started/"),
        ("Install uqulang", "/install/"),
    ]),
    ("Language", [
        ("Language tour", "/docs/tour/"),
    ]),
    ("Tooling", [
        ("Compiler CLI", "/docs/cli/"),
    ]),
]

CODE_RE = re.compile(
    r"<!--code(?P<attrs>[^>]*?)-->\n(?P<code>.*?)\n<!--/code-->", re.DOTALL
)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')

COPY_ICONS = (
    '<svg class="code-copy__icon code-copy__icon--idle" viewBox="0 0 16 16" fill="none" '
    'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
    '<rect x="5.5" y="5.5" width="8" height="9" rx="1.5"/>'
    '<path d="M10.5 3.5h-6a1.5 1.5 0 0 0-1.5 1.5v6"/></svg>'
    '<svg class="code-copy__icon code-copy__icon--done" viewBox="0 0 16 16" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M3 8.5l3.5 3.5L13 5"/></svg>'
)

# --- Hijri dates ----------------------------------------------------------
# Tabular (Kuwaiti) algorithm: the standard civil approximation. It can differ
# from the Umm al-Qura calendar by a day, so dates are checked before a post
# is published — see PLACEHOLDERS.md.
HIJRI_MONTHS_EN = [
    "Muharram", "Safar", "Rabiʿ al-Awwal", "Rabiʿ al-Thani",
    "Jumada al-Ula", "Jumada al-Akhira", "Rajab", "Shaʿban",
    "Ramadan", "Shawwal", "Dhu al-Qaʿda", "Dhu al-Hijja",
]
HIJRI_MONTHS_AR = [
    "محرم", "صفر", "ربيع الأول", "ربيع الآخر",
    "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان",
    "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
]
HIJRI_RE = re.compile(r"\{\{hijri:(\d{4})-(\d{2})-(\d{2})\}\}")


def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def to_hijri(year: int, month: int, day: int) -> "tuple[int, int, int]":
    """Gregorian date -> (hijri year, month 1-12, day)."""
    jdn = gregorian_to_jdn(year, month, day)
    l = jdn - 1948440 + 10632
    n = (l - 1) // 10631
    l = l - 10631 * n + 354
    j = ((10985 - l) // 5316) * ((50 * l) // 17719) + (l // 5670) * ((43 * l) // 15238)
    l = l - ((30 - j) // 15) * ((17719 * j) // 50) - (j // 16) * ((15238 * j) // 43) + 29
    m = (24 * l) // 709
    d = l - (709 * m) // 24
    return 30 * n + j - 30, m, d


def format_hijri(year: int, month: int, day: int, lang: str) -> str:
    hy, hm, hd = to_hijri(year, month, day)
    if lang == "ar":
        return f"{hd} {HIJRI_MONTHS_AR[hm - 1]} {hy}هـ"
    return f"{hd} {HIJRI_MONTHS_EN[hm - 1]} {hy} AH"


META_RE = re.compile(r"^\s*<!--meta\s*(?P<json>\{.*?\})\s*meta-->\s*", re.DOTALL)
FRONT_MATTER_RE = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)
FENCE_RE = re.compile(
    r"^```(?P<lang>[\w-]*)(?P<attrs>[^\n]*)\n(?P<code>.*?)\n```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
ADMONITION_RE = re.compile(
    r"(?:^> \[!(?P<kind>NOTE|WARNING|TIP)\][ \t]*\n(?P<body>(?:^>.*\n?)*))",
    re.MULTILINE,
)
TABLE_RE = re.compile(r"(<table>.*?</table>)", re.DOTALL)
TOKEN = "\u27e6BLOCK{}\u27e7"
TOKEN_P_RE = re.compile(r"<p>\s*\u27e6BLOCK(\d+)\u27e7\s*</p>")

ADMONITION_ICONS = {
    "NOTE": ('callout--note', '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.4"/>'),
    "TIP": ('callout--note', '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.4"/>'),
    "WARNING": ('callout--warn', '<path d="M12 4.5 21 19.5H3z"/><path d="M12 10v4M12 16.8v.2"/>'),
}
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass
class Page:
    source: Path
    meta: dict
    body: str
    outputs: dict = field(default_factory=dict)

    @property
    def path(self) -> str:
        return self.meta["path"]

    @property
    def lang(self) -> str:
        return self.meta.get("lang", "en")

    @property
    def out_file(self) -> Path:
        path = self.path
        if path == "/":
            return ROOT / "index.html"
        if path.endswith(".html"):
            return ROOT / path.lstrip("/")
        return ROOT / path.strip("/") / "index.html"


def expand_code_blocks(body: str, lang: str = "en") -> str:
    """Turn `<!--code file="…" lang="…"--> … <!--/code-->` into a code figure.

    The author writes raw source; escaping happens here, once, correctly.
    """
    copy_label = "نسخ" if lang == "ar" else "Copy"
    copy_aria = "نسخ الشيفرة" if lang == "ar" else "Copy code to clipboard"

    def replace(match: "re.Match[str]") -> str:
        attrs = dict(ATTR_RE.findall(match.group("attrs")))
        code = html.escape(match.group("code"))
        name = attrs.get("file", "")
        syntax = attrs.get("lang", "text")

        head = ""
        if name or attrs.get("copy") != "false":
            actions = ""
            if attrs.get("copy") != "false":
                actions = (
                    '<div class="code-block__actions">'
                    f'<button class="code-copy" type="button" data-code-copy aria-label="{copy_aria}">'
                    f'{COPY_ICONS}<span data-code-copy-label>{copy_label}</span></button></div>'
                )
            label = f'<span class="code-block__name">{html.escape(name)}</span>' if name else ""
            head = f'<div class="code-block__head">{label}{actions}</div>'

        return (
            f'<div class="code-block" data-code data-lang="{syntax}">'
            f"{head}"
            f'<pre tabindex="0"><code>{code}</code></pre>'
            "</div>"
        )

    return CODE_RE.sub(replace, body)


def url(path: str) -> str:
    """Resolve an internal path against BASE. External URLs pass through."""
    if path.startswith(("http://", "https://", "#", "mailto:")):
        return path
    return f"{BASE}{path}"


def build_stylesheet(*, check: bool, changed: list) -> str:
    """Concatenate the CSS layers into one fingerprinted file.

    One request instead of six, and a content hash in the name so the file can
    be served immutable — a repeat visitor never revalidates it, and a deploy
    is picked up instantly because the name changes.
    """
    parts = []
    for name in CSS_LAYERS:
        path = CSS_SRC / name
        if not path.exists():
            raise SystemExit(f"missing stylesheet layer: {path}")
        parts.append(f"/* {name} */\n{path.read_text(encoding='utf-8').strip()}\n")

    bundle = (
        "/* uqulang.com — generated by tools/build.py from src/css/. "
        "Do not edit this file. */\n\n" + "\n".join(parts)
    )
    digest = hashlib.sha256(bundle.encode("utf-8")).hexdigest()[:10]
    filename = f"site.{digest}.css"

    CSS_OUT.mkdir(parents=True, exist_ok=True)
    write(CSS_OUT / filename, bundle, check=check, changed=changed)

    # Drop superseded bundles so the deploy directory holds exactly one.
    for stale in CSS_OUT.glob("site.*.css"):
        if stale.name != filename:
            changed.append(f"removed {stale.relative_to(ROOT)}")
            if not check:
                stale.unlink()

    return f"{BASE}/assets/css/{filename}"


def parse_front_matter(text: str, source: Path) -> "tuple[dict, str]":
    """YAML-shaped `key: value` front matter, without a YAML dependency.

    Values are parsed as JSON when they look like it (so `true`, numbers and
    `{"en": "/"}` work), and treated as plain strings otherwise. That covers
    every field this site uses and keeps the build to one dependency.
    """
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise SystemExit(f"{source}: missing `---` front matter block")

    meta: dict = {}
    for number, line in enumerate(match.group("body").splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise SystemExit(f"{source}:{number}: expected `key: value`, got {line!r}")
        key, _, raw = line.partition(":")
        raw = raw.strip()
        try:
            meta[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            meta[key.strip()] = raw.strip("\"'")
    return meta, text[match.end():]


def render_markdown(body: str, source: Path) -> str:
    """Markdown to the HTML this site's stylesheet expects.

    Fenced code and admonitions are lifted out first so the author writes plain
    Markdown while the output still carries the copy button, the syntax spans
    and the callout markup. Raw HTML passes through untouched, so a page can
    still drop into a card grid or a definition list where prose is not enough.
    """
    blocks: list = []

    def stash(html_fragment: str) -> str:
        blocks.append(html_fragment)
        return TOKEN.format(len(blocks) - 1)

    def take_fence(match: "re.Match[str]") -> str:
        lang = match.group("lang") or "text"
        attrs = dict(ATTR_RE.findall(match.group("attrs") or ""))
        fence = f'<!--code lang="{lang}"'
        if attrs.get("file"):
            fence += f' file="{attrs["file"]}"'
        if attrs.get("copy") == "false":
            fence += ' copy="false"'
        return "\n" + stash(expand_code_blocks(f"{fence}-->\n{match.group('code')}\n<!--/code-->")) + "\n"

    def take_admonition(match: "re.Match[str]") -> str:
        kind = match.group("kind")
        inner = "\n".join(
            line[2:] if line.startswith("> ") else line[1:]
            for line in match.group("body").splitlines()
        )
        modifier, icon = ADMONITION_ICONS[kind]
        rendered = render_markdown(inner, source)
        return "\n" + stash(
            f'<div class="callout {modifier}">'
            f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" aria-hidden="true">{icon}</svg>'
            f'<div class="callout__body">{rendered}</div></div>'
        ) + "\n"

    body = FENCE_RE.sub(take_fence, body)
    body = ADMONITION_RE.sub(take_admonition, body)

    converter = markdown.Markdown(
        extensions=["tables", "attr_list", "toc", "sane_lists", "md_in_html"],
        extension_configs={"toc": {"permalink": False}},
        output_format="html5",
    )
    html_out = converter.convert(body)

    # Tables need the horizontal-scroll wrapper to survive a phone screen.
    html_out = TABLE_RE.sub(r'<div class="table-wrap">\1</div>', html_out)

    # Put the stashed blocks back, unwrapping the paragraph Markdown added.
    html_out = TOKEN_P_RE.sub(lambda m: blocks[int(m.group(1))], html_out)
    for index, block in enumerate(blocks):
        html_out = html_out.replace(TOKEN.format(index), block)

    # Authors write ordinary site paths; BASE is applied for sub-path deploys.
    if BASE:
        html_out = re.sub(r'href="(/[^"]*)"', lambda m: f'href="{BASE}{m.group(1)}"', html_out)
    return html_out


def apply_layout(page: "Page", content: str) -> str:
    """Wrap converted Markdown in the page furniture its layout implies."""
    layout = page.meta.get("layout", "raw")
    if layout == "raw":
        return content
    if layout == "post":
        layout = "page"

    meta = page.meta
    header = []
    if meta.get("eyebrow"):
        header.append(f'<span class="docs-header__eyebrow">{html.escape(meta["eyebrow"])}</span>')
    header.append(f'<h1>{meta.get("heading", meta["title"])}</h1>')
    if meta.get("lead"):
        header.append(f'<p class="docs-header__lead">{meta["lead"]}</p>')
    if meta.get("meta_line"):
        header.append(f'<p class="docs-header__meta">{meta["meta_line"]}</p>')
    header_html = '<header class="docs-header">' + "".join(header) + "</header>"

    crumbs = ""
    if meta.get("breadcrumb"):
        items = "".join(
            f'<li><a href="{url(path)}">{html.escape(label)}</a></li>'
            for label, path in meta["breadcrumb"]
        )
        current = meta.get("breadcrumb_current", meta["title"])
        crumbs = f'<ol class="breadcrumb">{items}<li>{html.escape(current)}</li></ol>'

    nav = ""
    previous, following = meta.get("prev"), meta.get("next")
    if previous or following:
        links = []
        if previous:
            links.append(
                f'<a class="page-nav__link" href="{url(previous["path"])}">'
                f'<span class="page-nav__dir">Previous</span>'
                f'<span class="page-nav__title">{html.escape(previous["title"])}</span></a>'
            )
        if following:
            links.append(
                f'<a class="page-nav__link page-nav__link--next" href="{url(following["path"])}">'
                f'<span class="page-nav__dir">Next</span>'
                f'<span class="page-nav__title">{html.escape(following["title"])}</span></a>'
            )
        nav = f'<nav class="page-nav" aria-label="Pagination">{"".join(links)}</nav>'

    if layout == "docs":
        return (
            '<div class="container container--docs docs">{{docs_aside}}<div class="docs-main">'
            f'{crumbs}{header_html}'
            f'<article class="docs-article" data-heading-anchors>{content}</article>'
            f'{nav}</div>{{{{docs_toc}}}}</div>'
        )

    return (
        f'<div class="container container--narrow page-head">{crumbs}{header_html}</div>'
        f'<div class="container container--narrow" data-heading-anchors>'
        f'<section class="docs-article prose-wide">{content}</section>{nav}</div>'
    )


def read_pages() -> list[Page]:
    """Collect every page source.

    Two authoring formats, one pipeline: Markdown with `---` front matter for
    prose (documentation, blog posts), and HTML with a `<!--meta … -->` block
    for the layout-heavy marketing pages. Markdown is converted here, so
    everything downstream sees HTML.
    """
    pages: list[Page] = []

    for source in sorted(PAGES.rglob("*.md")):
        meta, body = parse_front_matter(source.read_text(encoding="utf-8"), source)
        require_meta(meta, source)
        meta.setdefault("layout", "docs")
        page = Page(source=source, meta=meta, body="")
        page.body = apply_layout(page, render_markdown(body, source))
        pages.append(page)

    for source in sorted(PAGES.rglob("*.page.html")):
        raw = source.read_text(encoding="utf-8")
        match = META_RE.match(raw)
        if not match:
            raise SystemExit(f"{source}: missing <!--meta … meta--> block")
        try:
            meta = json.loads(match.group("json"))
        except json.JSONDecodeError as error:
            raise SystemExit(f"{source}: invalid meta JSON — {error}") from error
        require_meta(meta, source)
        pages.append(Page(source=source, meta=meta, body=raw[match.end():]))

    paths = [page.path for page in pages]
    duplicates = {path for path in paths if paths.count(path) > 1}
    if duplicates:
        raise SystemExit(f"two sources claim the same path: {sorted(duplicates)}")

    return sorted(pages, key=lambda page: page.path)


def require_meta(meta: dict, source: Path) -> None:
    for required in ("title", "description", "path"):
        if required not in meta:
            raise SystemExit(f"{source}: front matter is missing '{required}'")
    if len(str(meta["description"])) < 50:
        raise SystemExit(f"{source}: description is shorter than 50 characters")


def render_nav(lang: str, current: str | None) -> str:
    items = NAV_AR if lang == "ar" else NAV_EN
    out = []
    for key, label, path in items:
        aria = ' aria-current="page"' if key == current else ""
        out.append(f'<a class="site-nav__link" href="{url(path)}"{aria}>{label}</a>')
    return "\n      ".join(out)


def render_footer_groups(lang: str) -> str:
    groups = FOOTER_AR if lang == "ar" else FOOTER_EN
    blocks = []
    for title, links in groups:
        items = "\n          ".join(
            f'<li><a href="{url(path)}">{label}</a></li>' for label, path in links
        )
        blocks.append(
            '<div class="footer-group">\n'
            f'        <h2 class="footer-group__title">{title}</h2>\n'
            f'        <ul class="footer-group__list">\n          {items}\n        </ul>\n'
            "      </div>"
        )
    return "\n      ".join(blocks)


def render_docs_sidebar(current_path: str) -> str:
    groups = []
    for title, links in DOCS_TREE:
        items = []
        for label, path in links:
            aria = ' aria-current="page"' if path == current_path else ""
            items.append(
                f'<li><a class="docs-nav__link" href="{url(path)}"{aria}>{label}</a></li>'
            )
        joined = "\n            ".join(items)
        groups.append(
            '<li class="docs-nav__group">\n'
            f'          <span class="docs-nav__group-title">{title}</span>\n'
            f'          <ul class="docs-nav__sub">\n            {joined}\n          </ul>\n'
            "        </li>"
        )
    return "\n        ".join(groups)


def render_docs_aside(current_path: str) -> str:
    """Sidebar + search, identical on every docs page."""
    return f"""<aside class="docs-sidebar">
      <details class="docs-sidebar__disclosure" open>
        <summary>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
          Documentation
        </summary>
        <div class="docs-search" data-search="{url('/search-index.json')}">
          <svg class="docs-search__icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>
          <label class="visually-hidden" for="docs-search-input">Search the documentation</label>
          <input class="docs-search__input" id="docs-search-input" type="search" placeholder="Search docs…" autocomplete="off" spellcheck="false" data-search-input>
          <ul class="docs-search__results" aria-label="Search results" data-search-results></ul>
          <p class="visually-hidden" role="status" data-search-status></p>
        </div>
        <h2 class="docs-sidebar__title">Documentation</h2>
        <ul class="docs-nav">
        {render_docs_sidebar(current_path)}
        </ul>
      </details>
    </aside>"""


DOCS_TOC = """<aside class="docs-toc" data-toc=".docs-article">
      <h2 class="docs-toc__title">On this page</h2>
      <ul class="docs-toc__list" data-toc-list></ul>
    </aside>"""


def alternates(page: Page) -> str:
    """hreflang pairs for the pages that exist in both languages."""
    pairs = page.meta.get("alternates")
    if not pairs:
        return ""
    lines = [
        f'<link rel="alternate" hreflang="{lang}" href="{SITE_URL}{url(path)}">'
        for lang, path in pairs.items()
    ]
    lines.append(
        f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}{url(pairs.get("en", "/"))}">'
    )
    return "\n".join(lines)


def render(page: Page, layout: str, *, stylesheet: str, theme_init: str, pages: "list[Page]") -> str:
    lang = page.lang
    strings = STRINGS[lang]
    title = page.meta["title"]
    full_title = title if page.meta.get("raw_title") else f"{title} — uqulang"

    body = page.body.replace("{{post_list}}", render_post_list(pages, lang))
    body = expand_code_blocks(body, lang)
    body = body.replace("{{docs_aside}}", render_docs_aside(page.path))
    body = body.replace("{{docs_toc}}", DOCS_TOC)
    body = body.replace("{{docs_sidebar}}", render_docs_sidebar(page.path))
    body = body.replace("{{portal}}", PORTAL_URL)
    body = body.replace("{{support}}", SUPPORT_URL)
    body = body.replace("{{contact}}", url(CONTACT_URL))
    body = body.replace("{{email}}", CONTACT_EMAIL)
    body = body.replace("{{build_date}}", BUILD_DATE)
    body = HIJRI_RE.sub(
        lambda m: f'<span class="date-hijri">{format_hijri(int(m.group(1)), int(m.group(2)), int(m.group(3)), lang)}</span>',
        body,
    )
    body = re.sub(r"\{\{url:([^}]+)\}\}", lambda m: url(m.group(1)), body)

    pairs = page.meta.get("alternates") or {}
    other = "ar" if lang == "en" else "en"
    if pairs.get(other):
        label = "العربية" if other == "ar" else "English"
        lang_switch = (
            f'<a class="btn btn--ghost btn--sm" href="{url(pairs[other])}" '
            f'lang="{other}" hreflang="{other}">{label}</a>'
        )
    else:
        lang_switch = ""

    header_cta = page.meta.get("header_cta")
    if header_cta is None:
        label = "اطلب ترخيصاً" if lang == "ar" else "Request a licence"
        header_cta = f'<a class="btn btn--primary btn--sm" href="{url(CONTACT_URL)}">{label}</a>'

    values = {
        "lang": lang,
        "dir": strings["dir"],
        "og_locale": strings["og_locale"],
        "title": html.escape(full_title, quote=True),
        "og_title": html.escape(page.meta.get("og_title", full_title), quote=True),
        "description": html.escape(page.meta["description"], quote=True),
        "path": url(page.path if page.path != "/" else "/"),
        "site_url": SITE_URL,
        "base": BASE,
        "stylesheet": stylesheet,
        "theme_init": theme_init,
        "modulepreload": "\n".join(
            f'<link rel="modulepreload" href="{BASE}/assets/js/{module}">' for module in JS_MODULES
        ),
        "alternates": alternates(page),
        "body_class": page.meta.get("body_class", ""),
        "head_extra": page.meta.get("head_extra", ""),
        "nav_links": render_nav(lang, page.meta.get("nav")),
        "header_cta": header_cta,
        "lang_switch": lang_switch,
        "footer_groups": render_footer_groups(lang),
        "footer_about": strings["footer_about"],
        "footer_legal": strings["footer_legal"],
        "footer_made": strings["footer_made"],
        "skip_label": strings["skip_label"],
        "nav_label": strings["nav_label"],
        "menu_label": strings["menu_label"],
        "home_label": strings["home_label"],
        "home_suffix": strings["home_suffix"],
        "content": body.strip(),
    }

    out = layout
    for key, value in values.items():
        out = out.replace(f"{{{{{key}}}}}", str(value))

    leftover = re.findall(r"\{\{[a-z_:][^}]*\}\}", out)
    if leftover:
        raise SystemExit(f"{page.source}: unresolved placeholders {sorted(set(leftover))}")
    return out


def minify_theme_init(source: str) -> str:
    """Inline the theme guard from its real file so there is one copy of it.

    Comments and indentation are stripped because this script is inlined into
    every page and hashed for the Content-Security-Policy.
    """
    body = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    lines = [line.strip() for line in body.splitlines()]
    return "".join(line for line in lines if line)


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<(script|style|pre)\b.*?</\1>", " ", fragment, flags=re.DOTALL | re.IGNORECASE)
    text = TAG_RE.sub(" ", text)
    return WS_RE.sub(" ", html.unescape(text)).strip()


def render_post_list(pages: "list[Page]", lang: str) -> str:
    """The blog index, generated from the posts themselves.

    Adding a post is one file: the listing, its date and its excerpt come from
    that post's front matter, so the index can never fall out of step with it.
    """
    posts = [p for p in pages if p.meta.get("layout") == "post" and p.lang == lang]
    posts.sort(key=lambda p: str(p.meta.get("date", "")), reverse=True)

    if not posts:
        return '<p class="post__excerpt">No posts yet.</p>'

    items = []
    for post in posts:
        date = str(post.meta.get("date", ""))
        try:
            year, month, day = (int(part) for part in date.split("-"))
            human = dt.date(year, month, day).strftime("%-d %B %Y")
            hijri = f'<span class="date-hijri">{format_hijri(year, month, day, lang)}</span>'
        except (ValueError, TypeError):
            human, hijri = date, ""

        label = html.escape(str(post.meta.get("kind", "Release")))
        excerpt = post.meta.get("excerpt", post.meta["description"])
        items.append(
            "<li>"
            f'<div class="post__meta"><time datetime="{date}">{human}</time>{hijri}'
            f"<span>{label}</span></div>"
            f'<h2 class="post__title"><a href="{url(post.path)}">{html.escape(post.meta["title"])}</a></h2>'
            f'<p class="post__excerpt">{excerpt}</p>'
            "</li>"
        )
    return '<ul class="post-list">' + "".join(items) + "</ul>"


def build_search_index(pages: list[Page]) -> list[dict]:
    """One entry per page plus one per h2, so a search hit lands on a section."""
    entries = []
    for page in pages:
        if not page.meta.get("search", True) or page.lang != "en":
            continue

        section = page.meta.get("section", "Documentation")
        entries.append({
            "title": page.meta["title"],
            "section": section,
            "url": url(page.path),
            "body": strip_tags(expand_code_blocks(page.body))[:600],
        })

        for match in re.finditer(
            r'<h2[^>]*\bid="(?P<id>[^"]+)"[^>]*>(?P<text>.*?)</h2>(?P<rest>.*?)(?=<h2|\Z)',
            expand_code_blocks(page.body),
            re.DOTALL,
        ):
            entries.append({
                "title": strip_tags(match.group("text")).replace("#", "").strip(),
                "section": page.meta["title"],
                "url": f'{url(page.path)}#{match.group("id")}',
                "body": strip_tags(match.group("rest"))[:400],
            })
    return entries


def build_sitemap(pages: list[Page]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for page in pages:
        if not page.meta.get("sitemap", True):
            continue
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE_URL}{url(page.path)}</loc>")
        lines.append(f"    <lastmod>{BUILD_DATE}</lastmod>")
        lines.append(f'    <priority>{page.meta.get("priority", "0.6")}</priority>')
        for lang, path in (page.meta.get("alternates") or {}).items():
            lines.append(
                f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{SITE_URL}{url(path)}"/>'
            )
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def write(path: Path, content: str, *, check: bool, changed: list[str]) -> None:
    rel = path.relative_to(ROOT)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return
    changed.append(str(rel))
    if check:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build uqulang.org")
    parser.add_argument("--check", action="store_true", help="fail if output is stale")
    args = parser.parse_args()

    layout = (SRC / "_layout.html").read_text(encoding="utf-8")
    pages = read_pages()
    if not pages:
        raise SystemExit("no pages found in src/pages")

    changed: list[str] = []
    stylesheet = build_stylesheet(check=args.check, changed=changed)
    theme_init = minify_theme_init((ROOT / "assets/js/theme-init.js").read_text(encoding="utf-8"))

    for page in pages:
        write(
            page.out_file,
            render(page, layout, stylesheet=stylesheet, theme_init=theme_init, pages=pages),
            check=args.check,
            changed=changed,
        )

    write(
        ROOT / "search-index.json",
        json.dumps(build_search_index(pages), ensure_ascii=False, indent=0) + "\n",
        check=args.check,
        changed=changed,
    )
    write(ROOT / "sitemap.xml", build_sitemap(pages), check=args.check, changed=changed)

    if args.check:
        if changed:
            print("stale output, run: python3 tools/build.py")
            for name in changed:
                print(f"  {name}")
            return 1
        print(f"up to date — {len(pages)} pages")
        return 0

    print(f"built {len(pages)} pages" + (f", {len(changed)} file(s) written" if changed else ", no changes"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
