---
title: Compiler CLI
description: Reference for the uqu command line: build, run, test, fmt, doc, lsp, doctor, and the flags controlling optimisation, targets and cross-compilation.
path: /docs/cli/
nav: docs
section: Documentation
priority: 0.7
layout: docs
eyebrow: Reference
heading: The <code>uqu</code> command
lead: One binary does the whole job: compile, run, test, format, document and serve the language server. Every subcommand accepts <code>--help</code>.
meta_line: Covers toolchain 0.1.0
breadcrumb: [["Docs", "/docs/"]]
prev: {"title": "Language tour", "path": "/docs/tour/"}
next: {"title": "For universities", "path": "/universities/"}
---

## Synopsis {#synopsis}

```shell
$ uqu <command> [options] [paths]
```

| Command | What it does |
| --- | --- |
| `init` | Create a project in a new or empty directory |
| `build` | Compile to a binary or library in `target/` |
| `run` | Build, then execute, forwarding arguments |
| `test` | Compile and run every `test` block |
| `fmt` | Format source in place; one canonical style |
| `doc` | Generate HTML API documentation from doc comments |
| `check` | Type-check without producing a binary |
| `fix` | Apply mechanical migrations after an upgrade |
| `lsp` | Speak the Language Server Protocol over stdio |
| `doctor` | Report the toolchain, linker and target it can see |

## uqu build {#build}

```shell
$ uqu build --release
$ uqu build --target x86_64-unknown-linux-gnu
$ uqu build --emit asm --out build/
```

<div class="dl-grid">
        <div><dt>--release</dt><dd>Optimise (<code>opt=speed</code>), strip debug info, remove test blocks and debug assertions.</dd></div>
        <div><dt>--opt &lt;level&gt;</dt><dd><code>debug</code>, <code>size</code>, <code>speed</code>. Defaults to <code>debug</code>.</dd></div>
        <div><dt>--target &lt;triple&gt;</dt><dd>Cross-compile. Run <code>uqu targets</code> for the supported list.</dd></div>
        <div><dt>--emit &lt;kind&gt;</dt><dd><code>bin</code>, <code>lib</code>, <code>obj</code>, <code>asm</code>, <code>ir</code>. Useful for inspecting what was generated.</dd></div>
        <div><dt>--static / --dynamic</dt><dd>Link the standard library statically (default) or against a shared object.</dd></div>
        <div><dt>--out &lt;dir&gt;</dt><dd>Output directory. Defaults to <code>target/&lt;profile&gt;/</code>.</dd></div>
        <div><dt>-j &lt;n&gt;</dt><dd>Parallel compilation jobs. Defaults to the core count.</dd></div>
      </div>

## uqu run {#run}

Everything after `--` goes to your program, not to the compiler.

```shell
$ uqu run -- --input data.csv --verbose
```

## uqu test {#test}

```shell
$ uqu test
$ uqu test --filter checksum
$ uqu test --jobs 1 --fail-fast
```

<div class="dl-grid">
        <div><dt>--filter &lt;text&gt;</dt><dd>Run only tests whose name contains the text.</dd></div>
        <div><dt>--fail-fast</dt><dd>Stop at the first failure.</dd></div>
        <div><dt>--jobs &lt;n&gt;</dt><dd>Run tests in parallel; <code>1</code> makes ordering deterministic.</dd></div>
        <div><dt>--format &lt;kind&gt;</dt><dd><code>pretty</code> (default) or <code>json</code> for CI ingestion.</dd></div>
      </div>

## uqu fmt {#fmt}

One style, no options, so formatting never becomes a review topic. Use
`--check` in CI to fail on unformatted code.

```shell
$ uqu fmt
$ uqu fmt --check src/
```

## Exit codes {#exit-codes}

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Compilation error, test failure, or unformatted code under `--check` |
| `2` | Bad usage: unknown flag, missing argument |
| `101` | Internal compiler error — please [report it]({{support}}) with the source that triggered it |

## Environment {#env}

<div class="dl-grid">
        <div><dt>UQU_HOME</dt><dd>Toolchain directory. Defaults to <code>~/.uqulang</code>.</dd></div>
        <div><dt>UQU_CACHE</dt><dd>Build cache location. Delete it freely; it only costs time.</dd></div>
        <div><dt>UQU_TARGET</dt><dd>Default target triple, overridden by <code>--target</code>.</dd></div>
        <div><dt>NO_COLOR</dt><dd>Any value disables coloured diagnostics.</dd></div>
      </div>

## Using it in CI {#ci}

The toolchain is a single archive with no installer, which makes CI setup
three lines. Pin the exact version so a new release never changes a build
that used to pass.

```text file=".github/workflows/ci.yml"
- run: curl -fsSL https://get.uqulang.com/install.sh | sh -s -- --version 0.1.0
- run: uqu licence activate --offline "$UQU_LICENCE"   # from a CI secret
- run: uqu fmt --check
- run: uqu test --format json
```
