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

You need **Python 3.9 or newer**. Nothing else — no Node, no Ruby.

```bash
git clone <this repository>
cd uqulangsite
make setup          # creates .venv with the one build dependency
make serve          # builds, then serves http://localhost:4173
```

Other targets:

```bash
make build          # regenerate the site from src/
make check          # verify generated output and links (what CI runs)
make clean          # remove generated files
```

The single build dependency is [Markdown][pymd], pinned in `requirements.txt`
and installed into `.venv` by `make setup`. Nothing is installed system-wide,
and the deployed site has no dependencies at all — it is plain HTML, CSS and
JavaScript.

[pymd]: https://python-markdown.github.io/

## How the site is put together

Content lives in `src/`. The `.html` files in the repository root and in
`docs/`, `install/`, `blog/` and so on are **generated** — do not edit them, your
change will be overwritten and CI will reject the pull request.

```
src/pages/**/*.md        documentation and blog posts — write Markdown
src/pages/*.page.html    the layout-heavy marketing pages
src/css/*.css            stylesheet layers, concatenated at build time
src/_layout.html         the shared shell: head, header, footer
tools/build.py           the generator
```

**If you are changing documentation, you are writing Markdown.** The HTML
sources are only for pages built out of cards, tabs and grids.

### Adding a documentation page

Create `src/pages/docs/my-page.md`:

```markdown
---
title: My page
description: At least fifty characters, because this is the search result text.
path: /docs/my-page/
nav: docs
layout: docs
eyebrow: Reference
lead: One sentence under the title.
breadcrumb: [["Docs", "/docs/"]]
prev: {"title": "Getting started", "path": "/docs/getting-started/"}
next: {"title": "Compiler CLI", "path": "/docs/cli/"}
---

## A heading {#a-heading}

Ordinary Markdown. Links are written as plain site paths: [the docs](/docs/).
```

Front matter is `key: value`. A value that looks like JSON is parsed as JSON,
which is how `breadcrumb`, `prev` and `next` work.

Layouts: `docs` (sidebar and on-this-page), `page` (narrow column), `post`
(a blog entry), `raw` (HTML sources, no furniture).

Give every `##` an explicit `{#id}` so that links to it keep working if the
wording changes. Then run `make build` — the sidebar entry comes from
`DOCS_TREE` in `tools/build.py`, and the sitemap and search index update
themselves.

### Adding a blog post

One file: `src/pages/blog/my-post.md` with `layout: post`, a `date:` and a
`kind:`. The blog index builds its own list from the posts, so there is no
second file to keep in step.

### Code samples

Ordinary fenced code blocks. Syntax highlighting, escaping and the copy button
are generated:

````markdown
```uqulang file="example.uqu"
func main() {
    io.println("Hello")
}
```
````

Languages: `uqulang`, `shell`, `json`, `text`. Keep lines under about 72
characters so samples do not need horizontal scrolling on a laptop.

### Callouts

GitHub-style admonitions become the site's callout component:

```markdown
> [!NOTE]
> Worth knowing, but not a warning.

> [!WARNING]
> Something that will bite.
```

### When Markdown is not enough

Raw HTML passes through untouched, so a page can drop into a card grid or a
definition list where prose is not the right shape. Use the classes that already
exist rather than inventing new ones.

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
