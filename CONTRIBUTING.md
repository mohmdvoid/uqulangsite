# Contributing to uqulang.com

Thank you for helping improve the uqulang website and documentation.

**Scope.** This repository is the website and its documentation. The uqulang
compiler and toolchain are licensed commercially to universities and are not in
this repository. Bugs in the *compiler* go to your institution's support
contacts; everything about the *website and docs* belongs here.

## What is most useful

In rough order of value:

1. **Documentation that was wrong or missing.** If you had to work something out
   by experiment, that is a docs bug.
2. **Code samples that do not compile** against the current release.
3. **Unclear explanations.** "I read this three times" is a valid report.
4. **Accessibility and rendering problems** — keyboard traps, contrast, a layout
   that breaks at your window size, a screen reader announcing nonsense.
5. **Arabic translation.** The `/ar/` pages were not written by a native
   speaker. Corrections to terminology and phrasing are especially welcome.
6. **Broken links and stale version numbers.**

## Running it locally

You need **Python 3.9 or newer**. Nothing else — no Node, no Ruby, no package
install step.

```bash
git clone <this repository>
cd uqulangsite
make serve          # builds, then serves http://localhost:4173
```

Other targets:

```bash
make build          # regenerate the site from src/
make check          # verify generated output and links (what CI runs)
make clean          # remove generated files
```

If you do not have `make`, the equivalents are `python3 tools/build.py`,
`python3 tools/check_links.py` and `python3 -m http.server 4173`.

## How the site is put together

Content lives in `src/`. The `.html` files in the repository root and in
`docs/`, `install/`, `blog/` and so on are **generated** — do not edit them, your
change will be overwritten and CI will reject the pull request.

```
src/pages/*.page.html   one file per page: JSON front matter, then the body
src/css/*.css           stylesheet layers, concatenated at build time
src/_layout.html        the shared shell: head, header, footer
tools/build.py          the generator
```

### Adding a page

Create `src/pages/my-page.page.html`:

```html
<!--meta
{
  "title": "My page",
  "description": "At least fifty characters, because this is the search result text.",
  "path": "/my-page/",
  "nav": "docs"
}
meta-->

<div class="container container--narrow page-head">
  <h1>My page</h1>
</div>
```

Then run `make build`. The sitemap and the documentation search index update
themselves. To put the page in the docs sidebar, add it to `DOCS_TREE` in
`tools/build.py`.

### Adding a code sample

Write raw source — escaping, the copy button and syntax highlighting are
generated:

```html
<!--code file="example.uqu" lang="uqulang"-->
func main() {
    io.println("Hello")
}
<!--/code-->
```

Languages: `uqulang`, `shell`, `json`, `text`. Keep lines under about 72
characters so samples do not need horizontal scrolling on a laptop.

The uqulang keyword and type lists used by the highlighter are in one place:
`assets/js/lang/grammars.js`.

### Writing style

- British or American spelling is fine; be consistent within a page.
- Say what the compiler does, not what it will do one day. Anything unshipped is
  labelled **planned** in place.
- No performance claims without a reproducible measurement. The benchmark table
  on the home page stays empty until there are real numbers.
- Prefer a short sentence to a clever one. Many readers are students, and many
  are reading in their second language.

## Before you open a pull request

```bash
make check
```

This fails if the generated output does not match `src/`, if a link is broken,
if a heading level is skipped, if a page has no description, or if an `<img>`
has no `alt`. CI runs exactly the same command.

Please also check your change at a narrow window (around 375px wide) and in both
light and dark themes. The theme toggle is in the header.

## Pull requests

- One topic per pull request. A typo fix and a redesign do not belong together.
- Describe what a reader can now do that they could not before.
- Screenshots for anything visual, in both themes.
- Translation changes: say which language you are a native speaker of.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
