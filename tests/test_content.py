"""Markdown conversion, code blocks, front matter and dates."""
from __future__ import annotations

import unittest
from pathlib import Path

from .context import build, make_locale

SOURCE = Path("test.md")


class CodeBlockTests(unittest.TestCase):
    def setUp(self):
        self.renderer = build.ContentRenderer(make_locale())

    def test_escapes_html_in_code(self):
        out = self.renderer.expand_code_blocks(
            '<!--code lang="text"-->\n<script>alert(1)</script>\n<!--/code-->'
        )
        self.assertIn("&lt;script&gt;", out)
        self.assertNotIn("<script>alert", out)

    def test_keeps_the_filename_label(self):
        out = self.renderer.expand_code_blocks(
            '<!--code lang="uqulang" file="main.uqu"-->\nfunc main() {}\n<!--/code-->'
        )
        self.assertIn(">main.uqu<", out)

    def test_copy_button_can_be_suppressed(self):
        out = self.renderer.expand_code_blocks(
            '<!--code lang="text" copy="false"-->\nx\n<!--/code-->'
        )
        self.assertNotIn("data-code-copy", out)

    def test_copy_label_is_localised(self):
        arabic = build.ContentRenderer(make_locale("ar", strings={"copy": "نسخ"}))
        out = arabic.expand_code_blocks('<!--code lang="text"-->\nx\n<!--/code-->')
        self.assertIn("نسخ", out)

    def test_language_reaches_the_highlighter(self):
        out = self.renderer.expand_code_blocks('<!--code lang="shell"-->\n$ ls\n<!--/code-->')
        self.assertIn('data-lang="shell"', out)

    def test_pre_is_focusable_for_keyboard_scrolling(self):
        out = self.renderer.expand_code_blocks('<!--code lang="text"-->\nx\n<!--/code-->')
        self.assertIn('<pre tabindex="0">', out)


class MarkdownTests(unittest.TestCase):
    def setUp(self):
        self.renderer = build.ContentRenderer(make_locale())

    def render(self, text: str) -> str:
        return self.renderer.markdown(text, SOURCE)

    def test_fenced_code_becomes_a_code_block(self):
        out = self.render("```uqulang\nfunc main() {}\n```")
        self.assertIn('class="code-block"', out)
        self.assertIn('data-lang="uqulang"', out)

    def test_code_block_is_not_wrapped_in_a_paragraph(self):
        """Markdown wraps a stray token in <p>; the substitution must undo it."""
        out = self.render("Before.\n\n```text\nx\n```\n\nAfter.")
        self.assertNotIn('<p><div class="code-block"', out)
        self.assertNotIn("</div></p>", out)

    def test_fence_attributes_carry_the_filename(self):
        out = self.render('```uqulang file="hello.uqu"\nfunc main() {}\n```')
        self.assertIn(">hello.uqu<", out)

    def test_fenced_code_is_escaped(self):
        out = self.render("```text\n<b>not bold</b>\n```")
        self.assertIn("&lt;b&gt;", out)

    def test_note_admonition_becomes_a_callout(self):
        out = self.render("> [!NOTE]\n> Worth knowing.")
        self.assertIn("callout--note", out)
        self.assertIn("Worth knowing.", out)

    def test_warning_admonition_uses_the_warning_style(self):
        out = self.render("> [!WARNING]\n> Careful.")
        self.assertIn("callout--warn", out)

    def test_admonition_body_is_markdown(self):
        out = self.render("> [!NOTE]\n> A [link](/docs/) and `code`.")
        self.assertIn('href="/docs/"', out)
        self.assertIn("<code>code</code>", out)

    def test_tables_are_wrapped_for_small_screens(self):
        out = self.render("| a | b |\n| --- | --- |\n| 1 | 2 |")
        self.assertIn('class="table-wrap"', out)
        self.assertIn("<table>", out)

    def test_explicit_heading_ids_are_preserved(self):
        out = self.render("## Memory and ownership {#memory}")
        self.assertIn('id="memory"', out)

    def test_headings_get_an_id_even_without_one(self):
        out = self.render("## Automatic heading")
        self.assertIn('id="automatic-heading"', out)

    def test_raw_html_passes_through(self):
        out = self.render('<div class="grid grid--2">\n  <p>kept</p>\n</div>')
        self.assertIn('class="grid grid--2"', out)

    def test_ordinary_prose_is_a_paragraph(self):
        self.assertIn("<p>Hello.</p>", self.render("Hello."))


class FrontMatterTests(unittest.TestCase):
    def parse(self, text: str):
        return build.Site._front_matter(text, SOURCE)

    def test_reads_scalar_values(self):
        meta, body = self.parse("---\ntitle: A page\n---\n\nBody.")
        self.assertEqual(meta["title"], "A page")
        self.assertEqual(body.strip(), "Body.")

    def test_parses_json_shaped_values(self):
        meta, _ = self.parse('---\nnext: {"title": "T", "path": "/p/"}\n---\n\n')
        self.assertEqual(meta["next"]["path"], "/p/")

    def test_parses_booleans_and_numbers(self):
        meta, _ = self.parse("---\nsearch: false\norder: 3\n---\n\n")
        self.assertIs(meta["search"], False)
        self.assertEqual(meta["order"], 3)

    def test_parses_lists(self):
        meta, _ = self.parse('---\nbreadcrumb: [["Docs", "/docs/"]]\n---\n\n')
        self.assertEqual(meta["breadcrumb"], [["Docs", "/docs/"]])

    def test_ignores_comments_and_blank_lines(self):
        meta, _ = self.parse("---\n# a comment\n\ntitle: T\n---\n\n")
        self.assertEqual(meta, {"title": "T"})

    def test_a_value_may_contain_a_colon(self):
        meta, _ = self.parse("---\ntitle: E0101: use of moved value\n---\n\n")
        self.assertEqual(meta["title"], "E0101: use of moved value")

    def test_missing_block_is_an_error(self):
        with self.assertRaises(SystemExit):
            self.parse("No front matter here.")

    def test_a_line_without_a_colon_is_an_error(self):
        with self.assertRaises(SystemExit) as caught:
            self.parse("---\nbroken line\n---\n\n")
        self.assertIn("key: value", str(caught.exception))


class HijriTests(unittest.TestCase):
    def test_known_conversions(self):
        # 1448 AH begins mid-June 2026 in the tabular calendar.
        self.assertEqual(build.to_hijri(2026, 6, 17), (1448, 1, 1))
        self.assertEqual(build.to_hijri(2026, 9, 26)[0], 1448)

    def test_english_formatting(self):
        self.assertEqual(build.format_hijri(2026, 6, 17, "en"), "1 Muharram 1448 AH")

    def test_arabic_formatting(self):
        self.assertEqual(build.format_hijri(2026, 6, 17, "ar"), "1 محرم 1448هـ")

    def test_unknown_locale_falls_back_to_english_month_names(self):
        self.assertIn("Muharram", build.format_hijri(2026, 6, 17, "de"))

    def test_the_calendar_advances_monotonically(self):
        import datetime as dt
        previous = None
        day = dt.date(2026, 1, 1)
        while day < dt.date(2028, 1, 1):
            current = build.to_hijri(day.year, day.month, day.day)
            if previous is not None:
                self.assertGreaterEqual(current, previous, f"went backwards at {day}")
            previous = current
            day += dt.timedelta(days=1)


if __name__ == "__main__":
    unittest.main()
