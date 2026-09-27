"""Locale resolution, translation catalogues and their failure modes."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from .context import ROOT, build, make_locale


class CatalogTests(unittest.TestCase):
    def test_returns_the_string(self):
        catalog = build.Catalog({"greeting": "Hello"})
        self.assertEqual(catalog.get("greeting"), "Hello")

    def test_interpolates_parameters(self):
        catalog = build.Catalog({"legal": "© {year} uqulang"})
        self.assertEqual(catalog.get("legal", year=2026), "© 2026 uqulang")

    def test_falls_back_to_the_default_locale(self):
        base = build.Catalog({"previous": "Previous"})
        arabic = build.Catalog({}, fallback=base)
        self.assertEqual(arabic.get("previous"), "Previous")

    def test_prefers_its_own_string_over_the_fallback(self):
        base = build.Catalog({"previous": "Previous"})
        arabic = build.Catalog({"previous": "السابق"}, fallback=base)
        self.assertEqual(arabic.get("previous"), "السابق")

    def test_a_key_missing_everywhere_is_an_error(self):
        catalog = build.Catalog({})
        with self.assertRaises(SystemExit) as caught:
            catalog.get("nonexistent")
        self.assertIn("nonexistent", str(caught.exception))

    def test_membership_follows_the_fallback(self):
        catalog = build.Catalog({}, fallback=build.Catalog({"here": "yes"}))
        self.assertIn("here", catalog)
        self.assertNotIn("absent", catalog)


class LocaleTests(unittest.TestCase):
    def test_default_locale_does_not_prefix(self):
        english = make_locale("en", prefix="", is_default=True)
        self.assertEqual(english.localise("/docs/"), "/docs/")
        self.assertEqual(english.home(), "/")

    def test_prefixed_locale_prefixes(self):
        arabic = make_locale("ar", prefix="/ar", is_default=False)
        self.assertEqual(arabic.localise("/docs/"), "/ar/docs/")
        self.assertEqual(arabic.localise("/"), "/ar/")
        self.assertEqual(arabic.home(), "/ar/")

    def test_external_urls_are_left_alone(self):
        arabic = make_locale("ar", prefix="/ar", is_default=False)
        self.assertEqual(arabic.localise("https://example.org"), "https://example.org")

    def test_rtl_is_derived_from_direction(self):
        self.assertTrue(make_locale("ar", dir="rtl").is_rtl)
        self.assertFalse(make_locale("en", dir="ltr").is_rtl)


class LocaliserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, code, **overrides):
        data = {
            "code": code, "name": code, "dir": "ltr", "prefix": "",
            "default": False, "order": 1, "strings": {"a": "b"},
        }
        data.update(overrides)
        (self.dir / f"{code}.json").write_text(json.dumps(data), encoding="utf-8")

    def test_requires_exactly_one_default(self):
        self.write("en", default=True)
        self.write("ar", default=True, prefix="/ar")
        with self.assertRaises(SystemExit) as caught:
            build.Localiser(self.dir)
        self.assertIn("default", str(caught.exception))

    def test_requires_at_least_one_locale(self):
        with self.assertRaises(SystemExit):
            build.Localiser(self.dir)

    def test_rejects_a_shared_prefix(self):
        self.write("en", default=True)
        self.write("ar", prefix="/x")
        self.write("fr", prefix="/x")
        with self.assertRaises(SystemExit) as caught:
            build.Localiser(self.dir)
        self.assertIn("prefix", str(caught.exception))

    def test_unknown_locale_names_the_file_to_create(self):
        self.write("en", default=True)
        localiser = build.Localiser(self.dir)
        with self.assertRaises(SystemExit) as caught:
            localiser["de"]
        self.assertIn("de.json", str(caught.exception))

    def test_locale_comes_from_the_first_path_segment(self):
        self.write("en", default=True)
        self.write("ar", prefix="/ar")
        localiser = build.Localiser(self.dir)
        self.assertEqual(localiser.code_for_source(Path("docs/tour.md")), "en")
        self.assertEqual(localiser.code_for_source(Path("ar/docs/tour.md")), "ar")
        # A directory that merely shares a name with no locale stays default.
        self.assertEqual(localiser.code_for_source(Path("blog/post.md")), "en")


class RealLocaleDataTests(unittest.TestCase):
    """The shipped locale files, not fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.localiser = build.Localiser(ROOT / "src" / "i18n")

    def test_english_is_the_default(self):
        self.assertEqual(self.localiser.default_code, "en")

    def test_arabic_is_right_to_left(self):
        self.assertTrue(self.localiser["ar"].is_rtl)

    def test_every_locale_defines_every_string_the_default_defines(self):
        """A missing key falls back, but silently — so the suite says which."""
        default = self.localiser.default
        base_keys = set(default.catalog._strings)
        for locale in self.localiser.ordered():
            if locale.is_default:
                continue
            missing = base_keys - set(locale.catalog._strings)
            self.assertEqual(
                missing, set(),
                f"{locale.code}.json is missing: {sorted(missing)}",
            )

    def test_no_locale_defines_a_string_the_default_does_not(self):
        default_keys = set(self.localiser.default.catalog._strings)
        for locale in self.localiser.ordered():
            extra = set(locale.catalog._strings) - default_keys
            self.assertEqual(extra, set(), f"{locale.code}.json has orphan keys: {sorted(extra)}")

    def test_navigation_is_parallel_across_locales(self):
        keys = [[item["key"] for item in loc.nav] for loc in self.localiser.ordered()]
        self.assertTrue(all(k == keys[0] for k in keys), "nav keys differ between locales")

    def test_footer_and_sidebar_shapes_match(self):
        shapes = [
            ([len(g["links"]) for g in loc.footer], [len(g["items"]) for g in loc.docs_tree])
            for loc in self.localiser.ordered()
        ]
        self.assertTrue(all(s == shapes[0] for s in shapes), "footer or sidebar shape differs")


if __name__ == "__main__":
    unittest.main()
