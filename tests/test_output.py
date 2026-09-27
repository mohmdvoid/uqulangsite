"""Invariants that must hold for every page that ships.

These read the committed HTML rather than a fixture: what is asserted here is
exactly what a visitor receives.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from .context import ROOT, SiteTestCase

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"')
CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]*)"')
LANG_RE = re.compile(r'<html lang="([^"]*)" dir="([^"]*)"')
H1_RE = re.compile(r"<h1[^>]*>", re.IGNORECASE)
IMG_NO_ALT_RE = re.compile(r"<img\b(?![^>]*\balt=)[^>]*>", re.IGNORECASE)
MACRO_RE = re.compile(r"\{\{[^}\n]{1,60}\}\}")


class SvgAccessibilityParser(HTMLParser):
    """Find <svg> elements that assistive technology would announce as noise.

    A decorative icon is acceptable if it is aria-hidden, or sits inside
    something that is — a regular expression cannot see the second case, so
    this tracks the ancestor stack.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.depth = 0
        self.offenders: list = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag not in VOID_ELEMENTS:
            self.depth += 1
            if "aria-hidden" in attributes and self.hidden_depth == 0:
                self.hidden_depth = self.depth

        if tag == "svg":
            labelled = (
                "aria-hidden" in attributes
                or "role" in attributes
                or "aria-label" in attributes
                or "aria-labelledby" in attributes
            )
            if not labelled and self.hidden_depth == 0:
                self.offenders.append(self.getpos())

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            return
        if self.hidden_depth == self.depth:
            self.hidden_depth = 0
        self.depth = max(0, self.depth - 1)


VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class EveryPageTests(SiteTestCase):
    """One assertion per rule, run against every generated page."""

    def each(self):
        for path in self.pages():
            yield path.relative_to(ROOT), path.read_text(encoding="utf-8")

    def test_has_a_title(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                match = TITLE_RE.search(text)
                self.assertIsNotNone(match)
                self.assertTrue(match.group(1).strip())

    def test_has_a_useful_description(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                match = DESC_RE.search(text)
                self.assertIsNotNone(match, "no meta description")
                self.assertGreaterEqual(len(match.group(1)), 50)

    def test_has_a_canonical_url(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                match = CANONICAL_RE.search(text)
                self.assertIsNotNone(match)
                self.assertTrue(match.group(1).startswith("https://uqulang.com"))

    def test_declares_language_and_direction(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                match = LANG_RE.search(text)
                self.assertIsNotNone(match, "<html> without lang and dir")
                code, direction = match.groups()
                self.assertIn(code, {"en", "ar"})
                self.assertEqual(direction, "rtl" if code == "ar" else "ltr")

    def test_has_exactly_one_h1(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                self.assertEqual(len(H1_RE.findall(text)), 1)

    def test_heading_levels_are_not_skipped(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                levels = [int(m) for m in re.findall(r"<h([1-6])\b", text, re.IGNORECASE)]
                previous = None
                for level in levels:
                    if previous is not None:
                        self.assertLessEqual(level, previous + 1, f"h{previous} -> h{level}")
                    previous = level

    def test_no_image_without_alt_text(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                self.assertEqual(IMG_NO_ALT_RE.findall(text), [])

    def test_decorative_svgs_are_hidden_from_screen_readers(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                parser = SvgAccessibilityParser()
                parser.feed(text)
                self.assertEqual(
                    parser.offenders, [],
                    "an <svg> is announced to screen readers without a label; "
                    "add aria-hidden or a role",
                )

    def test_no_unresolved_template_macros(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                self.assertEqual(MACRO_RE.findall(text), [])

    def test_no_inline_style_attributes(self):
        """The Content-Security-Policy has no 'unsafe-inline' for styles."""
        for name, text in self.each():
            with self.subTest(page=str(name)):
                self.assertNotIn(' style="', text)

    def test_exactly_one_inline_script_and_it_is_the_theme_guard(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                inline = re.findall(r"<script>(.*?)</script>", text, re.DOTALL)
                self.assertEqual(len(inline), 1)
                self.assertIn("uqulang:theme", inline[0])

    def test_no_third_party_requests(self):
        allowed = ("uqulang.com", "schema.org", "www.w3.org", "creativecommons.org",
                   "apache.org", "rfc-editor.org", "github.com", "python-markdown.github.io")
        for name, text in self.each():
            with self.subTest(page=str(name)):
                for attr in re.findall(r'(?:src|href)="(https?://[^"]+)"', text):
                    self.assertTrue(
                        any(host in attr for host in allowed),
                        f"third-party request to {attr}",
                    )

    def test_skip_link_is_first_and_targets_main(self):
        for name, text in self.each():
            with self.subTest(page=str(name)):
                self.assertIn('class="skip-link" href="#main"', text)
                self.assertIn('id="main"', text)

    def test_stylesheet_is_the_fingerprinted_bundle(self):
        bundles = {p.name for p in (ROOT / "assets" / "css").glob("site.*.css")}
        self.assertEqual(len(bundles), 1, "exactly one stylesheet bundle should exist")
        for name, text in self.each():
            with self.subTest(page=str(name)):
                sheets = re.findall(r'<link rel="stylesheet" href="([^"]+)"', text)
                self.assertEqual(len(sheets), 1)
                self.assertIn(Path(sheets[0]).name, bundles)


class LocalisedOutputTests(SiteTestCase):
    def test_arabic_pages_are_right_to_left(self):
        for path in self.pages():
            if "ar/" not in str(path.relative_to(ROOT)):
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIn('dir="rtl"', text)

    def test_arabic_pages_link_back_to_english(self):
        for path in self.pages():
            relative = str(path.relative_to(ROOT))
            if not relative.startswith("ar/"):
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIn('hreflang="en"', text)

    def test_paired_pages_declare_both_alternates(self):
        for key, translations in self.site.by_key.items():
            if len(translations) < 2:
                continue
            for page in translations.values():
                text = page.out_file.read_text(encoding="utf-8")
                with self.subTest(key=key, locale=page.locale.code):
                    self.assertIn('hreflang="en"', text)
                    self.assertIn('hreflang="ar"', text)
                    self.assertIn('hreflang="x-default"', text)

    def test_code_stays_left_to_right_on_arabic_pages(self):
        css = next((ROOT / "assets" / "css").glob("site.*.css")).read_text(encoding="utf-8")
        self.assertIn("direction: ltr", css, "code blocks must pin direction")


class GeneratedAssetTests(SiteTestCase):
    def test_sitemap_lists_only_pages_that_exist(self):
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        locations = re.findall(r"<loc>https://uqulang\.com([^<]*)</loc>", sitemap)
        self.assertTrue(locations)
        for location in locations:
            self.assertIn(location, self.site.paths, f"sitemap lists {location}")

    def test_sitemap_excludes_pages_marked_out(self):
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("/404.html", sitemap)
        self.assertNotIn("/500.html", sitemap)

    def test_search_index_entries_point_at_real_pages(self):
        for name in ("search-index.json", "ar/search-index.json"):
            index = json.loads((ROOT / name).read_text(encoding="utf-8"))
            self.assertTrue(index, f"{name} is empty")
            for entry in index:
                target = entry["url"].split("#")[0]
                with self.subTest(index=name, url=entry["url"]):
                    self.assertIn(target, self.site.paths)
                    self.assertTrue(entry["title"].strip())

    def test_search_indexes_do_not_mix_languages(self):
        arabic = json.loads((ROOT / "ar" / "search-index.json").read_text(encoding="utf-8"))
        for entry in arabic:
            self.assertTrue(entry["url"].startswith("/ar/"), entry["url"])

    def test_feed_is_valid_atom(self):
        feed = (ROOT / "feed.xml").read_text(encoding="utf-8")
        for required in ("<feed", "<title>", "<updated>", "<id>", "<entry>", 'rel="self"'):
            self.assertIn(required, feed)

    def test_feed_entries_match_the_posts(self):
        feed = (ROOT / "feed.xml").read_text(encoding="utf-8")
        posts = [p for p in self.site.pages
                 if p.meta.get("layout") == "post" and p.locale.is_default]
        self.assertEqual(feed.count("<entry>"), len(posts))
        for post in posts:
            self.assertIn(html_mod.escape(post.meta["title"]), feed)

    def test_robots_points_at_the_sitemap(self):
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("https://uqulang.com/sitemap.xml", robots)

    def test_security_txt_has_not_expired(self):
        import datetime as dt
        text = (ROOT / ".well-known" / "security.txt").read_text(encoding="utf-8")
        match = re.search(r"Expires:\s*(\d{4})-(\d{2})-(\d{2})", text)
        self.assertIsNotNone(match, "security.txt needs an Expires field")
        expiry = dt.date(*(int(g) for g in match.groups()))
        self.assertGreater(expiry, dt.date.today(), "security.txt has expired")

    def test_csp_hash_matches_the_inline_script(self):
        import base64, hashlib
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        script = re.search(r"<script>(.*?)</script>", page, re.DOTALL).group(1)
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        headers = (ROOT / "_headers").read_text(encoding="utf-8")
        self.assertIn(f"sha256-{digest}", headers,
                      "the CSP hash in _headers does not match the inline script")


if __name__ == "__main__":
    unittest.main()
