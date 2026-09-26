# Deploying uqulang.com

The site is static files. Deploying is copying `dist/` somewhere that serves it
over HTTPS. Everything below is about doing that correctly rather than merely
doing it.

```bash
make dist        # build, verify, minify, precompress, enforce the budget
```

`dist/` then holds the whole site plus a `.gz` — and a `.br` if the optional
`brotli` package is installed — next to every text file, so the edge never
compresses anything at request time.

## Choosing a host

Any static host works. The differences that matter:

| Host | Headers from | Notes |
| --- | --- | --- |
| Cloudflare Pages | `_headers`, `_redirects` | Serves `.br` automatically; largest free edge network |
| Netlify | `_headers`, `_redirects`, `netlify.toml` | Build config included; Lighthouse plugin wired up |
| Vercel | `vercel.json` | `cleanUrls` and `trailingSlash` already set |
| S3 + CloudFront | CloudFront behaviours | **`_headers` is ignored** — replicate it, see below |
| Self-hosted nginx | `deploy/nginx.conf` | Complete config, including precompressed serving |
| Docker | `deploy/Dockerfile` | Builds and serves; `docker build -f deploy/Dockerfile .` |

## The one thing that must be right

Two cache lifetimes, and they are not the same:

- **HTML: `max-age=0, must-revalidate`.** A deploy has to be visible on the
  next request. HTML is small and revalidation is a 304.
- **`/assets/css/*`: `max-age=31536000, immutable`.** The filename contains a
  hash of the contents, so a change ships under a new name and the old one can
  be cached for a year.

Get this backwards and either deploys do not appear, or visitors keep a stale
stylesheet. `/assets/js/*` revalidates because ES module specifiers are literal
paths and are therefore not fingerprinted.

On a host that ignores `_headers` — plain S3 is the common case — replicate it
in the CDN's own behaviour rules before going live. Everything else degrades
gracefully; this does not.

## Checklist before the first deploy

- [ ] DNS for `uqulang.com` and `www.uqulang.com`, with `www` redirecting
- [ ] TLS certificate, and HSTS only after you are sure about the subdomains
- [ ] Cache headers per the table above
- [ ] `404.html` wired to 404 responses, `500.html` to 5xx
- [ ] `get.uqulang.com` actually serving `install.sh` and `install.ps1`
- [ ] Content-Security-Policy hash matches: `python3 tools/csp_hash.py`
- [ ] `PLACEHOLDERS.md` reviewed — invented facts are still on the pages

## Rollback

Each CI run uploads `dist/` as an artifact with a seven-day retention. A
rollback is redeploying an earlier artifact; nothing needs rebuilding, and the
build is reproducible from any commit in any case.

## What a deploy does not include

`src/`, `tools/`, `deploy/`, `.github/` and the repository's own documentation
are excluded from `dist/` by `tools/postprocess.py`. If you deploy the
repository root instead, those become publicly readable.
