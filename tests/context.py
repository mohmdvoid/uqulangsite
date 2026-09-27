"""Shared fixtures: import the tools under test, and build the site once."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build  # noqa: E402  (path set above)
import postprocess  # noqa: E402


# Directories that contain HTML which is not part of the site: sources, build
# tooling, the deployment copy, and the quality report.
NOT_THE_SITE = {"src", "tools", "dist", "deploy", "reports", ".git", ".github",
                ".venv", "node_modules"}


def make_locale(code="en", prefix="", is_default=True, strings=None, **kwargs) -> "build.Locale":
    """A locale built by hand, so a unit test does not need the real data files."""
    defaults = {
        "copy": "Copy", "copy_code": "Copy code", "previous": "Previous", "next": "Next",
        "pagination": "Pagination", "documentation": "Documentation",
        "on_this_page": "On this page", "search_label": "Search", "search_results": "Results",
        "search_placeholder": "Search…", "version": "Version", "release": "Release",
        "outdated_docs": "Reading {version}, current is {current}.",
        "read_current": "Read current", "no_posts": "No posts.", "no_errors": "No errors.",
        "error_code": "Code", "error_meaning": "Meaning", "error_category": "Category",
    }
    defaults.update(strings or {})
    return build.Locale(
        code=code,
        name=kwargs.get("name", code),
        dir=kwargs.get("dir", "ltr"),
        prefix=prefix,
        is_default=is_default,
        order=kwargs.get("order", 1),
        catalog=build.Catalog(defaults),
        nav=[], footer=[], docs_tree=[],
    )


class SiteTestCase(unittest.TestCase):
    """Base class for tests that read the generated site.

    The site is built once for the whole suite rather than per test: these are
    assertions about the committed output, which is what actually ships.
    """

    site: "build.Site"

    @classmethod
    def setUpClass(cls) -> None:
        cls.site = build.Site().collect()

    @staticmethod
    def pages() -> list:
        return sorted(p for p in ROOT.rglob("*.html")
                      if not any(part in NOT_THE_SITE for part in p.relative_to(ROOT).parts))
