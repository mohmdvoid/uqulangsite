---
title: Language tour
description: A tour of the uqulang language: bindings, types, structs, enums, pattern matching, traits, generics, optionals, errors, ownership, modules and C interoperability.
path: /docs/tour/
nav: docs
section: Documentation
priority: 0.8
layout: docs
eyebrow: Reference tutorial
lead: The whole language, in the order it makes sense to learn it. If you have written C, C++, Swift, Rust or Go, you can read this in one sitting.
meta_line: Covers toolchain 0.1.0 · updated {{build_date}}
breadcrumb: [["Docs", "/docs/"]]
prev: {"title": "Getting started", "path": "/docs/getting-started/"}
next: {"title": "Compiler CLI", "path": "/docs/cli/"}
---

## Bindings {#bindings}

`let` binds a value that cannot be reassigned; `var` binds one that can.
Types are inferred from the initialiser, and written explicitly when you want
the contract visible.

```uqulang
let limit = 4096             // inferred u32
let name: str = "uqulang"    // explicit
var count: u64 = 0           // mutable

count = count + 1
// limit = 8192              // error: cannot assign to a let binding
```

There is no uninitialised binding. A declaration without a value must be
assigned on every path before it is read, and the compiler checks that.

## Numbers and operators {#numbers}

Integer types name their width: `i8` … `i64`, `u8` … `u64`, plus `isize` and
`usize` for pointer-sized values. There are no implicit conversions between
them — a widening conversion is still written down.

```uqulang
let a: i32 = 7
let b: i64 = i64(a)          // explicit, always

let mask = 0b1010_1100
let addr = 0xFFFF_0000
let ratio = 1.5e-3           // f64

// Overflow is checked in debug builds and wraps only where you ask:
let sum = a + 1              // traps on overflow in debug
let wrap = a &+ 1            // wrapping add, in any build
```

## Control flow {#control-flow}

`if`, `while` and `for` behave as you expect. Conditions are `bool`; an
integer is not a condition. `guard` states a precondition and must exit the
scope.

```uqulang
func classify(n: i32) -> str {
    if n < 0 {
        return "negative"
    } else if n == 0 {
        return "zero"
    }
    return "positive"
}

func sum_to(n: u32) -> u32 {
    var total: u32 = 0
    for i in 1...n {          // inclusive range; 1..<n is exclusive
        total = total + i
    }
    return total
}

func head(items: []i32) -> i32 {
    guard items.len > 0 else { return 0 }
    return items[0]
}
```

## Functions {#functions}

Parameters are immutable bindings. Pass a pointer when the callee must write
through it, and the call site shows it with `&`.

```uqulang
func min(a: i32, b: i32) -> i32 {
    return a < b ? a : b
}

func swap(x: *i32, y: *i32) {
    let t = x.*
    x.* = y.*
    y.* = t
}

var left = 1
var right = 2
swap(&left, &right)

// Multiple results are a tuple, destructured at the call site.
func divmod(n: u32, d: u32) -> (u32, u32) {
    return (n / d, n % d)
}

let (q, r) = divmod(17, 5)
```

## Structs {#structs}

A struct is data with a predictable layout: fields in declaration order,
alignment following the platform C rules. Methods live in an `impl` block,
and `self` is explicit.

```uqulang
pub struct Rect {
    pub w: f32,
    pub h: f32,
}

impl Rect {
    pub func square(side: f32) -> Rect {       // no self: a constructor
        return Rect{ w: side, h: side }
    }

    pub func area(self) -> f32 {               // borrows self
        return self.w * self.h
    }

    pub func scale(self: *Rect, k: f32) {      // mutates through a pointer
        self.w = self.w * k
        self.h = self.h * k
    }
}

var r = Rect.square(2.0)
r.scale(3.0)
io.println("{}", r.area())    // 36.0
```

`@layout("c")` pins a struct to the exact C layout when you need to share it
across an FFI boundary.

## Enums and pattern matching {#enums}

Enums carry payloads, and `match` must cover every case. An uncovered case is
a compile error, not a warning — which is what makes adding a variant safe.

```uqulang
enum Shape {
    Circle(radius: f32),
    Rect(w: f32, h: f32),
    Point,
}

func area(s: Shape) -> f32 {
    match s {
        case .Circle(let radius):  return 3.14159 * radius * radius
        case .Rect(let w, let h):  return w * h
        case .Point:               return 0.0
    }
}
```

Patterns also match values, ranges and tuples:

```uqulang
match (code, retries) {
    case (200, _):            return .ok
    case (429, let n) if n < 3: return .retry
    case (500...599, _):      return .server_error
    default:                  return .fail
}
```

## Optionals {#optionals}

`?T` is a value that may be absent. There is no null pointer hiding inside an
ordinary type, and an optional must be unwrapped before use.

```uqulang
func find(haystack: []str, needle: str) -> ?usize {
    for i in 0..<haystack.len {
        if haystack[i] == needle { return i }
    }
    return nil
}

if let index = find(words, "uqu") {
    io.println("found at {}", index)
} else {
    io.println("not found")
}

let position = find(words, "uqu") ?? 0     // default if absent
```

## Errors {#errors}

A function that can fail is marked `throws`, optionally with the error type
it throws. Callers propagate with `try` or handle with `match`. Errors are
ordinary values moving up the call stack — there is no unwinding machinery
and no cost when nothing fails.

