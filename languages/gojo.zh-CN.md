# Gojo

[English](gojo.md) | 简体中文

Gojo 是实验性的系统编程语言，围绕所有权、受限借用、确定性资源释放和结构化并发设计，编译器用 Rust 编写，通过 C 后端与 POSIX 运行时执行。它希望同时覆盖安全的原生工具和服务，以及较小的语言复杂度与较快的编译体验。[官方仓库](https://github.com/egoist/gojo)

## 研究快照

研究日期为 2026-11-11，固定提交为 `215e07c8f016203c52a68e91db9d7097e8e4ff4b`，提交日期为 2026-11-10。本机编译器报告 `gojo 0.0.1 (215e07c8f0, aarch64-apple-darwin)`。本轮以语言规范和源码为准，WebAssembly 与包管理文档中含有尚在提案阶段的设计。[固定源码](https://github.com/egoist/gojo/tree/215e07c8f016203c52a68e91db9d7097e8e4ff4b)、[语言规范](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md)、[WebAssembly 提案](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/wasm.md)

| 维度 | 当前判断 |
| --- | --- |
| 程序正确性 | 已实现所有权、借用、穷尽匹配、错误处理和线性资源检查，保障依赖编译器、运行时、标准库与 unsafe 边界 |
| 内存正确性与效率 | 默认独占所有权，支持选择性提前释放、显式 Rc／Arc、小对象分配器与 Box 复用；任务栈和共享结构需要单独测量 |
| 系统编程 | 已有固定宽度整数、f64、裸指针、C 互操作、文件、进程和网络库，适合继续研究用户态工具与服务 |
| 编译与执行 | 本机整数循环接近 C／Rust；运行库缓存预热后，完整 release 构建耗时约为 Go 的 1.56 倍、Zig 的 1.66 倍 |
| 并发模型 | 作用域内的有栈 M:N 任务，包含借用约束、取消、通道和共享状态检查，固定地址栈具有明确成本 |
| 元编程 | 泛型单态化、整数常量参数与静态反射支持专门化和序列化，编译期功能边界较明确 |

## 程序正确性

普通参数借用，`inout` 参数通过调用点的 `&` 表达可变借用，`sink` 参数接收所有权。检查器追踪已移动、可能已移动、跨循环移动、冲突访问和失效视图。引用与视图的存储位置和逃逸受到限制，返回视图可以用 `of` 标明来源，或由编译器分析返回值来源。这种限制减少了生命周期标注需求，也限制了长期跨对象借用的数据结构。[借用检查器](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/borrowck.rs)、[所有权规则](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#5-ownership)

`?T` 表达可选值，`T ! E` 表达显式错误，模式匹配需要穷尽。`linear struct` 与 `linear enum` 要求值沿每条正常退出路径被消费，可以表达事务必须 commit／rollback 等协议。panic 会结束进程，资源清理的保障需要结合这种失败模型理解。[线性类型](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#57-linear-types)、[错误处理](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#8-error-handling)

release 构建保留溢出、索引、转换、除零和 unwrap 检查。`requires` 在调用时检查前置条件，并向函数体提供事实；`checkfree fn` 要求编译器消除函数中的所有数组边界检查；`gojo claims` 展示哪些检查已消除、哪些仍保留。这些能力的保障范围由对应程序分析和运行时契约决定。[边界分析实现](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/codegen/bce.rs)、[执行模型](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#14-execution-model)

裸指针解引用、外部调用和 unsafe 函数要求显式 unsafe 块。manifest 可以限制依赖中的 unsafe，以及文件系统、环境变量、进程和网络等标准库权限。保障仍依赖相应接口边界与外部代码的约定。[unsafe 与 FFI](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#11-unsafe-and-ffi)、[manifest 规则](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#21-package-manifest-gojotoml)

固定源码含 259 个编译错误用例和 257 个对抗借用检查的用例。本轮运行上游 `compile_errors` 和 `unsafe_programs_rejected`，两项测试通过，覆盖这 516 个输入。另外执行并记录了 15 项探针，包括四个正确程序、八类编译拒绝和三项 release 运行时失败检查。完整 sanitizer 与长期模糊测试仍需单独运行。[上游测试入口](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/tests/suite.rs)、[本项目原始结果](../experiments/gojo-2026-11-11/results.json)

## 内存正确性与效率

具有可观察清理行为的值在作用域结束时析构，包括文件和用户定义的析构方法。对于析构只释放内存的值，编译器可以在最后使用后提前释放，并追踪仍引用它的视图。闭包、任务捕获、defer、unsafe 和裸指针表达式会约束这一优化。[析构分析](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/codegen/drops.rs)、[提前释放设计](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/drops.md)

Vec／String 缓冲区使用 malloc／realloc，小型 Box 及部分共享或接口对象使用线程局部的尺寸分级空闲链表，消费后的 Box 有时可以复用于重建节点。Rc／Arc 显式表达共享，Arena 使用带代次的句柄。循环共享图仍需要适当的 Weak 或 Arena 设计。[运行时分配实现](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/runtime/gojo_rt.c)、[分配与 Box 复用](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#14-execution-model)

项目方报告，两阶段大数组示例通过提前释放将峰值 RSS 从 383 MB 降到 192 MB，机器为 Apple M5。这体现了特定生命周期模式下的收益。本轮本机整数循环主要提供执行与构建数据，分配和峰值内存仍需相应工作负载。[项目方内存测量](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/drops.md#measurements)

## 系统编程能力

Gojo 提供最高到 u64／i64 的固定宽度整数、f64、拥有缓冲区与借用切片、裸指针，以及 C 兼容的外部函数签名。外部库可以静态链接或 dlopen，导出的 C 函数仍有回调与调用线程限制。原生程序经 C 编译器生成，支持的交叉编译路径使用 Zig。[类型](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#41-built-in-types)、[C 互操作](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#11-unsafe-and-ffi)

标准库覆盖文件、进程、TCP／UDP／DNS、HTTP／TLS 与常见数据格式。当前原生宿主为 macOS／Linux 的 arm64 与 x86-64，运行时依赖 POSIX 与任务调度器。Windows、包版本解析与注册中心、分包独立编译和部分工具链能力仍有限，WebAssembly 保留在提案中。内核、驱动、裸机和精确布局／分配器控制还需要额外的目标与 API 证据。[标准库](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/std/README.md)、[当前限制](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/README.md#not-yet-implemented)、[Wasm 提案](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/wasm.md)

## 并发模型

`go` 在 `scope` 中创建有栈任务，作用域等待子任务结束。任务可以借用活得足够久的数据，包括互不重叠的切片区间。编译器推导 send 能力，追踪任务捕获、可变访问与作用域值逃逸；Mutex、RwLock、原子操作和通道表达共享状态，持锁区域限制可能等待的操作。[结构化任务与共享规则](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#10-concurrency)

运行时将任务以 M:N 方式调度到 worker，使用抢占检查点、阻塞外部调用处理和 I/O 停泊。取消沿任务树传播，受支持的阻塞操作可以被中断，析构过程屏蔽取消。模拟调度器支持种子、虚拟时间、交错探索与故障注入，实际覆盖范围取决于测试工作负载和探索到的调度。[调度器实现](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/runtime/gojo_sched.c)、[运行时与模拟规则](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#107-runtime)

任务可能借用彼此栈上的数据，因此栈保留固定地址。长时间停泊的栈可以休眠并归还页面，传给 C 的栈指针则可能钉住栈。项目方报告 Linux 上 10 万个暂停任务传递值耗时 0.38 秒、占用 441 MB，Go 为 0.11 秒、284 MB；macOS 的空闲任务可以从栈休眠中获益。评估并发效率需要考虑任务数、停泊时间和工作分布。[并发基准及口径](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/bench/README.md#goroutine)

## 元编程能力

泛型具有能力约束并通过单态化生成实现，整数常量参数表达固定维度，结构化接口根据方法集合匹配。静态反射支持字段与类型遍历、静态分支、按类型构造，可用于通用序列化与解码器。规范也描述了泛型体与专门化代码的检查边界。[泛型与静态反射](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#9-generics)、[检查实现](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/src/check/body.rs)

当前元编程能力集中于这些边界明确的构造。规范描述的实现范围尚未包含用户宏系统和任意编译期程序执行。单态化及反射生成代码会增加 C 输出和后端工作，大型泛型程序的编译时间与二进制体积仍需测量。

## 本机实验

本轮复用 Bend 专题中的 C／Rust／Go／Zig xorshift32 源码，加入 Gojo 实现。五种实现从种子 1 开始执行 5,000 万轮，校验和均为 `376378803`。机器为 Apple M4 Max、16 核、128 GiB，使用 clang 22.1.8、Rust 1.95.0-nightly、Go 1.27.3、Zig 0.16.0。Gojo 固定一个 worker，串行轮转测量，预热一次后计时五次构建、七次运行。[复现脚本](../experiments/gojo-2026-11-11/run.py)、[原始数据](../experiments/gojo-2026-11-11/results.json)

| 实现 | 完整构建中位数 | 运行中位数 |
| --- | --- | --- |
| Gojo release | 171.7 ms | 76.16 ms |
| Go | 110.3 ms | 88.24 ms |
| Zig ReleaseFast | 103.6 ms | 75.86 ms |
| Rust opt-level=3 | 111.6 ms | 75.07 ms |
| C -O3 | 135.2 ms | 75.26 ms |

每次 Gojo 构建保留运行库目标文件缓存，删除生成程序的二进制缓存。另用空运行库缓存测得首次 release 构建为 2.021 秒。Gojo 默认 release 使用 clang -O2 并保留语言检查，其他实现采用记录中的优化选项。此例 Gojo 执行耗时约为 C 的 1.012 倍、Rust 的 1.015 倍，计时包含进程启动和打印。这些数字的适用范围是当前标量依赖链，分配、争用、I/O 和大型构建需要对应测量。

项目方另有微基准和 Rust 应用工作负载对照，JSON、日志处理与 HTTP 服务呈现不同结果，其中服务数据也受库选择和负载生成方式影响。它们使用不同版本与硬件，应按各自方法解释。[微基准](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/bench/README.md)、[应用基准结果](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/bench/realworld/results/issue-4/after-pinned/RESULTS.md)

复现命令和工具要求见英文专题，脚本记录工具链、缓存状态、原始样本、诊断和 bounds claims。[实验复现](gojo.md#reproduction)
