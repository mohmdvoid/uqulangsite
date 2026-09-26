#!/usr/bin/env python3
"""
uqulang.com static site generator.

    python3 tools/build.py            # write the site
    python3 tools/build.py --check    # verify output is up to date (CI)

Design
------
The site is multilingual by construction rather than by retrofit. A page's
locale and its URL both come from where its source file sits:

    src/pages/docs/tour.md      ->  en  ->  /docs/tour/
    src/pages/ar/docs/tour.md   ->  ar  ->  /ar/docs/tour/

Both files share the translation key `docs/tour`, which is what pairs them.
From that pairing the generator derives the hreflang alternates, the language
switcher, and whether a link should point at a translated page or fall back to
the default locale. Adding a language is a JSON file in src/i18n/ plus the
pages you choose to translate; nothing in this file needs to change.

Everything a translator touches — interface strings, navigation, footer,
documentation sidebar — lives in src/i18n/<code>.json, never in Python.

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
from dataclasses import dataclass
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
I18N = SRC / "i18n"
CSS_SRC = SRC / "css"
CSS_OUT = ROOT / "assets" / "css"

# --- Site configuration ---------------------------------------------------
# BASE is the path the site is served from. "" means the domain root.
SITE_URL = "https://uqulang.com"
BASE = ""

# Commercial product: licensed to universities and research institutions.
EXTERNAL = {
    "portal": "https://portal.uqulang.com",
    "support": "https://support.uqulang.com",
}
CONTACT_PATH = "/universities/#contact"
CONTACT_EMAIL = "universities@uqulang.com"

BUILD_DATE = dt.date.today().isoformat()

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

# Preloading turns a three-round-trip import waterfall into one parallel fetch.
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

META_RE = re.compile(r"^\s*<!--meta\s*(?P<json>\{.*?\})\s*meta-->\s*", re.DOTALL)
FRONT_MATTER_RE = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)
CODE_RE = re.compile(r"<!--code(?P<attrs>[^>]*?)-->\n(?P<code>.*?)\n<!--/code-->", re.DOTALL)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
FENCE_RE = re.compile(
    r"^```(?P<lang>[\w-]*)(?P<attrs>[^\n]*)\n(?P<code>.*?)\n```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
ADMONITION_RE = re.compile(
    r"(?:^> \[!(?P<kind>NOTE|WARNING|TIP)\][ \t]*\n(?P<body>(?:^>.*\n?)*))",
    re.MULTILINE,
)
TABLE_RE = re.compile(r"(<table>.*?</table>)", re.DOTALL)
HIJRI_RE = re.compile(r"\{\{hijri:(\d{4})-(\d{2})-(\d{2})\}\}")
STRING_RE = re.compile(r"\{\{t:([a-z_]+)\}\}")
URL_RE = re.compile(r"\{\{url:([^}]+)\}\}")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TOKEN = "⟦BLOCK{}⟧"
TOKEN_P_RE = re.compile(r"<p>\s*⟦BLOCK(\d+)⟧\s*</p>")

COPY_ICONS = (
    '<svg class="code-copy__icon code-copy__icon--idle" viewBox="0 0 16 16" fill="none" '
    'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
    '<rect x="5.5" y="5.5" width="8" height="9" rx="1.5"/>'
    '<path d="M10.5 3.5h-6a1.5 1.5 0 0 0-1.5 1.5v6"/></svg>'
    '<svg class="code-copy__icon code-copy__icon--done" viewBox="0 0 16 16" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M3 8.5l3.5 3.5L13 5"/></svg>'
)

ADMONITION_ICONS = {
    "NOTE": ("callout--note", '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.4"/>'),
    "TIP": ("callout--note", '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.4"/>'),
    "WARNING": ("callout--warn", '<path d="M12 4.5 21 19.5H3z"/><path d="M12 10v4M12 16.8v.2"/>'),
}

# --- Hijri dates ----------------------------------------------------------
# Tabular (Kuwaiti) algorithm: the standard civil approximation. It can differ
# from the Umm al-Qura calendar by a day, so dates are checked before a post is
# published — see PLACEHOLDERS.md.
HIJRI_MONTHS = {
    "en": ["Muharram", "Safar", "Rabiʿ al-Awwal", "Rabiʿ al-Thani",
           "Jumada al-Ula", "Jumada al-Akhira", "Rajab", "Shaʿban",
           "Ramadan", "Shawwal", "Dhu al-Qaʿda", "Dhu al-Hijja"],
    "ar": ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى",
           "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال",
           "ذو القعدة", "ذو الحجة"],
}


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


def format_hijri(year: int, month: int, day: int, code: str) -> str:
    hy, hm, hd = to_hijri(year, month, day)
    months = HIJRI_MONTHS.get(code, HIJRI_MONTHS["en"])
    if code == "ar":
        return f"{hd} {months[hm - 1]} {hy}هـ"
    return f"{hd} {months[hm - 1]} {hy} AH"


# --- Locales --------------------------------------------------------------


class Catalog:
    """Interface strings for one locale, with a fallback to the default.

    A missing key is an error rather than an empty string: a half-translated
    page is worse than an obviously untranslated one, and this way the build
    tells you which key you forgot.
    """

    def __init__(self, strings: dict, fallback: "Catalog | None" = None):
        self._strings = strings
        self._fallback = fallback

    def __contains__(self, key: str) -> bool:
        return key in self._strings or (self._fallback is not None and key in self._fallback)

    def get(self, key: str, **params) -> str:
        if key in self._strings:
            value = self._strings[key]
        elif self._fallback is not None:
            value = self._fallback.get(key)
        else:
            raise SystemExit(f"missing interface string: {key!r}")
        return value.format(**params) if params else value


@dataclass
class Locale:
    """One language: its direction, its URL prefix, and everything a
    translator can edit for it."""

    code: str
    name: str
    dir: str
    prefix: str
    is_default: bool
    order: int
    catalog: Catalog
    nav: list
    footer: list
    docs_tree: list

    @property
    def is_rtl(self) -> bool:
        return self.dir == "rtl"

    def home(self) -> str:
        return f"{self.prefix}/" if self.prefix else "/"

    def localise(self, path: str) -> str:
        """Prefix a default-locale path for this locale."""
        if not self.prefix or not path.startswith("/"):
            return path
        if path == "/":
            return f"{self.prefix}/"
        return f"{self.prefix}{path}"

    def t(self, key: str, **params) -> str:
        return self.catalog.get(key, **params)


class Localiser:
    """The set of locales, loaded from src/i18n/*.json."""

    def __init__(self, directory: Path):
        raw = {}
        for path in sorted(directory.glob("*.json")):
            try:
                raw[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise SystemExit(f"{path}: invalid JSON — {error}") from error

        if not raw:
            raise SystemExit(f"no locale files found in {directory}")

        defaults = [code for code, data in raw.items() if data.get("default")]
        if len(defaults) != 1:
            raise SystemExit(f'exactly one locale must set "default": true, found {defaults}')
        self.default_code = defaults[0]

        base_catalog = Catalog(raw[self.default_code]["strings"])
        self.locales: dict = {}
        for code, data in raw.items():
            is_default = code == self.default_code
            self.locales[code] = Locale(
                code=code,
                name=data["name"],
                dir=data.get("dir", "ltr"),
                prefix=data.get("prefix", "").rstrip("/"),
                is_default=is_default,
                order=data.get("order", 99),
                catalog=Catalog(data["strings"], None if is_default else base_catalog),
                nav=data.get("nav", []),
                footer=data.get("footer", []),
                docs_tree=data.get("docs_tree", []),
            )

        prefixes = [loc.prefix for loc in self.locales.values() if loc.prefix]
        if len(set(prefixes)) != len(prefixes):
            raise SystemExit("two locales share a URL prefix")

    @property
    def default(self) -> Locale:
        return self.locales[self.default_code]

    def __getitem__(self, code: str) -> Locale:
        if code not in self.locales:
            raise SystemExit(f"unknown locale {code!r}; add src/i18n/{code}.json")
        return self.locales[code]

    def ordered(self) -> list:
        return sorted(self.locales.values(), key=lambda loc: loc.order)

    def code_for_source(self, relative: Path) -> str:
        """The locale of a page source, from its first path segment."""
        head = relative.parts[0] if relative.parts else ""
        if head in self.locales and head != self.default_code:
            return head
        return self.default_code


# --- Pages ----------------------------------------------------------------


@dataclass
class Page:
    source: Path
    meta: dict
    body: str
    locale: Locale
    key: str

    @property
    def path(self) -> str:
        return self.meta["path"]

    @property
    def out_file(self) -> Path:
        path = self.path
        if path == "/":
            return ROOT / "index.html"
        if path.endswith(".html"):
            return ROOT / path.lstrip("/")
        return ROOT / path.strip("/") / "index.html"


def url(path: str) -> str:
    """Resolve an internal path against BASE. External URLs pass through."""
    if path.startswith(("http://", "https://", "#", "mailto:")):
        return path
    return f"{BASE}{path}"


def derive_key_and_path(relative: Path, locale: Locale, default_code: str) -> "tuple[str, str]":
    """Translation key and URL, both from where the file sits.

    `docs/tour.md` -> key `docs/tour`, path `/docs/tour/`
    `ar/docs/tour.md` -> key `docs/tour`, path `/ar/docs/tour/`
    """
    parts = list(relative.parts)
    if parts and parts[0] == locale.code and locale.code != default_code:
        parts = parts[1:]

    stem = parts[-1]
    for suffix in (".page.html", ".md", ".html"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    parts[-1] = stem
    key = "/".join(parts)

    if key == "index":
        path = locale.home()
    elif key == "404":
        path = f"{locale.prefix}/404.html" if locale.prefix else "/404.html"
    elif stem == "index":
        path = locale.localise("/" + "/".join(parts[:-1]) + "/")
    else:
        path = locale.localise("/" + key + "/")
    return key, path


# --- Content rendering ----------------------------------------------------


class ContentRenderer:
    """Turns a page body — Markdown or HTML — into the site's markup."""

    def __init__(self, locale: Locale):
        self.locale = locale

    def expand_code_blocks(self, body: str) -> str:
        """`<!--code ...--> ... <!--/code-->` becomes a code figure.

        The author writes raw source; escaping happens here, once, correctly.
        """
        copy_label = self.locale.t("copy")
        copy_aria = self.locale.t("copy_code")

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
                        f"{COPY_ICONS}<span data-code-copy-label>{copy_label}</span></button></div>"
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

    def markdown(self, body: str, source: Path) -> str:
        """Markdown to the HTML this site's stylesheet expects.

        Fenced code and admonitions are lifted out first so the author writes
        plain Markdown while the output still carries the copy button, the
        syntax spans and the callout markup. Raw HTML passes through untouched.
        """
        blocks: list = []

        def stash(fragment: str) -> str:
            blocks.append(fragment)
            return TOKEN.format(len(blocks) - 1)

        def take_fence(match: "re.Match[str]") -> str:
            lang = match.group("lang") or "text"
            attrs = dict(ATTR_RE.findall(match.group("attrs") or ""))
            fence = f'<!--code lang="{lang}"'
            if attrs.get("file"):
                fence += f' file="{attrs["file"]}"'
            if attrs.get("copy") == "false":
                fence += ' copy="false"'
            rendered = self.expand_code_blocks(f"{fence}-->\n{match.group('code')}\n<!--/code-->")
            return "\n" + stash(rendered) + "\n"

        def take_admonition(match: "re.Match[str]") -> str:
            kind = match.group("kind")
            inner = "\n".join(
                line[2:] if line.startswith("> ") else line[1:]
                for line in match.group("body").splitlines()
            )
            modifier, icon = ADMONITION_ICONS[kind]
            rendered = self.markdown(inner, source)
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
        out = converter.convert(body)

        # Tables need the horizontal-scroll wrapper to survive a phone screen.
        out = TABLE_RE.sub(r'<div class="table-wrap">\1</div>', out)

        out = TOKEN_P_RE.sub(lambda m: blocks[int(m.group(1))], out)
        for index, block in enumerate(blocks):
            out = out.replace(TOKEN.format(index), block)
        return out


# --- Layouts --------------------------------------------------------------


class LayoutRenderer:
    """Wraps converted content in the furniture its layout implies."""

    def __init__(self, site: "Site"):
        self.site = site

    def apply(self, page: Page, content: str) -> str:
        layout = page.meta.get("layout", "raw")
        if layout == "raw":
            return content
        if layout == "post":
            layout = "page"

        locale, meta = page.locale, page.meta
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
                f'<li><a href="{url(self.site.resolve(path, locale))}">{html.escape(label)}</a></li>'
                for label, path in meta["breadcrumb"]
            )
            current = meta.get("breadcrumb_current", meta["title"])
            crumbs = f'<ol class="breadcrumb">{items}<li>{html.escape(current)}</li></ol>'

        nav = self._pagination(page)

        if layout == "docs":
            aside = self.docs_aside(page)
            toc = self.docs_toc(locale)
            return (
                f'<div class="container container--docs docs">{aside}<div class="docs-main">'
                f"{crumbs}{header_html}"
                f'<article class="docs-article" data-heading-anchors>{content}</article>'
                f"{nav}</div>{toc}</div>"
            )

        return (
            f'<div class="container container--narrow page-head">{crumbs}{header_html}</div>'
            f'<div class="container container--narrow" data-heading-anchors>'
            f'<section class="docs-article prose-wide">{content}</section>{nav}</div>'
        )

    def _pagination(self, page: Page) -> str:
        locale, meta = page.locale, page.meta
        previous, following = meta.get("prev"), meta.get("next")
        if not previous and not following:
            return ""

        links = []
        if previous:
            target = url(self.site.resolve(previous["path"], locale))
            links.append(
                f'<a class="page-nav__link" href="{target}">'
                f'<span class="page-nav__dir">{locale.t("previous")}</span>'
                f'<span class="page-nav__title">{html.escape(previous["title"])}</span></a>'
            )
        if following:
            target = url(self.site.resolve(following["path"], locale))
            links.append(
                f'<a class="page-nav__link page-nav__link--next" href="{target}">'
                f'<span class="page-nav__dir">{locale.t("next")}</span>'
                f'<span class="page-nav__title">{html.escape(following["title"])}</span></a>'
            )
        return f'<nav class="page-nav" aria-label="{locale.t("pagination")}">{"".join(links)}</nav>'

    def docs_sidebar(self, page: Page) -> str:
        locale = page.locale
        groups = []
        for group in locale.docs_tree:
            items = []
            for item in group["items"]:
                target = self.site.resolve(item["path"], locale)
                aria = ' aria-current="page"' if target == page.path else ""
                items.append(
                    f'<li><a class="docs-nav__link" href="{url(target)}"{aria}>'
                    f'{html.escape(item["label"])}</a></li>'
                )
            groups.append(
                '<li class="docs-nav__group">'
                f'<span class="docs-nav__group-title">{html.escape(group["title"])}</span>'
                f'<ul class="docs-nav__sub">{"".join(items)}</ul></li>'
            )
        return "".join(groups)

    def docs_aside(self, page: Page) -> str:
        locale = page.locale
        return (
            '<aside class="docs-sidebar"><details class="docs-sidebar__disclosure" open><summary>'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" aria-hidden="true">'
            '<path d="M4 7h16M4 12h16M4 17h16"/></svg>'
            f'{locale.t("documentation")}</summary>'
            f'<div class="docs-search" data-search="{url(self.site.search_index_path(locale))}">'
            '<svg class="docs-search__icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" aria-hidden="true">'
            '<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>'
            f'<label class="visually-hidden" for="docs-search-input">{locale.t("search_label")}</label>'
            '<input class="docs-search__input" id="docs-search-input" type="search" '
            f'placeholder="{locale.t("search_placeholder")}" autocomplete="off" spellcheck="false" data-search-input>'
            f'<ul class="docs-search__results" aria-label="{locale.t("search_results")}" data-search-results></ul>'
            '<p class="visually-hidden" role="status" data-search-status></p>'
            "</div>"
            f'<h2 class="docs-sidebar__title">{locale.t("documentation")}</h2>'
            f'<ul class="docs-nav">{self.docs_sidebar(page)}</ul>'
            "</details></aside>"
        )

    @staticmethod
    def docs_toc(locale: Locale) -> str:
        return (
            '<aside class="docs-toc" data-toc=".docs-article">'
            f'<h2 class="docs-toc__title">{locale.t("on_this_page")}</h2>'
            '<ul class="docs-toc__list" data-toc-list></ul></aside>'
        )


# --- The site -------------------------------------------------------------


class Site:
    def __init__(self):
        self.localiser = Localiser(I18N)
        self.layout_html = (SRC / "_layout.html").read_text(encoding="utf-8")
        self.pages: list = []
        self.by_key: dict = {}
        self.paths: set = set()
        self.layouts = LayoutRenderer(self)

    # -- collection --------------------------------------------------------

    def collect(self) -> "Site":
        sources = sorted(PAGES.rglob("*.md")) + sorted(PAGES.rglob("*.page.html"))
        raw_pages = [self._read(source) for source in sources]

        paths = [page.path for page in raw_pages]
        duplicates = {p for p in paths if paths.count(p) > 1}
        if duplicates:
            raise SystemExit(f"two sources claim the same path: {sorted(duplicates)}")
        self.paths = set(paths)

        for page in raw_pages:
            self.by_key.setdefault(page.key, {})[page.locale.code] = page

        # Layouts resolve links, so they run once every path is known.
        for page in raw_pages:
            page.body = self.layouts.apply(page, page.body)

        self.pages = sorted(raw_pages, key=lambda page: (page.locale.order, page.path))
        return self

    def _read(self, source: Path) -> Page:
        relative = source.relative_to(PAGES)
        locale = self.localiser[self.localiser.code_for_source(relative)]
        raw = source.read_text(encoding="utf-8")
        renderer = ContentRenderer(locale)

        if source.suffix == ".md":
            meta, body = self._front_matter(raw, source)
            meta.setdefault("layout", "docs")
            content = renderer.markdown(body, source)
        else:
            match = META_RE.match(raw)
            if not match:
                raise SystemExit(f"{source}: missing <!--meta ... meta--> block")
            try:
                meta = json.loads(match.group("json"))
            except json.JSONDecodeError as error:
                raise SystemExit(f"{source}: invalid meta JSON — {error}") from error
            content = raw[match.end():]

        for required in ("title", "description"):
            if required not in meta:
                raise SystemExit(f"{source}: front matter is missing '{required}'")
        if len(str(meta["description"])) < 50:
            raise SystemExit(f"{source}: description is shorter than 50 characters")

        key, derived_path = derive_key_and_path(relative, locale, self.localiser.default_code)
        meta.setdefault("path", derived_path)
        if locale.prefix and not meta["path"].startswith(locale.prefix):
            raise SystemExit(
                f"{source}: path {meta['path']} does not start with the "
                f"{locale.code} prefix {locale.prefix}"
            )

        return Page(source=source, meta=meta, body=content, locale=locale, key=key)

    @staticmethod
    def _front_matter(text: str, source: Path) -> "tuple[dict, str]":
        """YAML-shaped `key: value` front matter, without a YAML dependency.

        Values are parsed as JSON when they look like it (so `true`, numbers and
        `{"title": "..."}` work) and treated as plain strings otherwise.
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

    # -- locale-aware link resolution --------------------------------------

    def resolve(self, path: str, locale: Locale) -> str:
        """The best URL for `path` when reading in `locale`.

        A default-locale path is rewritten to the translated page when one
        exists, and left pointing at the original when it does not — so a link
        in an Arabic page never leads to a 404, and starts working on its own
        the day somebody translates the target.
        """
        if path.startswith(("http://", "https://", "mailto:", "#")):
            return path
        if locale.is_default:
            return path

        anchor = ""
        if "#" in path:
            path, _, fragment = path.partition("#")
            anchor = "#" + fragment

        localised = locale.localise(path)
        return (localised if localised in self.paths else path) + anchor

    def translations_of(self, page: Page) -> dict:
        return self.by_key.get(page.key, {})

    def search_index_path(self, locale: Locale) -> str:
        if locale.is_default:
            return "/search-index.json"
        return f"{locale.prefix}/search-index.json"

    # -- rendering ---------------------------------------------------------

    def render(self, page: Page, *, stylesheet: str, theme_init: str) -> str:
        locale = page.locale
        title = page.meta["title"]
        full_title = title if page.meta.get("raw_title") else f"{title} — uqulang"

        body = page.body
        body = body.replace("{{post_list}}", self.post_list(locale))
        body = ContentRenderer(locale).expand_code_blocks(body)
        body = body.replace("{{build_date}}", BUILD_DATE)
        body = body.replace("{{contact}}", url(self.resolve(CONTACT_PATH, locale)))
        body = body.replace("{{email}}", CONTACT_EMAIL)
        for name, target in EXTERNAL.items():
            body = body.replace("{{%s}}" % name, target)
        body = HIJRI_RE.sub(
            lambda m: '<span class="date-hijri">'
                      + format_hijri(int(m.group(1)), int(m.group(2)), int(m.group(3)), locale.code)
                      + "</span>",
            body,
        )
        body = STRING_RE.sub(lambda m: locale.t(m.group(1)), body)
        body = URL_RE.sub(lambda m: url(self.resolve(m.group(1), locale)), body)

        # Markdown authors write plain site paths; localise them the same way.
        if page.source.suffix == ".md" and not locale.is_default:
            body = re.sub(
                r'href="(/[^"]*)"',
                lambda m: 'href="' + url(self.resolve(m.group(1), locale)) + '"',
                body,
            )
        elif BASE:
            body = re.sub(r'href="(/[^"]*)"', lambda m: f'href="{BASE}{m.group(1)}"', body)

        values = {
            "lang": locale.code,
            "dir": locale.dir,
            "og_locale": locale.code,
            "title": html.escape(full_title, quote=True),
            "og_title": html.escape(page.meta.get("og_title", full_title), quote=True),
            "description": html.escape(page.meta["description"], quote=True),
            "path": url(page.path),
            "site_url": SITE_URL,
            "base": BASE,
            "stylesheet": stylesheet,
            "theme_init": theme_init,
            "modulepreload": "\n".join(
                f'<link rel="modulepreload" href="{BASE}/assets/js/{module}">'
                for module in JS_MODULES
            ),
            "alternates": self.alternate_links(page),
            "feed_link": (
                f'<link rel="alternate" type="application/atom+xml" '
                f'title="uqulang releases" href="{url(self.feed_path(locale))}">'
                if self.feed(locale) else ""
            ),
            "body_class": page.meta.get("body_class", ""),
            "head_extra": page.meta.get("head_extra", ""),
            "nav_links": self.nav_links(page),
            "header_cta": self.header_cta(page),
            "lang_switch": self.language_switch(page),
            "footer_groups": self.footer_groups(locale),
            "footer_about": locale.t("footer_about"),
            "footer_legal": locale.t("footer_legal", year=dt.date.today().year),
            "footer_made": locale.t("footer_made"),
            "skip_label": locale.t("skip_to_content"),
            "nav_label": locale.t("main_nav"),
            "menu_label": locale.t("open_menu"),
            "theme_label": locale.t("switch_theme"),
            "home_label": locale.t("home"),
            "home_href": url(locale.home()),
            "content": body.strip(),
        }

        out = self.layout_html
        for key, value in values.items():
            out = out.replace(f"{{{{{key}}}}}", str(value))

        leftover = re.findall(r"\{\{[a-z_:][^}]*\}\}", out)
        if leftover:
            raise SystemExit(f"{page.source}: unresolved placeholders {sorted(set(leftover))}")
        return out

    def nav_links(self, page: Page) -> str:
        locale = page.locale
        current = page.meta.get("nav")
        out = []
        for item in locale.nav:
            target = self.resolve(item["path"], locale)
            aria = ' aria-current="page"' if item["key"] == current else ""
            out.append(
                f'<a class="site-nav__link" href="{url(target)}"{aria}>'
                f'{html.escape(item["label"])}</a>'
            )
        return "\n      ".join(out)

    def footer_groups(self, locale: Locale) -> str:
        blocks = []
        for group in locale.footer:
            items = []
            for link in group["links"]:
                if "url" in link:
                    target = EXTERNAL[link["url"]]
                else:
                    target = url(self.resolve(link["path"], locale))
                items.append(f'<li><a href="{target}">{html.escape(link["label"])}</a></li>')
            blocks.append(
                '<div class="footer-group">'
                f'<h2 class="footer-group__title">{html.escape(group["title"])}</h2>'
                f'<ul class="footer-group__list">{"".join(items)}</ul></div>'
            )
        return "\n      ".join(blocks)

    def header_cta(self, page: Page) -> str:
        if "header_cta" in page.meta:
            return page.meta["header_cta"]
        locale = page.locale
        return (
            f'<a class="btn btn--primary btn--sm" href="{url(self.resolve(CONTACT_PATH, locale))}">'
            f'{locale.t("header_cta")}</a>'
        )

    def language_switch(self, page: Page) -> str:
        """Switch to the same page in another language, or that language's home.

        The title says which of the two it is, so a reader is never surprised to
        land on the front page of a site they have not seen.
        """
        translations = self.translations_of(page)
        links = []
        for other in self.localiser.ordered():
            if other.code == page.locale.code:
                continue
            counterpart = translations.get(other.code)
            target = counterpart.path if counterpart else other.home()
            label_key = "switch_language" if counterpart else "switch_language_home"
            links.append(
                f'<a class="btn btn--ghost btn--sm" href="{url(target)}" lang="{other.code}" '
                f'hreflang="{other.code}" title="{html.escape(page.locale.t(label_key))}">'
                f"{html.escape(other.name)}</a>"
            )
        return "".join(links)

    def alternate_links(self, page: Page) -> str:
        translations = self.translations_of(page)
        if len(translations) < 2:
            return ""
        lines = [
            f'<link rel="alternate" hreflang="{code}" href="{SITE_URL}{url(other.path)}">'
            for code, other in sorted(translations.items())
        ]
        default = translations.get(self.localiser.default_code)
        if default:
            lines.append(
                f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}{url(default.path)}">'
            )
        return "\n".join(lines)

    def post_list(self, locale: Locale) -> str:
        """The blog index, generated from the posts themselves."""
        posts = [
            page for page in self.pages
            if page.meta.get("layout") == "post" and page.locale.code == locale.code
        ]
        posts.sort(key=lambda page: str(page.meta.get("date", "")), reverse=True)
        if not posts:
            return f'<p class="post__excerpt">{locale.t("no_posts")}</p>'

        items = []
        for post in posts:
            date = str(post.meta.get("date", ""))
            try:
                year, month, day = (int(part) for part in date.split("-"))
                human = dt.date(year, month, day).strftime("%-d %B %Y")
                hijri = ('<span class="date-hijri">'
                         + format_hijri(year, month, day, locale.code) + "</span>")
            except (ValueError, TypeError):
                human, hijri = date, ""

            label = html.escape(str(post.meta.get("kind", locale.t("release"))))
            excerpt = post.meta.get("excerpt", post.meta["description"])
            items.append(
                "<li>"
                f'<div class="post__meta"><time datetime="{date}">{human}</time>{hijri}'
                f"<span>{label}</span></div>"
                f'<h2 class="post__title"><a href="{url(post.path)}">'
                f'{html.escape(post.meta["title"])}</a></h2>'
                f'<p class="post__excerpt">{excerpt}</p>'
                "</li>"
            )
        return '<ul class="post-list">' + "".join(items) + "</ul>"

    # -- generated assets --------------------------------------------------

    def stylesheet(self, *, check: bool, changed: list) -> str:
        """Concatenate the CSS layers into one fingerprinted file."""
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

        for stale in CSS_OUT.glob("site.*.css"):
            if stale.name != filename:
                changed.append(f"removed {stale.relative_to(ROOT)}")
                if not check:
                    stale.unlink()

        return f"{BASE}/assets/css/{filename}"

    def search_index(self, locale: Locale) -> list:
        """One entry per page plus one per h2, so a hit lands on a section."""
        entries = []
        for page in self.pages:
            if page.locale.code != locale.code or not page.meta.get("search", True):
                continue

            entries.append({
                "title": page.meta["title"],
                "section": page.meta.get("section", locale.t("documentation")),
                "url": url(page.path),
                "body": strip_tags(page.body)[:600],
            })

            for match in re.finditer(
                r'<h2[^>]*\bid="(?P<id>[^"]+)"[^>]*>(?P<text>.*?)</h2>(?P<rest>.*?)(?=<h2|\Z)',
                page.body,
                re.DOTALL,
            ):
                entries.append({
                    "title": strip_tags(match.group("text")).replace("#", "").strip(),
                    "section": page.meta["title"],
                    "url": f'{url(page.path)}#{match.group("id")}',
                    "body": strip_tags(match.group("rest"))[:400],
                })
        return entries

    def feed(self, locale: Locale) -> "str | None":
        """Atom feed of this locale's posts.

        Atom rather than RSS: dates are unambiguous (RFC 3339), content type
        is explicit, and every reader supports it. A locale with no posts gets
        no feed rather than an empty one.
        """
        posts = [
            page for page in self.pages
            if page.meta.get("layout") == "post" and page.locale.code == locale.code
        ]
        posts.sort(key=lambda page: str(page.meta.get("date", "")), reverse=True)
        if not posts:
            return None

        def entry(post: Page) -> str:
            date = str(post.meta.get("date", BUILD_DATE))
            updated = f"{date}T00:00:00Z"
            link = f"{SITE_URL}{url(post.path)}"
            summary = post.meta.get("excerpt", post.meta["description"])
            return (
                "  <entry>\n"
                f"    <title>{html.escape(post.meta['title'])}</title>\n"
                f'    <link href="{link}"/>\n'
                f"    <id>{link}</id>\n"
                f"    <updated>{updated}</updated>\n"
                f"    <published>{updated}</published>\n"
                f'    <category term="{html.escape(str(post.meta.get("kind", "Release")))}"/>\n'
                f'    <summary type="text">{html.escape(summary)}</summary>\n'
                "  </entry>"
            )

        self_url = f"{SITE_URL}{url(self.feed_path(locale))}"
        home = f"{SITE_URL}{url(locale.home())}"
        newest = f"{posts[0].meta.get('date', BUILD_DATE)}T00:00:00Z"
        entries = "\n".join(entry(post) for post in posts)

        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{locale.code}">\n'
            f"  <title>{html.escape(locale.t('feed_title'))}</title>\n"
            f'  <link href="{home}"/>\n'
            f'  <link rel="self" type="application/atom+xml" href="{self_url}"/>\n'
            f"  <id>{self_url}</id>\n"
            f"  <updated>{newest}</updated>\n"
            "  <author><name>uqulang</name></author>\n"
            f"  <rights>© {dt.date.today().year} uqulang</rights>\n"
            f"{entries}\n"
            "</feed>\n"
        )

    @staticmethod
    def feed_path(locale: Locale) -> str:
        return "/feed.xml" if locale.is_default else f"{locale.prefix}/feed.xml"

    def sitemap(self) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
        ]
        for page in self.pages:
            if not page.meta.get("sitemap", True):
                continue
            lines.append("  <url>")
            lines.append(f"    <loc>{SITE_URL}{url(page.path)}</loc>")
            lines.append(f"    <lastmod>{BUILD_DATE}</lastmod>")
            lines.append(f'    <priority>{page.meta.get("priority", "0.6")}</priority>')
            for code, other in sorted(self.translations_of(page).items()):
                lines.append(
                    f'    <xhtml:link rel="alternate" hreflang="{code}" '
                    f'href="{SITE_URL}{url(other.path)}"/>'
                )
            lines.append("  </url>")
        lines.append("</urlset>")
        return "\n".join(lines) + "\n"


# --- Helpers --------------------------------------------------------------


def minify_theme_init(source: str) -> str:
    """Inline the theme guard from its real file so there is one copy of it."""
    body = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return "".join(line.strip() for line in body.splitlines() if line.strip())


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<(script|style|pre)\b.*?</\1>", " ", fragment, flags=re.DOTALL | re.IGNORECASE)
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", text))).strip()


def write(path: Path, content: str, *, check: bool, changed: list) -> None:
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
    parser = argparse.ArgumentParser(description="Build uqulang.com")
    parser.add_argument("--check", action="store_true", help="fail if output is stale")
    args = parser.parse_args()

    site = Site().collect()
    if not site.pages:
        raise SystemExit("no pages found in src/pages")

    changed: list = []
    stylesheet = site.stylesheet(check=args.check, changed=changed)
    theme_init = minify_theme_init((ROOT / "assets/js/theme-init.js").read_text(encoding="utf-8"))

    for page in site.pages:
        write(
            page.out_file,
            site.render(page, stylesheet=stylesheet, theme_init=theme_init),
            check=args.check,
            changed=changed,
        )

    for locale in site.localiser.ordered():
        target = ROOT / site.search_index_path(locale).lstrip("/")
        write(target, json.dumps(site.search_index(locale), ensure_ascii=False, indent=0) + "\n",
              check=args.check, changed=changed)

        feed = site.feed(locale)
        if feed:
            write(ROOT / site.feed_path(locale).lstrip("/"), feed, check=args.check, changed=changed)

    write(ROOT / "sitemap.xml", site.sitemap(), check=args.check, changed=changed)

    if args.check:
        if changed:
            print("stale output, run: python3 tools/build.py")
            for name in changed:
                print(f"  {name}")
            return 1
        print(f"up to date — {len(site.pages)} pages in {len(site.localiser.locales)} locales")
        return 0

    by_locale = ", ".join(
        f"{loc.code} {sum(1 for p in site.pages if p.locale.code == loc.code)}"
        for loc in site.localiser.ordered()
    )
    print(f"built {len(site.pages)} pages ({by_locale})"
          + (f", {len(changed)} file(s) written" if changed else ", no changes"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
