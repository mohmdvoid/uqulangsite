"""The deployment step: minification safety, compression, and the budget.

The minifier is the only thing in this project that rewrites finished HTML, so
it gets the most adversarial tests here. A minifier that changes what a page
says is worse than no minifier at all.
"""
from __future__ import annotations

import re
import unittest

from .context import ROOT, postprocess


def visible_text(markup: str) -> list:
    body = re.search(r"<body[^>]*>(.*)</body>", markup, re.DOTALL)
    markup = body.group(1) if body else markup
    markup = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", "\n", markup).split()


class MinifierSafetyTests(unittest.TestCase):
    def test_preserves_whitespace_inside_pre(self):
        source = "<div>\n  <pre>line one\n    indented\n\nblank above</pre>\n</div>"
        out = postprocess.minify_html(source)
        self.assertIn("line one\n    indented\n\nblank above", out)

    def test_preserves_code_content_exactly(self):
        source = '<pre><code>func main() {\n    io.println("x")\n}</code></pre>'
        out = postprocess.minify_html(source)
        self.assertIn('func main() {\n    io.println("x")\n}', out)

    def test_preserves_textarea_content(self):
        source = "<textarea>\n  keep   this\n</textarea>"
        self.assertIn("\n  keep   this\n", postprocess.minify_html(source))

    def test_preserves_script_bodies(self):
        source = "<script>var a = 1;   var b = 2;</script>"
        self.assertIn("var a = 1;   var b = 2;", postprocess.minify_html(source))

    def test_keeps_a_single_space_between_inline_elements(self):
        """"<b>a</b> <i>b</i>" must not become "ab"."""
        out = postprocess.minify_html("<p><b>a</b> <i>b</i></p>")
        self.assertIn("</b> <i>", out)

    def test_collapses_formatting_whitespace_between_blocks(self):
        out = postprocess.minify_html("<div>\n\n    <p>x</p>\n\n</div>")
        self.assertIn("<div><p>x</p></div>", out)

    def test_removes_comments(self):
        self.assertNotIn("secret", postprocess.minify_html("<p>x</p><!-- secret -->"))

    def test_keeps_conditional_comments(self):
        source = "<!--[if IE]><p>old</p><![endif]-->"
        self.assertIn("[if IE]", postprocess.minify_html(source))

    def test_does_not_touch_arabic_text(self):
        source = "<p>مرحباً بالعالم</p>"
        self.assertIn("مرحباً بالعالم", postprocess.minify_html(source))

    def test_is_idempotent(self):
        source = "<div>\n  <p>x</p>\n</div>"
        once = postprocess.minify_html(source)
        self.assertEqual(once, postprocess.minify_html(once))


class MinifiedSiteTests(unittest.TestCase):
    """Run the minifier over every real page and compare the visible text."""

    def test_every_page_says_exactly_the_same_thing(self):
        pages = [p for p in ROOT.rglob("*.html")
                 if not any(part in {"src", "tools", "dist", "deploy", "reports",
                                     ".git", ".github", ".venv", "node_modules"}
                            for part in p.relative_to(ROOT).parts)]
        self.assertGreater(len(pages), 10, "expected the built site to be present")

        for page in pages:
            source = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertEqual(
                    visible_text(source),
                    visible_text(postprocess.minify_html(source)),
                    "minification changed the page's visible text",
                )

    def test_code_blocks_survive_byte_for_byte(self):
        page = ROOT / "docs" / "tour" / "index.html"
        source = page.read_text(encoding="utf-8")
        pattern = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL)
        self.assertEqual(
            pattern.findall(source),
            pattern.findall(postprocess.minify_html(source)),
        )


class DeploymentContentsTests(unittest.TestCase):
    """What the deployment directory must and must not contain."""

    def test_sources_and_tooling_are_excluded(self):
        for name in ("src/pages/index.page.html", "tools/build.py", "README.md",
                     "PLACEHOLDERS.md", "deploy/nginx.conf", "Makefile"):
            with self.subTest(path=name):
                self.assertFalse(postprocess.deployable(ROOT / name), f"{name} would be published")

    def test_the_site_itself_is_included(self):
        for name in ("index.html", "docs/tour/index.html", "robots.txt",
                     "sitemap.xml", "feed.xml", "manifest.webmanifest",
                     ".well-known/security.txt"):
            with self.subTest(path=name):
                self.assertTrue(postprocess.deployable(ROOT / name), f"{name} would be withheld")

    def test_budget_limits_are_sane(self):
        self.assertLessEqual(postprocess.BUDGET["html_gzip"], 50 * 1024)
        self.assertLessEqual(
            postprocess.BUDGET["page_total_gzip"], 150 * 1024,
            "a static page budget above 150 KB is not a budget",
        )


if __name__ == "__main__":
    unittest.main()
