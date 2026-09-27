"""URL derivation, cross-locale link resolution and documentation versions."""
from __future__ import annotations

import unittest
from pathlib import Path

from .context import ROOT, build, make_locale, SiteTestCase


class PathDerivationTests(unittest.TestCase):
    def setUp(self):
        self.en = make_locale("en", prefix="", is_default=True)
        self.ar = make_locale("ar", prefix="/ar", is_default=False)

    def derive(self, relative, locale):
        return build.derive_key_and_path(Path(relative), locale, "en")

    def test_home_page(self):
        self.assertEqual(self.derive("index.page.html", self.en), ("index", "/"))

    def test_arabic_home_page(self):
        self.assertEqual(self.derive("ar/index.page.html", self.ar), ("index", "/ar/"))

    def test_section_index(self):
        self.assertEqual(self.derive("docs/index.md", self.en), ("docs/index", "/docs/"))

    def test_nested_page(self):
        self.assertEqual(self.derive("docs/tour.md", self.en), ("docs/tour", "/docs/tour/"))

    def test_deeply_nested_page(self):
        self.assertEqual(
            self.derive("docs/errors/E0101.md", self.en),
            ("docs/errors/E0101", "/docs/errors/E0101/"),
        )

    def test_translation_shares_the_key(self):
        english_key, _ = self.derive("docs/tour.md", self.en)
        arabic_key, arabic_path = self.derive("ar/docs/tour.md", self.ar)
        self.assertEqual(english_key, arabic_key)
        self.assertEqual(arabic_path, "/ar/docs/tour/")

    def test_error_pages_keep_their_extension(self):
        self.assertEqual(self.derive("404.page.html", self.en), ("404", "/404.html"))
        self.assertEqual(self.derive("500.page.html", self.en), ("500", "/500.html"))

    def test_arabic_error_page_is_prefixed(self):
        self.assertEqual(self.derive("ar/404.page.html", self.ar), ("404", "/ar/404.html"))


class LinkResolutionTests(SiteTestCase):
    """The rule that makes partial translation safe."""

    def test_default_locale_paths_are_untouched(self):
        english = self.site.localiser["en"]
        self.assertEqual(self.site.resolve("/docs/tour/", english), "/docs/tour/")

    def test_translated_target_is_localised(self):
        arabic = self.site.localiser["ar"]
        # /ar/docs/ exists, so an Arabic page linking to /docs/ should land there.
        self.assertEqual(self.site.resolve("/docs/", arabic), "/ar/docs/")

    def test_untranslated_target_falls_back_rather_than_404ing(self):
        arabic = self.site.localiser["ar"]
        resolved = self.site.resolve("/docs/tour/", arabic)
        self.assertEqual(resolved, "/docs/tour/")
        self.assertIn(resolved, self.site.paths, "fallback must point at a page that exists")

    def test_fragments_survive_resolution(self):
        arabic = self.site.localiser["ar"]
        self.assertTrue(self.site.resolve("/universities/#contact", arabic).endswith("#contact"))

    def test_external_urls_are_untouched(self):
        arabic = self.site.localiser["ar"]
        for target in ("https://example.org", "mailto:a@b.c", "#anchor"):
            self.assertEqual(self.site.resolve(target, arabic), target)

    def test_every_resolved_internal_link_exists(self):
        """Exhaustive: no locale can produce a link to a page that is not built."""
        for locale in self.site.localiser.ordered():
            for page in self.site.pages:
                for item in locale.nav:
                    resolved = self.site.resolve(item["path"], locale)
                    self.assertIn(resolved, self.site.paths,
                                  f"{locale.code} nav {item['path']} -> {resolved}")


class TranslationPairingTests(SiteTestCase):
    def test_home_pages_are_paired(self):
        translations = self.site.by_key["index"]
        self.assertEqual(set(translations), {"en", "ar"})

    def test_docs_hubs_are_paired(self):
        self.assertEqual(set(self.site.by_key["docs/index"]), {"en", "ar"})

    def test_an_untranslated_page_has_one_entry(self):
        self.assertEqual(set(self.site.by_key["docs/tour"]), {"en"})

    def test_alternates_are_symmetric(self):
        for key, translations in self.site.by_key.items():
            if len(translations) < 2:
                continue
            for page in translations.values():
                self.assertEqual(
                    set(self.site.translations_of(page)), set(translations),
                    f"{key} disagrees about its translations",
                )


class DocVersionTests(unittest.TestCase):
    def setUp(self):
        self.versions = build.DocVersions(ROOT / "src" / "versions.json")
        self.en = make_locale("en", prefix="", is_default=True)
        self.ar = make_locale("ar", prefix="/ar", is_default=False)

    def test_exactly_one_version_is_current(self):
        current = [v for v in self.versions.versions if v.is_current]
        self.assertEqual(len(current), 1)

    def test_the_current_version_owns_the_canonical_prefix(self):
        self.assertEqual(self.versions.current.prefix(self.en), "/docs/")

    def test_an_archived_version_lives_under_its_id(self):
        archived = build.DocVersion(id="0.1", label="0.1", status="archived")
        self.assertEqual(archived.prefix(self.en), "/docs/0.1/")
        self.assertEqual(archived.prefix(self.ar), "/ar/docs/0.1/")

    def test_recognises_a_versioned_url(self):
        versions = build.DocVersions(ROOT / "src" / "versions.json")
        versions.versions.append(build.DocVersion(id="0.0", label="0.0", status="archived"))
        self.assertEqual(versions.version_of("/docs/0.0/tour/").id, "0.0")
        self.assertEqual(versions.version_of("/ar/docs/0.0/tour/").id, "0.0")

    def test_an_unversioned_url_has_no_version(self):
        self.assertIsNone(self.versions.version_of("/docs/tour/"))
        self.assertIsNone(self.versions.version_of("/install/"))


if __name__ == "__main__":
    unittest.main()
