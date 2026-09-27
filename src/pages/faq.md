---
title: Frequently asked questions
description: Common questions about uqulang — what it is for, how it compares to C and Rust, licensing for universities, platform support, and what is not finished yet.
nav: null
section: FAQ
priority: 0.7
layout: page
faq: true
eyebrow: Questions
lead: The questions that come up most often, answered plainly. If yours is not here, ask your institution's support contact or write to us.
---

## Is uqulang open source? {#open-source}

No. The compiler, standard library and toolchain are commercial software
licensed to universities and research institutions. This website and its
documentation are public and openly licensed, but that is a separate thing —
see [the licensing page](/universities/).

## Why another systems language? {#why}

Because the two things a systems course needs are usually in different
languages. C shows the student what the machine does, and hides nothing — but
it also hides nothing about its own age, and a beginner spends the first weeks
on undefined behaviour rather than on the subject. Newer languages read well
but put a runtime, a collector or a borrow checker between the student and the
hardware.

uqulang is an attempt at the narrow overlap: the machine model of C with the
reading experience of Swift, small enough to teach in one semester.

## How does it compare to C? {#versus-c}

Same compilation model, same ABI, same ability to point at a line and say what
it costs. Different in the places where C's age shows: no implicit numeric
conversions, no uninitialised bindings, no null pointer hiding inside an
ordinary type, exhaustive `match`, and errors that must be handled at the call
site.

Interoperation is direct rather than wrapped, so a course can use an existing C
library without a binding layer in between.

## How does it compare to Rust? {#versus-rust}

Rust proves more, and asks more of the reader to do it. uqulang's ownership
rules are scope-based and explicit: the compiler catches use-after-move and
double-free, and does not attempt to prove every aliasing property. That is a
deliberate trade — less proved, less to learn before the first working program.

If your course is about proving memory safety, Rust is the better instrument.
If it is about what the machine does, with guard rails, this is.

## What platforms are supported? {#platforms}

macOS 13+ on Apple silicon and Intel, Linux with glibc 2.31+ or musl on x86-64
and aarch64, and Windows 10 22H2+ on x86-64 and arm64. Bare-metal targets are
on [the roadmap](/universities/#roadmap), not in 0.1.

## Can students install it on their own laptops? {#student-install}

Yes. A campus licence covers every enrolled student and every member of staff,
on university machines and their own. See
[what a licence includes](/universities/#included).

## Does it work in a lab with no internet? {#offline}

Yes, and this was designed for rather than worked around. Site licences include
an offline activation file, so lab machines never contact a licence server, and
the toolchain is a single archive you can put on an image or a file share. See
[lab and offline deployment](/install/#labs).

## How do you handle grading? {#grading}

The same source and the same toolchain version produce a byte-identical binary,
and `uqu test --format json` emits machine-readable results for an autograder.
Pinning a release for the length of a semester is part of the licence, so an
upgrade cannot change results mid-course.

## What is not finished? {#unfinished}

Generics over constant values, structured concurrency and non-blocking I/O, a
dependency manager, and a larger standard library. All are designed; none are
in 0.1. The documentation marks anything unshipped as *planned* in place rather
than implying it exists.

## Why are there no benchmark numbers? {#benchmarks}

Because we cannot yet hand you a harness to reproduce them on your own
machines. When 0.2 ships that harness, the numbers go up — including the ones
where we lose. Until then, treat performance claims about uqulang, including
ours, as unproven.

## Is the documentation available in Arabic? {#arabic}

Partly. The home page and the documentation overview are in Arabic; the
detailed documentation is in English and is being translated. Every page has a
language switch in the header, and a link to a page that is not translated yet
goes to the English version rather than nowhere.

## Who is behind it? {#who}

uqulang is designed and built in Saudi Arabia. The name comes from
<span lang="ar" dir="rtl">عقل</span> — *ʿaql*, the reasoning mind — and the mark
is drawn from its first letter.
