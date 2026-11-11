# Awesome New Programming Languages

[English](README.md) | 简体中文

精选正在演进的编程语言，介绍它们的设计与实现思路。

重点关注程序正确性、内存安全与效率、系统编程、并发模型和元编程能力。编译效率以 Go、Zig 为参照，执行效率以 Rust、C 为参照，相关实现与证据收录在专题研究中。

## 目录

- [系统编程](#系统编程)
- [科学计算与 GPU 编程](#科学计算与-gpu-编程)
- [函数式编程与证明](#函数式编程与证明)
- [领域特定语言](#领域特定语言)
- [预告阶段语言](#预告阶段语言)
- [研究与实验](#研究与实验)
- [参与贡献](#参与贡献)

## 系统编程

- [Gojo](https://github.com/egoist/gojo) — 实验性系统语言，结合所有权、无需生命周期参数的借用、确定性释放、结构化有栈任务和静态反射，通过 C 后端生成原生程序。[研究专题](languages/gojo.zh-CN.md) · [English](languages/gojo.md)

## 函数式编程与证明

- [Bend 2](https://github.com/bendlang/bend) — 纯函数式语言，结合依赖类型、仿射所有权、显式正确性证明、编译期模板，以及 CPU／GPU 上的 fork-join 执行。[研究专题](languages/bend.md)

## 科学计算与 GPU 编程

- [Mojo](https://github.com/modular/modular/tree/main/Mojo) — 使用接近 Python 的语法构建原生程序，结合所有权、编译期特化、SIMD 和显式 CPU／GPU 编程。[研究专题](languages/mojo.zh-CN.md) · [English](languages/mojo.md)

## 领域特定语言

- [DIL](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works) — 第三方逆向报告描述的界面语言，以标记、组件标签和表达式构建流式交互界面。[研究笔记](languages/dil.zh-CN.md) · [English](languages/dil.md)

## 预告阶段语言

- [Blood](https://blood-lang.org/) — 已公布的设计方向包括类型、效应、元编程，以及支持语义合并的内容寻址代码；尚无公开实现细节和基准可供验证。[研究笔记](languages/blood.zh-CN.md) · [English](languages/blood.md)

## 研究与实验

- [Bend 行为探针与整数循环基准](experiments/bend-2026-11-11/run.py) — 可复现的机制检查，以及 C／Rust／Go／Zig 对照。[实验结果](experiments/bend-2026-11-11/results.json)
- [Gojo 安全探针与整数循环基准](experiments/gojo-2026-11-11/run.py) — 所有权与运行时检查、边界分析报告，以及 C／Rust／Go／Zig 对照。[实验结果](experiments/gojo-2026-11-11/results.json)
- [Mojo 所有权探针与整数循环基准](experiments/mojo-2026-11-11/run.py) — 编译拒绝检查、编译期求值，以及 C／Rust／Go／Zig 对照。[实验结果](experiments/mojo-2026-11-11/results.json)

研究记录注明源码版本、一手资料、能力边界和测量条件。性能结论保留其工作负载与工具链范围。

## 参与贡献

欢迎通过 Issue 和 Pull Request 推荐语言、修正资料或补充介绍。请附上项目链接、简短描述，以及支持设计或性能结论的来源。
