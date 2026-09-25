# Placeholders to replace before launch

uqulang is a commercial product licensed to universities — the site says so
throughout, and there are no open-source claims, no public repository links and
no downloads without a licence key.

I do not have the real syntax, version numbers, URLs, prices or measurements, so
every invented value is listed here. Nothing below is presented on the site as a
verified fact, but all of it needs your review before launch.

## 1. Destinations — four constants, one edit each

All defined at the top of `tools/build.py`:

```python
SITE_URL      = "https://uqulang.com"           # canonical URLs, sitemap, Open Graph
PORTAL_URL    = "https://portal.uqulang.com"    # licence portal + downloads
SUPPORT_URL   = "https://support.uqulang.com"   # ticketed support for licensees
CONTACT_EMAIL = "universities@uqulang.com"      # licence enquiries
```

Change them there and run `python3 tools/build.py` — every link on every page
updates. `BASE` in the same file handles a sub-path deploy.

I moved the domain from `.org` to `.com` because `.org` reads as non-commercial.
Change it back in one line if you own the other one.

## 2. Language syntax — invented, coherent, replaceable

Every code sample is my invention, internally consistent in a Swift + C style:
`module` / `import` / `pub`, `func`, `let` / `var`, `struct`, `enum` with
payloads, `trait` / `impl`, `?T` optionals, typed `throws`, `defer`, `move`,
`extern "C"`, `@attributes`, and `test` blocks.

Samples live in `src/pages/**/*.page.html` inside `<!--code … --> … <!--/code-->`
blocks — raw source, escaped at build time. Replace the code, rebuild, done.

Highlighting keywords and builtin types are in exactly one place:
`assets/js/lang/grammars.js` (`UQULANG_KEYWORDS`, `UQULANG_TYPES`).

## 3. Product facts I invented

| Placeholder | Where | Note |
| --- | --- | --- |
| `0.1.0` | home, install, docs | Current release number |
| `UQU-XXXX-XXXX-XXXX` | install | Licence key format |
| `uqu licence activate` / `--offline licence.jwt` | install, CLI | Activation commands and the offline activation file |
| `get.uqulang.com/install.sh`, `install.ps1` | home, install, ar | You must actually host these |
| `brew install uqulang`, `winget install uqulang.uqu` | install | Only if you publish those packages |
| `King Example University` | install (`uqu doctor` output) | Sample licensee name |
| Support response targets (4 h / 1 d / 3 d / 5 d) | universities | **Contractual** — confirm before publishing |
| "Unlimited seats", version pinning, starter kit, faculty training | universities | The licence contents I assumed |
| Sunday–Thursday, Arabia Standard Time | universities | Support hours |
| Roadmap 0.1 → 1.0 | universities | Release contents and order |
| Editor support table | install | Marked "Preview" — confirm |

**There is no pricing anywhere on the site.** Enquiries route to email. If you
want a published price list or a quote form, that is a page to add — and a form
needs a backend, which this site deliberately does not have.

## 4. Content that speaks for the company

- **`src/pages/blog/announcing-uqulang.page.html`** — a complete launch post
  dated 26 September 2026. Read it line by line.
- **`src/pages/universities.page.html`** — licence contents, support targets,
  evaluation terms, trademark policy. This is the page a procurement officer
  will read most carefully.
- **Files referenced but not written**: `install.sh`, `install.ps1`, and
  whatever the licence portal and support portal actually are.

## 5. Benchmarks — deliberately empty

The performance table on the home page contains `—` in every cell, with a note
saying numbers are published only when a licensee can reproduce them on their
own machines. That is an editorial position, not a stub to fill with guesses.
Fill it from a real harness, or delete the section.

## 6. Hijri dates

Blog dates show Hijri alongside Gregorian, converted by the tabular (Kuwaiti)
algorithm in `tools/build.py`. That is the standard civil approximation and can
differ from the **Umm al-Qura** calendar by one day. Check each published date
against Umm al-Qura, or drop the `{{hijri:…}}` macro from the post.

## 7. Security header

`_headers` already carries the correct CSP hash for the one inline script (the
theme-flash guard in `<head>`). If you edit that script, recompute it:

```bash
python3 tools/csp_hash.py
```

and paste the result into `script-src` in `_headers`.

## 8. Arabic

`/ar/` is a full Arabic RTL home page; the rest of the site is English and the
Arabic page says so in a callout. Translations are mine and should be reviewed
by a native speaker, particularly the technical vocabulary and the licensing
wording.
