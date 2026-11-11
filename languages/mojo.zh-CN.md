# Mojo

[English](mojo.md) | 简体中文

Mojo 将接近 Python 的语法与原生值类型、所有权、编译期特化及 CPU／GPU 编程结合起来。在本项目中，主要关注它构建高性能库和异构计算程序的能力。[项目源码](https://github.com/modular/modular/tree/f364f26cd29207a9501625f566527354bb5dac4f/Mojo) · [手册](https://mojolang.org/docs/manual/)

调研日期为 2026-11-11。实测安装包报告 **Mojo 1.2.0 (2016d0cd)**；独立检查的公开源码快照为 `f364f26cd29207a9501625f566527354bb5dac4f`，没有确认它与该二进制的源码完全对应。Mojo 已开源，采用带 LLVM 例外的 Apache-2.0 许可；MAX 的许可需另行查看。[源码与许可](https://github.com/modular/modular/tree/f364f26cd29207a9501625f566527354bb5dac4f)

## 所有权与正确性

值具有所有者，函数参数默认不可变，`mut` 提供独占的可变访问，`^` 显式转移所有权。Origin 跟踪引用的来源、生命周期和可变性，也用于指针与 span，因此编译器可以拒绝可变别名、转移后使用等错误。声明 `raises` 的函数要求调用者处理或传播错误。这些机制保障局部安全性质，算法是否满足业务规格仍需另外验证。[所有权](https://mojolang.org/docs/manual/values/ownership/) · [生命周期](https://mojolang.org/docs/manual/values/lifetimes/) · [错误处理](https://mojolang.org/docs/manual/errors/)

系统代码需要注意安全边界：使用不受跟踪的 origin 和 unsafe 指针操作时，分配、初始化、越界和生命周期由程序员负责。所有权检查无法弥补 unsafe 实现中的错误；自定义资源类型也需要实现相应的销毁行为。[指针](https://mojolang.org/docs/manual/pointers/using-pointers/)

## 内存与系统编程

Mojo 通常在最后一次使用后尽早销毁值，即 **ASAP destruction**；借用可以延长生命周期。依赖资源存活时间的代码需要适应这一规则，要求显式销毁的类型则可以强制调用者执行销毁操作。它通过及时释放和底层分配 API 提供内存控制，无需追踪式垃圾收集器。[销毁规则](https://mojolang.org/docs/manual/lifecycle/death/) · [显式销毁](https://mojolang.org/docs/manual/lifecycle/explicit-destroy/)

编译器支持原生可执行文件、目标文件、汇编、LLVM IR、动态库和设备目标。C 互操作和内联 MLIR 提供底层控制；Python 互操作便于使用已有生态，但任意 Python 代码的性能仍需单独评估。由 C 宿主加载、且使用并行 API 的动态库，需要按文档初始化运行时。[编译](https://mojolang.org/docs/tools/compilation/) · [内联 MLIR](https://mojolang.org/docs/reference/inline-mlir/)

## 并发与元编程

CPU 并行可使用 `parallelize` 等库 API，分发按索引划分的任务并等待完成。GPU 编程采用显式 kernel、设备上下文、异步传输和启动，以及同步操作；这些 GPU API 通过 MAX 提供。本次没有验证任意并行 kernel 都受编译器的数据竞争自由保证，也没有开展 GPU 实验。[CPU 并行 API](https://max.modular.com/api/mojo/max/algorithm/backend/cpu/parallelize/parallelize/) · [GPU 教程](https://max.modular.com/gpu/intro-tutorial/)

编译期参数、trait、求值和反射可以生成特化容器及数值 kernel，消除运行时分派和通用元数据处理，同时会增加编译工作和代码变体。内联 MLIR 进一步开放编译器层面的操作能力。[元编程](https://mojolang.org/docs/manual/metaprogramming/) · [编译期求值](https://mojolang.org/docs/manual/metaprogramming/comptime-evaluation/) · [反射](https://mojolang.org/docs/manual/metaprogramming/reflection/)

## 本地实验

[实验脚本](../experiments/mojo-2026-11-11/run.py) · [原始结果](../experiments/mojo-2026-11-11/results.json)

五个反例均被编译器以预期诊断拒绝：类型不匹配、通过不可变参数修改列表、同一列表传给两个可变参数、所有权转移后继续使用、调用可能抛错的函数却未处理。一个正例计算 `comptime N = 6 * 7` 并输出 `42`。六项均符合预期。

性能实验沿用其他专题的五千万步 UInt32 xorshift 循环，五种语言均输出校验值 `376378803`。机器为 Apple M4 Max、128 GiB 内存，运行原生 ARM64 程序；预热后按轮次串行测量五次构建、七次运行。工具链与文件系统已预热，每次构建使用新源码文件名，Zig 使用新本地缓存并关闭增量编译。运行时间包含进程启动与输出。

| 语言 | 构建中位数 | 运行中位数 |
| --- | ---: | ---: |
| Mojo 1.2.0，`-O3` | 1.0233 s | 0.08329 s |
| C／Clang 22.1.8，`-O3` | 0.1368 s | 0.07778 s |
| Rust 1.95.0-nightly，opt-level 3 | 0.1141 s | 0.07830 s |
| Go 1.27.3，默认选项 | 0.1107 s | 0.09186 s |
| Zig 0.16.0，ReleaseFast | 0.1049 s | 0.07853 s |

在这个小型 CPU 工作负载中，Mojo 运行耗时比 C 高约 7%、比 Rust 高约 6%，构建耗时约为 Go 的 9.2 倍、Zig 的 9.8 倍。它展示了有竞争力的标量代码生成，以及本例较高的固定构建成本。大型工程、增量构建、内存分配、SIMD、Python 互操作和 GPU 吞吐均需另测。

安装包每次调用会报告非致命的 Crashpad 初始化警告，构建与运行成功，原始结果保留了该信息。复现时按[官方安装说明](https://mojolang.org/install/)隔离安装，再在四种对照工具链可用的环境中运行 `python3 experiments/mojo-2026-11-11/run.py --mojo-bin /path/to/mojo`。
