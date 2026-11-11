# Rune

[English](rune.md) | 简体中文

[Rune](https://github.com/google/rune) 是实验性系统语言，将接近 Python 的语法、秘密值类型、声明式对象关系和 Structure-of-Arrays 存储结合起来，尤其适合研究复杂对象图的另一种内存管理方式。仓库明确说明项目尚未完成，且**不是 Google 官方支持的产品**。[项目状态](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/README.md)

调研日期为 2026-11-11，源码固定在 `a8fb12f974736f20eaefb1f614df68411dac7bc8`，采用 Apache-2.0 许可。本次研究的是用 C 实现、生成 LLVM IR 并调用 Clang 的编译器。Rune 自举编译器和新版 transformer 的文档中还包含未来规划。[编译驱动](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/src/main.c) · [自举方案](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/compiler_phases.md)

## 正确性与秘密值

Rune 提供类型推断、显式可空类型，默认启用数组边界、整数溢出和已销毁对象访问检查。`-U` 会关闭重要运行时保护。这些检查针对具体非法操作，目前没有通用的程序正确性证明。[语言参考](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#memory-safety)

其特色是秘密属性传播：由 `secret` 值派生的结果保留秘密属性，部分操作选用常数时间实现。参考文档称秘密值不能用于分支和索引，但本地实验发现实现与这一描述存在差异：秘密值索引被拒绝，下面这个**依赖运行时输入的秘密值分支却在默认安全模式、`-O` 下编译成功**：

```text
password = secret(argv[1])
if password == "password" {
  println "leaked"
}
```

传入参数 `password` 会输出 `leaked`。保存的 LLVM IR 包含秘密值比较及通向输出块的条件分支。当前绑定代码只检查 `if` 条件是否为 Boolean，没有拒绝其秘密属性；后端生成普通条件跳转。这是可复现的文档与实现差异，本次没有测量完整的时序攻击。[绑定检查](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/bind/bindexpr.c#L1982) · [分支生成](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/llvm/genllvm.c#L3963) · [实验结果](../experiments/rune-2026-11-11/results.json)

上游 TODO 还列有防优化器破坏的秘密结构体比较、秘密 select 处理和进一步的常数时间测试。参考文档的常数时间定义针对等长输入，也排除了其他侧信道。因此秘密类型很值得研究，但该版本仍存在重要实现缺口。[秘密值语义](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#constant-time-processing-of-secrets) · [TODO](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/TODO)

## 关系式内存管理

类通过声明参与双向链表、一对一关联等关系。Cascade 关系使父对象销毁时递归销毁子对象，生成的清理代码同时更新其他关联对象；不属于 cascade 所有权的类使用引用计数。参考文档还将静态分析和引用环限制作为安全设计的一部分。它把大量指针操作中的维护工作提升到了数据模型层。[内存模型与关系](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#relations)

字段分开存放在数组中，对象引用使用索引表示。遍历少数字段时，可以避免载入无关字段，也能使用更小的引用表示。收益取决于访问模式，不能推导为普遍优于 C／Rust 的布局或分配器；完整对象访问、扩容和大型对象图销毁仍需另测。TODO 仍有销毁安全与内存池方面的改进，因此应结合这些缺口理解文档中的广泛内存安全主张。[数据模型](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/database_design.md) · [内存管理实现](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/transformer/memmanage.c)

## 系统编程、并发与元编程

编译器分析整个程序或独立库，生成 LLVM IR，再通过 Clang 链接原生代码，库边界采用兼容 C 的模型。完整 C++ 互操作、C 指针、内存映射 I/O 声明等底层能力仍在待办中，替代 C++ 的目标范围大于当前已经实现的接口。[编译单元](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#compilation-units) · [系统能力待办](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/TODO)

该快照明确尚不支持多线程。迭代器和关系遍历本身不能说明它提供 actor、结构化任务或数据竞争保障，并发系统编程仍是明显空缺。

元编程是这一方案的核心能力：编译期解释执行的 transformer 可以生成或修改类字段、方法与清理逻辑。内置 `DoublyLinked` 提供了实际实现，本地关系实验也运行了它生成的插入与删除操作。将 transformer 编译为动态库、直接操作 HIR 的方案属于后续设计。[当前 transformer](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/builtin/doublylinked.rn) · [参考说明](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#transformers) · [升级提案](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/transformers.md)

## 本地检查与性能证据

[复现说明](../experiments/rune-2026-11-11/README.md) · [实验脚本](../experiments/rune-2026-11-11/run.py) · [结果](../experiments/rune-2026-11-11/results.json)

未修改的编译器在 Ubuntu 24.04 x86-64 容器中构建成功，依赖 Clang 14、DataDraw、GMP 和 CTTK。六项预期中五项成立：秘密值索引和类型变更被编译器拒绝，溢出和越界在运行时停止，生成的关系方法能插入对象、销毁时移除对象并清空父对象链接。第六项暴露了上述秘密分支被接受的问题。数组越界打印 panic 后以状态 139 退出，整数溢出以状态 1 退出。这些是具体观察，本次未运行完整上游测试集。

宿主是 Apple Silicon，而容器是 x86-64，因此不提供与 macOS 原生 Go／Zig／Rust／C 的耗时比例。后续应在同一台原生 Linux 机器运行所有工具链，分别注明默认安全配置和主动关闭检查的配置。小程序适合测编译器与链接器固定成本，对象图工作负载则能检验布局和销毁设计。

上游包含二叉树和优先队列示例，C++ 对照采用不同分配策略，不能据此给出通用语言排名；仓库自己的队列记录也显示不同工作负载下结果不同。本次没有验证与 Go／Zig 的编译效率对照。[基准源码](https://github.com/google/rune/tree/a8fb12f974736f20eaefb1f614df68411dac7bc8/benchmarks) · [上游观察](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/benchmarks/results.md)
