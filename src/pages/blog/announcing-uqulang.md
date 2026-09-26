---
title: Announcing the uqulang 0.1 preview
description: The first release of the uqulang compiler and toolchain to universities: what works today, what is deliberately missing, and where we want feedback from teaching staff.
path: /blog/announcing-uqulang/
nav: blog
section: Blog
priority: 0.6
head_extra: <script type="application/ld+json">{"@context":"https://schema.org","@type":"BlogPosting","headline":"Announcing the uqulang 0.1 preview","datePublished":"2026-09-26","inLanguage":"en","url":"https://uqulang.org/blog/announcing-uqulang/"}</script>
layout: post
date: 2026-09-26
kind: Release
lead: The compiler is self-hosting, the toolchain is one binary, and both are now shipping to universities. This is a preview, and the version number is doing honest work.
breadcrumb: [["Blog", "/blog/"]]
breadcrumb_current: 0.1 preview
prev: {"title": "All posts", "path": "/blog/"}
next: {"title": "Install the preview", "path": "/install/"}
meta_line: <time datetime="2026-09-26">26 September 2026</time> {{hijri:2026-09-26}} <span>Release</span>
---

uqulang began with a narrow complaint: writing systems code still means
choosing between a language that tells you exactly what the machine will do
and a language you can comfortably read. C gives you the first. Swift gives
you the second. Most of the time you pick one and pay for the other for
years.

0.1 is the first version where that idea is testable by somebody other than
the people who wrote it — starting with the departments teaching the courses
it was built for.

## What works today {#what-works}

- A self-hosting compiler producing native binaries for macOS, Linux and
  Windows on x86-64 and aarch64.
- Structs, enums with payloads, exhaustive pattern matching, traits, generics
  with static dispatch.
- Optionals, typed `throws`, `defer`, scope-based ownership with `move`.
- C interop in both directions at the ABI level, with no bindings generator.
- `uqu build / run / test / fmt / check / doc / lsp` in one binary, and `uqu
  doctor` when something is off.

## What is deliberately missing {#what-is-missing}

A preview that pretends to be complete wastes everybody's time. These are
known gaps, not oversights:

- **No dependency manager.** Dependencies are paths and archives for now. The
  design is being written.
- **No concurrency story.** Threads exist through the C library; structured
  concurrency is designed and unshipped.
- **Generics are incomplete.** Generics over constant values — the thing
  fixed-capacity containers need — is 0.2 work.
- **The standard library is small** and its module layout will move before
  1.0.
- **No public issue tracker.** Reports come through your institution’s named
  support contacts, which is also how they get prioritised.
- **No published benchmarks.** See below; this one is on purpose.

## On benchmarks {#benchmarks}

New languages usually launch with a graph. We are not going to, yet. The
generated code is already close to what clang emits at `-O2` for the loops we
have measured, but “close on our machines, on our examples” is not a claim
worth publishing.

0.2 ships a benchmark harness to licensed institutions — hardware
description, compiler flags, input data and raw timings — and the numbers
will be whatever the harness produces on your machines, including where we
lose. Until then, the [performance table on the front
page]({{url:/}}#performance) stays empty.

## Where feedback helps most {#feedback}

Not all feedback is equally useful at this stage. In rough order:

1. **Diagnostics that were unhelpful.** If the compiler was right but the
   message did not tell you what to change, that is a bug worth filing.
2. **Ownership friction.** Real code where the ownership rules forced an
   awkward structure. These cases shape 0.2.
3. **C interop gaps.** A header the compiler cannot express, a layout
   mismatch, a calling convention we got wrong.
4. **Platform failures.** Anything where the toolchain does not build or run,
   with the `uqu doctor` output attached.

## A note on where this comes from {#thanks}

uqulang is designed and built in Saudi Arabia. The name comes from <span
lang="ar" dir="rtl">عقل</span> — *ʿaql*, the reasoning mind — and the mark is
drawn from its first letter. Both the language and the documentation are
developed in English and Arabic, because the people who will use it read
both.

Install it, break it, and tell us where it bent: [installation
guide](/install/) · [request a licence](/universities/#contact) · [support
portal]({{support}}).
