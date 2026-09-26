---
title: Getting started
description: Install uqulang, compile and run your first program, add a test, and learn the project layout the compiler expects.
path: /docs/getting-started/
nav: docs
section: Documentation
priority: 0.8
layout: docs
eyebrow: Tutorial
lead: From nothing installed to a tested, compiled binary. Everything here works with toolchain 0.1.0 on macOS, Linux and Windows.
breadcrumb: [["Docs", "/docs/"]]
prev: {"title": "Documentation overview", "path": "/docs/"}
next: {"title": "Language tour", "path": "/docs/tour/"}
---

## 1. Install the toolchain {#install}

If you have not installed `uqu` yet, follow the [installation
guide](/install/) — it is one command on every supported platform. Then
confirm the compiler can see everything it needs:

```shell
$ uqu doctor
toolchain   ~/.uqulang/0.1.0
linker      cc (found)
target      aarch64-apple-darwin
status      ready
```

## 2. Create a project {#new-project}

`uqu init` writes the smallest project that builds: a manifest, a source
directory and one module.

```shell
$ uqu init greeter
$ cd greeter
$ tree
.
├── uqu.toml
└── src
    └── main.uqu
```

The manifest is deliberately small. There is no build script:

```text file="uqu.toml"
[package]
name    = "greeter"
version = "0.1.0"

[build]
target = "native"
opt    = "debug"
```

## 3. Write and run a program {#first-program}

Open `src/main.uqu`. Every executable needs exactly one `main`, and `main`
may declare that it throws.

```uqulang file="src/main.uqu"
module main

import std.io

func greet(name: str) -> str {
    return str.format("Hello, {}!", name)
}

func main() {
    let names = ["Reem", "Faisal", "عبدالله"]

    for name in names {
        io.println(greet(name))
    }
}
```

Build and run it in one step:

```shell
$ uqu run
Hello, Reem!
Hello, Faisal!
Hello, عبدالله!
```

> [!NOTE]
> Source files are UTF-8, and string literals hold arbitrary Unicode.
> Identifiers are ASCII in 0.1; wider identifier support is *planned*.

## 4. Add a type {#types}

Structs hold data with a layout you can predict — fields in declaration
order, C-compatible padding rules. Behaviour is attached with `impl`, not
inheritance.

```uqulang file="src/greeting.uqu"
module greeting

import std.io

pub struct Greeting {
    pub greeting: str,
    pub name: str,
}

impl Greeting {
    pub func new(name: str) -> Greeting {
        return Greeting{ greeting: "Hello", name: name }
    }

    pub func render(self) -> str {
        return str.format("{}, {}!", self.greeting, self.name)
    }
}
```

Import it from `main` by module path:

```uqulang file="src/main.uqu"
module main

import std.io
import greeting.Greeting

func main() {
    let g = Greeting.new("world")
    io.println(g.render())
}
```

## 5. Handle a failure {#errors}

Anything that can fail says so in its signature. The caller must respond —
with `try` to propagate, or `match` to handle.

```uqulang file="src/main.uqu"
module main

import std.io
import std.fs

func main() throws {
    let text = try fs.read_to_string("names.txt")

    for line in text.lines() {
        let name = line.trim()
        if name.len == 0 { continue }
        io.println("Hello, {}!", name)
    }
}
```

If the file is missing, the error reaches `main`, the process exits non-zero,
and the message goes to stderr — no stack unwinding, no silent default:

```shell
$ uqu run
error: fs.Error.NotFound: names.txt
  at main (src/main.uqu:8)
$ echo $?
1
```

## 6. Write a test {#tests}

Tests live next to the code they test, in the same file or a sibling one. The
runner is built in; there is nothing to add to the manifest.

```uqulang file="src/greeting.uqu"
test "render includes the name" {
    let g = Greeting.new("Reem")
    assert.equal(g.render(), "Hello, Reem!")
}

test "empty name still renders" {
    let g = Greeting.new("")
    assert.equal(g.render(), "Hello, !")
}
```

```shell
$ uqu test
greeting  render includes the name ....... ok (0.4 ms)
greeting  empty name still renders ....... ok (0.3 ms)

2 passed, 0 failed in 0.02 s
```

## 7. Build for release {#release}

A release build turns on optimisation and strips debug information. The
result is a single static binary you can copy to any machine with the same
target triple.

```shell
$ uqu build --release
$ ls -lh target/release/greeter
-rwxr-xr-x  1 you  staff   412K  greeter

$ ./target/release/greeter
Hello, world!
```

## Where to go next {#next}

- [Language tour](/docs/tour/) — the rest of the language, in order.
- [Compiler CLI](/docs/cli/) — every flag, including cross-compilation.
- [For universities](/universities/) — licensing, lab deployment and support.
