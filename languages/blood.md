# Blood

English | [简体中文](blood.zh-CN.md)

Blood is an upcoming language by Kit Langton. As checked on 2026-11-11, its [official website](https://blood-lang.org/) is a teaser with no specification, compiler download, or documentation links. This note records the announcement and the questions it raises for future investigation.

In his [2026-11-07 announcement](https://x.com/kitlangton/status/2119137520529375499), the author describes a strong type system, effects, metaprogramming, inexpensive worktrees, semantic merging, and content-addressed code stored in SQLite. He also claims performance exceeding Rust. These are author claims; this study found no runnable implementation or reproducible benchmark supporting a comparison.

## What merits follow-up

A type and effect system could make operations and their interactions easier to check, but the announcement does not establish which errors the compiler rejects, how effects are handled, or whether concurrency has static safety guarantees. The ownership model, allocation strategy, destruction behavior, and unsafe boundary are also unspecified in the available material.

Content-addressed code and semantic merging are particularly interesting as language/tooling integration: definitions might be identified independently of their textual location, enabling different approaches to reuse and versioning. The available announcement does not establish the identity rules, dependency model, SQLite schema, or compatibility with ordinary source repositories. Metaprogramming is named without a documented execution or staging model.

There is no basis yet for comparing compilation with Go/Zig or execution with Rust/C. A useful next milestone is public code or documentation that makes the correctness, memory, systems, concurrency, and metaprogramming semantics testable. Until then, Blood belongs among upcoming languages with explicit evidence limits.