```uqulang
enum ConfigError {
    Missing(key: str),
    Invalid(key: str, value: str),
}

func port(cfg: Config) throws ConfigError -> u16 {
    guard let raw = cfg.get("port") else {
        throw ConfigError.Missing(key: "port")
    }
    guard let n = u16.parse(raw) else {
        throw ConfigError.Invalid(key: "port", value: raw)
    }
    return n
}

func start(cfg: Config) throws {
    let p = try port(cfg)        // propagate
    try listen(p)
}

// Or handle it here:
match port(cfg) {
    case .ok(let p):  io.println("port {}", p)
    case .err(let e): io.eprintln("config: {}", e)
}
```

> [!NOTE]
> Ignoring a failure is possible, but you have to write it: `discard try
> f()`. Grep finds every one of them.

## Memory and ownership {#memory}

Values live on the stack. Heap allocation is a function call you can see, and
every allocation has exactly one owner. When the owner goes out of scope, the
memory is released — no collector, no reference counting unless you opt into
it.

```uqulang
func build_report() throws -> Buffer {
    var buf = try Buffer.with_capacity(4096)   // buf owns the allocation
    defer_on_error buf.free()                  // freed only if we throw below

    try buf.write("total: ")
    try buf.write_u64(compute_total())

    return move buf                            // ownership goes to the caller
}

func use_it() throws {
    let report = try build_report()
    defer report.free()                        // released at scope exit

    io.write(report.bytes())
    // io.write(report.bytes())  after a `move report` would be a compile error
}
```

- `defer` runs at scope exit, in reverse order of declaration.
- `move` transfers ownership; the source binding is dead afterwards.
- Reading a moved-from binding is a compile error, not undefined behaviour.
- Shared ownership is explicit: `Rc<T>` from the standard library.

## Arrays, slices and strings {#slices}

`[N]T` is a fixed-size array. `[]T` is a slice: a pointer and a length,
bounds-checked in debug builds. `str` is a UTF-8 slice of bytes with no
terminator.

```uqulang
let fixed: [4]u8 = [1, 2, 3, 4]
let all: []u8 = fixed[..]        // slice over the whole array
let tail = fixed[1..]            // slice from index 1

let text = "مرحبا, uqulang"
io.println("{} bytes", text.len)              // byte length
for scalar in text.scalars() { /* … */ }      // Unicode scalars
for byte in text.bytes() { /* … */ }          // raw bytes

// C interop wants a terminator; ask for one explicitly.
let c_string = text.c_str()
```

## Traits and generics {#traits}

A trait is a set of requirements a type can satisfy. Generic functions are
monomorphised — one specialised copy per concrete type, dispatched
statically, with no vtable unless you ask for dynamic dispatch with `dyn`.

```uqulang
trait Writer {
    func write(self: *Self, bytes: []u8) throws -> usize
}

trait Display {
    func format(self) -> str
}

func log<W: Writer, T: Display>(out: *W, value: T) throws {
    try out.write(value.format().bytes())
}

// Dynamic dispatch when the concrete type is only known at run time:
func log_all(out: *dyn Writer, items: []dyn Display) throws {
    for item in items {
        try out.write(item.format().bytes())
    }
}
```

## Modules and visibility {#modules}

One file is one module, named by its path from the source root. Nothing
leaves a module unless it is marked `pub`, and there are no header files to
keep in sync.

```uqulang
// src/net/http.uqu
module net.http

pub struct Request { /* … */ }
pub func get(url: str) throws -> Response { /* … */ }

func parse_status(line: str) -> u16 { /* private to this module */ }
```

```uqulang
// src/main.uqu
module main

import std.io
import net.http                  // whole module
import net.http.get              // one symbol

func main() throws {
    let response = try http.get("https://example.org")
    io.println("{}", response.status)
}
```

## C interoperability {#c-interop}

Declaring a C function is enough to call it: no bindings generator, no
marshalling, no wrapper library. The call is a direct call with the platform
ABI.

```uqulang
extern "C" {
    func clock_gettime(clk: i32, ts: *TimeSpec) -> i32
    func write(fd: i32, buf: *void, count: usize) -> isize
}

@layout("c")
struct TimeSpec {
    seconds: i64,
    nanos: i64,
}

func now() -> i64 {
    var ts = TimeSpec{ seconds: 0, nanos: 0 }
    discard clock_gettime(0, &ts)
    return ts.seconds
}
```

And in the other direction — exporting for C to call:

```uqulang
@export("uqu_checksum")
pub func checksum(data: *u8, len: usize) -> u32 {
    var hash: u32 = 2166136261
    for i in 0..<len {
        hash = (hash ^ u32((data + i).*)) &* 16777619
    }
    return hash
}
```

## Attributes {#attributes}

<div class="dl-grid">
        <div><dt>@inline / @noinline</dt><dd>Force or forbid inlining of a function.</dd></div>
        <div><dt>@layout("c")</dt><dd>Use the platform C layout and padding for a struct.</dd></div>
        <div><dt>@export("name")</dt><dd>Expose a symbol under an exact name for C callers.</dd></div>
        <div><dt>@deprecated("use x")</dt><dd>Warn at every use site, with your message.</dd></div>
        <div><dt>@target(os: "linux")</dt><dd>Compile a declaration only for matching targets.</dd></div>
      </div>

## Tests {#tests}

`test` blocks are part of the language, not a library. They are compiled out
of release builds entirely.

```uqulang
test "checksum is stable" {
    let data: [3]u8 = [1, 2, 3]
    assert.equal(checksum(&data[0], 3), 0x2E3D_1A47)
}

test "empty input" {
    assert.equal(checksum(nil, 0), 2166136261)
}
```

## Planned, not yet shipped {#planned}

These are designed and discussed, and not in 0.1. Do not write code against
them yet.

- Generics over constant values, for fixed-capacity containers.
- Compile-time evaluation beyond constant folding.
- Structured concurrency and non-blocking I/O in the standard library.
- A package registry and a lockfile format.
