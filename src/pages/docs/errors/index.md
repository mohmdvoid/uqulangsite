---
title: Compiler error index
description: Every diagnostic the uqulang compiler can emit, with an example that triggers it and the change that fixes it.
nav: docs
section: Documentation
priority: 0.7
layout: docs
eyebrow: Reference
lead: Every diagnostic the compiler can emit, what it means, and the change that fixes it. If you landed here from a compiler message, the code in the message is in the table below.
meta_line: Covers toolchain 0.1.0 · updated {{build_date}}
breadcrumb: [["Docs", "/docs/"]]
---

Compiler messages carry a code, such as `E0101`. Passing `--explain E0101` to
the compiler prints the same explanation you will find here:

```shell
$ uqu --explain E0101
```

## The index {#index}

{{error_index}}

## How to read a diagnostic {#reading}

Every message names three things: what the compiler expected, what it found,
and the rule that makes the difference matter. The caret line points at the
smallest expression that could be wrong, not at the whole statement.

```text
error[E0101]: use of moved value `buf`
  --> src/main.uqu:14:18
   |
12 |     let owned = move buf
   |                 -------- `buf` was moved here
13 |
14 |     io.write(buf.bytes())
   |              ^^^ used after the move
   |
   = note: a moved-from binding is dead; the value now belongs to `owned`
   = help: borrow instead of moving, or use `owned` on this line
```

The `note` explains the rule. The `help` proposes a change. Where the compiler
is confident the change is correct, `uqu fix` will apply it for you.

> [!NOTE]
> A diagnostic that was technically correct but did not tell you what to change
> is a bug worth reporting. Message quality is treated as a feature, not a
> nicety — see [the support page](/universities/#support).
