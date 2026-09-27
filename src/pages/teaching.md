---
title: Teaching with uqulang
description: Course material, lab deployment, grading and syllabus guidance for faculty teaching systems programming with uqulang at a licensed institution.
nav: universities
section: For universities
priority: 0.8
layout: page
eyebrow: For faculty
lead: What comes with a campus licence for the people who actually run the course — the starter kit, the lab setup, grading, and an honest account of where uqulang is the wrong choice.
---

## The starter kit {#kit}

Every campus licence includes a course starter kit, delivered through the
[licence portal]({{portal}}). It is material to adapt, not a curriculum to
adopt.

<div class="grid grid--2">
  <article class="card">
    <h3 class="card__title">Lab exercises</h3>
    <p class="card__body">
      Twelve graded exercises from a first program to a small allocator, each
      with a worked solution and the common wrong answers annotated.
    </p>
  </article>
  <article class="card">
    <h3 class="card__title">Sample assignments</h3>
    <p class="card__body">
      Four assignments with rubrics and reference implementations: a parser, a
      memory pool, a C interop task, and a concurrency-free pipeline.
    </p>
  </article>
  <article class="card">
    <h3 class="card__title">Slides</h3>
    <p class="card__body">
      Editable lecture slides covering the language in twelve sessions,
      matching the order of the <a href="/docs/tour/">language tour</a>.
    </p>
  </article>
  <article class="card">
    <h3 class="card__title">Autograder harness</h3>
    <p class="card__body">
      A reference harness consuming <code>uqu test --format json</code>, with
      adapters for the common submission systems.
    </p>
  </article>
</div>

## A twelve-week shape {#syllabus}

This is the order the material is written in. Weeks are a unit of convenience;
adapt freely.

| Weeks | Topic | What the student can do afterwards |
| --- | --- | --- |
| 1–2 | Bindings, control flow, functions | Write, compile and test a program that does arithmetic and branches |
| 3–4 | Structs, enums, pattern matching | Model a small domain and handle every case of it |
| 5–6 | Memory: stack, heap, ownership, `defer` | Explain where a value lives and who frees it |
| 7 | Errors as values | Write code whose failure paths are visible in the signature |
| 8–9 | Slices, strings, and what UTF-8 costs | Reason about bytes against characters |
| 10 | Traits and generics | Write code once for several types without a vtable |
| 11 | C interoperability | Call an existing C library and be called from C |
| 12 | Reading the generated code | Use `uqu build --emit asm` to connect source to instructions |

Week 12 is the one faculty tell us matters most, and the one most easily cut
for time. It is the week where the machine model stops being an assertion.

## Running the lab {#lab}

The toolchain is a single binary with offline activation, so a lab image is a
copy and a symlink. The full procedure is on the
[installation page](/install/#labs).

> [!NOTE]
> Pin the release for the length of the course. A campus licence includes a
> named version held stable for a semester, so an upgrade cannot change a
> student's results halfway through.

## Grading {#grading}

Two properties matter for automated marking, and uqulang has both.

**Reproducible builds.** The same source and the same toolchain version produce
a byte-identical binary. A submission that compiles on the student's laptop
compiles identically on the marker's machine.

**Machine-readable test output.** The test runner is part of the language, not
a library the student has to install:

```shell
$ uqu test --format json
{"tests":[{"name":"render includes the name","ok":true,"ms":0.4}],"passed":1,"failed":0}
```

Marking on the compiler's own diagnostics is also viable, and more instructive
than marking on output alone — a submission that fails with
[E0101](/docs/errors/E0101/) has a specific, teachable misunderstanding.

## Where uqulang is the wrong choice {#not-suitable}

We would rather you find this out now than in week three.

- **A course about proving memory safety.** uqulang catches use-after-move and
  double-free; it does not prove the absence of aliasing bugs. Rust is the right
  instrument for that syllabus.
- **A first-ever programming course for non-majors.** Explicit types, explicit
  conversions and explicit memory are the point here, and they are a lot to
  carry in week one. Python remains the better on-ramp.
- **Anything needing concurrency this year.** Structured concurrency is designed
  and unshipped. Threads are reachable through C, which is not a foundation for
  coursework.
- **A course that depends on a package ecosystem.** There is no registry yet.
  Dependencies are paths and archives.

## Asking for what you need {#requests}

Requests from a course that is actually running carry the most weight in what
gets built next — teaching friction is the most useful signal we get. They go
through your named contact and are answered in writing; accepted ones appear on
[the roadmap](/universities/#roadmap) against a release.

<div class="hero__actions mt-6">
  <a class="btn btn--primary" href="{{contact}}">Request a campus licence</a>
  <a class="btn btn--secondary" href="/universities/#evaluation">Evaluate it for one course</a>
</div>
