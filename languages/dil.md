# DIL

English | [简体中文](dil.zh-CN.md)

DIL is a UI DSL described in an October 2026 reverse-engineering report about ChatGPT. The authors observed Markdown, component tags, and JavaScript expressions compiled into a host-rendered interface. Research date is 2026-11-11. Evidence here consists of that report and a separate educational visualization. [Observer's report](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works), [visualization and its evidence scope](https://kejun.github.io/demos/chatgpt-intelligent-ui/)

The report describes catalog validation, expression-error recovery, JavaScript execution, and worker/message boundaries. Correctness guarantees, allocation behavior, scheduling semantics, and user metaprogramming remain open questions. The observed interface is tied to host components and actions. The reviewed material provides no reproducible compiler or Go/Zig/Rust/C comparison.

These observations support studying streaming UI language design. Language soundness, sandbox strength, and production performance require additional evidence. The visualization states that its interactions are illustrative and execute no real DIL. [Visualization source snapshot](https://github.com/kejun/demos/blob/150c9dcfc7b62239e2208c258bb87fe0e868f40f/chatgpt-intelligent-ui/index.html)
