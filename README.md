# uqulang.com

The website for uqulang, a compiled systems language licensed to universities
and research institutions: home, installation, documentation, campus licensing
and blog, in English with an Arabic (RTL) home page.

Plain static HTML, CSS and ES modules. **No framework, no npm, no build step at
deploy time.** The `.html` files in this repository are the deployable artifact —
upload them and you are live.

## Why it is built this way

At 1M+ visitors the failure modes that matter are operational, not aesthetic:

- **Nothing to install to deploy.** The generated HTML is committed, so shipping
  is a file copy. The build has exactly one dependency (Markdown, pinned in
  `requirements.txt`) and it never runs on the server.
- **One CDN hit per page, one for CSS.** No hydration, no client-side router, no
  JS execution before text is on screen. The stylesheet ships as a single
  content-hashed file served `immutable`, so repeat visits never revalidate it.
- **No third-party requests.** System font stack, self-hosted SVG, no analytics
  by default, no Google Fonts. Nothing to leak, nothing to rate-limit you.
- **Nothing to leak about customers.** No forms, no backend, no database — the
  licensing page routes enquiries to email and the support portal.
- **It degrades.** With JavaScript disabled every page is complete: tabs show all
  panels with headings, code is readable (unhighlighted), navigation is links.

Swift, Go, Zig and Rust all ship their language sites as generated static HTML
for the same reasons.

## Layout

```
src/pages/**/*.md         docs and blog posts: Markdown + front matter
src/pages/*.page.html     marketing pages: JSON front matter + HTML body
src/css/*.css             stylesheet layers (edit these)
src/_layout.html          the shared shell (head, header, footer)
tools/build.py            generator: pages + stylesheet + sitemap + search index
tools/check_links.py      links, duplicate ids, heading order, metadata
tools/csp_hash.py         CSP hash for the one inline script

assets/css/site.<hash>.css  ← generated bundle, served immutable
assets/js/core/           Component, App, EventBus, Store
assets/js/components/     ThemeToggle, NavDrawer, TabGroup, CodeBlock,
                          PlatformDetector, TableOfContents, HeadingAnchors,
                          DocsSearch
assets/js/lang/           syntax grammars + highlighter
assets/img/               mark, favicon, app icons, Open Graph image

index.html, install/, docs/, universities/, blog/, ar/, 404.html  ← generated
sitemap.xml, search-index.json                                  ← generated
```

## Working on it

Python 3.9+ and nothing else — no Node, no Ruby.

```bash
make setup     # once: .venv with the single build dependency
make serve     # build, then http://localhost:4173
make check     # what CI runs: output freshness, links, headings, metadata
make build     # regenerate only
```

Contributors: see [CONTRIBUTING.md](CONTRIBUTING.md).

Edit `src/`, never the generated files — `build.py --check` fails in CI if the
output does not match the sources. Generated and committed: every `.html`,
`assets/css/site.<hash>.css`, `sitemap.xml` and `search-index.json`.

The inline theme script in every `<head>` is generated from
`assets/js/theme-init.js`, so it exists in exactly one place. Change it and
re-run `tools/csp_hash.py`, then update `_headers`.

### Adding a page

1. Create `src/pages/my-page.page.html` starting with a meta block:

   ```html
   <!--meta
   { "title": "My page", "description": "…50+ characters…", "path": "/my-page/", "nav": "docs" }
   meta-->
   ```

2. Add it to `DOCS_TREE` in `tools/build.py` if it belongs in the docs sidebar.
3. Run the build. The sitemap and the docs search index update themselves.

### Adding a code sample

```html
<!--code file="example.uqu" lang="uqulang"-->
func main() { io.println("Hello") }
<!--/code-->
```

Write raw source — escaping, the copy button and the syntax markup are generated.
Languages: `uqulang`, `shell`, `json`, `text`.

## Design system

All colour, type, spacing and motion values live in `assets/css/tokens.css`.
Brand: palm green `#0E7A57` (light) / `#35C48E` (dark), desert gold accent, with
a mark drawn from ع — the first letter of *ʿaql* (عقل), "mind" — opening into a
compiler arrow. Light and dark themes are both first-class; dark follows the OS
unless the visitor chooses otherwise.

Saudi detail is deliberately quiet: a sadu-weave band above the footer
(`assets/img/sadu.svg`, applied as a CSS mask so it takes the theme colour), the
ع etymology in the footer, Hijri dates beside Gregorian ones on the blog, and
the Arabic RTL home page. Nothing else is themed — the rest is the same
restrained layout.

Every stylesheet uses CSS logical properties, so `dir="rtl"` mirrors the entire
layout with no RTL-specific stylesheet. `/ar/` is the proof.

## Languages

A page's locale and URL both come from where its source sits — `src/pages/ar/docs/index.md`
is Arabic and serves `/ar/docs/`. Files that share a path across locales are
translations of each other, and from that pairing the build derives the
`hreflang` alternates, the language switcher, the per-locale search index, and
whether a link should resolve to a translated page or fall back to English.

Interface strings, navigation, footer and the docs sidebar live in
`src/i18n/<code>.json`. Adding a language is one JSON file plus the pages you
choose to translate; `tools/build.py` does not change.

## JavaScript architecture

`Component` is the base class: `static selector`, `mount()`, tracked listeners,
`destroy()`. `App` finds and mounts each registered component **inside its own
try/catch**, so one broken widget can never take a page down; failures land in
`app.failures` and the console. Components talk through an `EventBus`, and
`Store` wraps `localStorage` so blocked storage degrades to "no preference
remembered" instead of an exception.

## Deploying

Any static host. Serve from the domain root, or set `BASE` in `tools/build.py`
for a sub-path deploy.

- **Cloudflare Pages / Netlify** — `_headers` is already in the right format.
- **nginx** — `root /srv/uqulang.com;` plus `try_files $uri $uri/index.html =404;`
  and `error_page 404 /404.html;`. Copy the headers from `_headers` into
  `add_header` directives.
- **S3 + CloudFront** — index document `index.html`, error document `404.html`.

`_headers` sets CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` and
`Permissions-Policy`. The CSP allows exactly one inline script by hash; re-run
`tools/csp_hash.py` if that script ever changes.

Caching is conservative on purpose: HTML revalidates every request, assets cache
for an hour. Once asset filenames are fingerprinted, raise `/assets/*` to
`max-age=31536000, immutable`.

## Licensing

Code (generator, CSS, JavaScript) is Apache-2.0; content (documentation, posts)
is CC-BY-4.0; the name and mark are trademarks covered by neither. See
[LICENSE.md](LICENSE.md). The compiler itself is commercial and is not in this
repository.

## Before launch

Read [PLACEHOLDERS.md](PLACEHOLDERS.md). It lists every invented value on the
site — syntax, version numbers, install commands, URLs and the deliberately
empty benchmark table.
