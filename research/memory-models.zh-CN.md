# 内存安全、减少分配与降低所有权管理负担

[English](memory-models.md) | 简体中文

调研日期：2026-11-11。**这三个目标可以在有用的程序范围内同时实现。** 自动插入引用计数并复用存储、推断区域分配，都是实际存在的路线。现有证据尚未证明某个受调研语言可以同时提供任意可变对象图、及时回收、自由共享和最佳分配表现，且没有相应成本或限制。

关键在于由谁管理所有权：编译器可以在内部跟踪它，而普通源码不需要所有权注解或显式转移。这本身就是有价值的进步。仅仅没有所有权检查器，并不代表生命周期已经自动安全。

## 怎样理解证据

本文的内存安全关注安全子集内的边界、初始化、类型正确访问和生命周期有效性。它不自动包含无泄漏、应用对象身份不失效、无数据竞争和资源不泄漏。运行时及外部代码的正确性仍然重要；核心演算的证明，也需要与完整编译器、运行时的保证范围分开理解。

分配需要分别观察：创建了多少逻辑对象、调用多少次分配器、累计申请多少字节、预留多少虚拟地址空间、峰值活数据和实际驻留内存。池可以减少 malloc 次数，却仍保留大量存储；提前释放可以降低峰值，却不减少分配次数。此前的整数循环无法回答这些问题。

“非 GC”也需要明确：这里区分追踪式收集与自动引用计数。引用计数仍有维护和回收成本，即使用户完全不写所有权管理代码。

## 证据最扎实的路线：自动引用计数与复用

PLDI 2021 的 Perceus 已在 Koka 实现：自动插入精确引用计数，在唯一引用时复用匹配的构造器存储。论文针对规定的核心演算给出形式化结果，其中 garbage-free 结论有无引用环的前提。后续 frame-limited reuse 工作进一步处理复用策略造成的内存滞留。这是有原始论文和实现支持的研究贡献。[Perceus 论文](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/perceus-tr-v4.pdf) · [有界复用研究](https://www.microsoft.com/en-us/research/publication/reference-counting-with-frame-limited-reuse-extended-version/)

Koka 源码可以写“生成一条新链表”，实现却在输入独占时原地改写节点。若旧值仍被共享，就必须保留它，相同操作可能需要分配。论文没有给出任意可变环图或全部并发成本的通用解决方案，也不能据此推出零分配或完整编译器已被验证。[Koka 复用机制](https://koka-lang.github.io/koka/doc/book.html#why-fbip)

后续 FP²（ICFP 2023）更进一步：在受限线性演算中检查完全原地执行函数，并在规定前提下证明不分配及常量栈空间性质。Koka 提供 `fip`／`fbip` 注解，带来有用的算法级契约，同时有用法与唯一性条件，也不保证共享调用者从不复制。本地 Koka 3.2.9 实验中，合法的 `fip` 反转可以运行；一个错误声明为 `fip` 的分配函数被报告警告，却仍然构建成功。因此不能仅凭当前编译器默认构建成功就认证分配契约成立。[FP² 论文](https://www.microsoft.com/en-us/research/uploads/prod/2023/05/fbip.pdf)

Koka 手册仍将其定位为研究语言，库与包管理尚有缺口。这些分配研究不能直接证明它适合全面替代 Rust／C 的系统代码；本轮也没有为 Koka 或 Lean 新增 Go／Zig 编译耗时或 Rust／C 执行效率对照。[项目范围](https://koka-lang.github.io/koka/doc/book.html#getstarted)

Lean 同样提供了实际例子：自动引用计数、构造器复用和部分写时复制原语。普通函数式代码可以复用存储，无需用户编写所有权转移，但共享会改变成本。[Lean 运行时参考](https://lean-lang.org/doc/reference/latest/Run-Time-Code/Reference-Counting/)

区域推断也有既有研究：Tofte 和 Talpin 的工作早于这些项目，并在 ML Kit 实现。这提供了技术背景，不代表 Goose 使用了完全相同的算法。Goose 的新意应从稳定引用、内联变长表示、目标位置构造及限制条件的具体组合来判断。[1997 年区域内存管理论文](https://www.sciencedirect.com/science/article/pii/S0890540196926139)

## 本轮新增实验

[源码与复现](../experiments/memory-models-2026-11-11/README.md) · [原始结果](../experiments/memory-models-2026-11-11/results.json)

- **Goose 记录集合**：构建一万条包含变长名字的记录，并读取每个名字的全部字节。插桩后的生成 C 在工作区间内没有调用 malloc／calloc／realloc。启动阶段仍分配运行时元数据，并建立两个虚拟内存映射；因此这不代表零内存使用或操作系统不分配页面。
- **C 对照**：逐条分配名字的实现调用 10,001 次 malloc；手写紧凑区域的实现调用 1 次。三者校验值一致。这说明 Goose 自动化了有效的布局与分配策略，无法据此推导 C 做不到同样的分配效果。
- **Lean 复用**：对一千个小自然数执行相同的纯函数链表转换。输入独占时，插桩的生成 C 调用点没有新建链表构造器；保留原输入时，新建 1,000 个。两个结果校验值均为 500500，保留的原输入仍为 499500。计数不覆盖预编译库和头文件辅助函数内部的分配。
- **Koka 3.2.9**：启用和关闭复用时输出一致，包含共享原输入不变。启用时生成 C 将可复用存储传给链表构造器，关闭时传入空复用标记。这里验证的是代码生成，没有测量 Koka 的分配次数或性能比例。
- **Koka 分配契约**：合法 `fip` 反转运行成功；没有复用额度却新建链表节点的 `fip` 函数被诊断为发生分配，但默认设置仍允许构建和运行。报告诊断与强制拒绝需要分别评价。

这些实验验证了机制，没有证明完整内存安全、比较总内存排名，也没有测量长期服务、引用环、并发和 RSS 行为。

## 已收录语言的判断

### Goose：受限存储模型内，分配自动化有实效

实测版本 `f4637bf` 通过推断 root 和活跃性检查保护引用，编译器分配的数据栈、目标位置构造和嵌套内联值避免逐对象分配。另核对的更新主线 `32a4f445d8a94b22874a28469f95f69ba3ac31dd` 增加了其他功能，相关内存模型未变。这是有本地证据支持、值得重视的工程整合，但没有证据说明它给出了消除通用内存管理取舍的新定理。[内存模型](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/reference.md#4-where-values-live)

用户仍要安排所有者、作用域、池和表示方式。递归中的可增长局部数据、紧凑变长元素的随机访问、逃逸函数值受到限制，池复用也不会自动使旧对象身份失效。适合按区域处理的数据流水线；长期可变对象图仍有明显设计负担。[限制与池](https://github.com/aardappel/goose/blob/32a4f445d8a94b22874a28469f95f69ba3ac31dd/docs/tutorial.md#18-limitations)

### Gojo、Mojo：降低表达负担，所有权决策仍在

Gojo `215e07c` 保留借用、`inout`、`sink` 及 Rc／Arc 的共享选择。符合条件的纯内存值可以在最后使用处释放，减少滞留；小对象分配和部分 Box 复用处理的是其他成本。这些是有用的实现改进，用户仍参与所有权管理。[提前释放](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/drops.md) · [执行模型](https://github.com/egoist/gojo/blob/215e07c8f016203c52a68e91db9d7097e8e4ff4b/docs/spec.md#14-execution-model)

Mojo 1.2.0 使用所有权、origin、可变访问约定和显式转移。ASAP 销毁可以减少滞留，值表示和特化可以避免部分分配，但这些机制不会自动消除所有权选择，也不保证减少堆请求次数。不受跟踪的 origin 和 unsafe 操作还有额外责任。[所有权](https://mojolang.org/docs/manual/values/ownership/) · [生命周期](https://mojolang.org/docs/manual/values/lifetimes/) · [销毁](https://mojolang.org/docs/manual/lifecycle/death/)

### Bend 2：语言理论有分量，仿射约束仍显式存在

`d18110b` 通过仿射消费与选择性共享指导原生回收，数组有平坦的专门表示并支持原地更新，其他值仍使用运行时堆。程序员需要遵守仿射使用和显式复制规则。其类型理论证明对规定演算提供了重要证据，翻译、代码生成、运行时和 unsafe 功能另有可信边界。它把正确性与高效执行结合起来，但没有实现严格意义上对所有权完全透明的通用系统编程。[运行时设计](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ) · [研究专题](../languages/bend.md)

### Rune：关系式所有权可以自动维护对象关系

`a8fb12f` 的关系声明会生成链接和清理代码，cascade 所有权可以避免部分引用计数，SoA 字段数组摊销对象存储。用户设计关系模型，减少逐个维护指针的工作。这是基于 DataDraw 思路的有趣组合，但还不能证明任意变长字段都减少分配，也无法给未完成的实现认证完整内存安全。此前秘密分支被接受属于另一项安全发现，不能单凭它否定内存模型。[语言参考](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/g3doc/rune_reference.md#memory-safety) · [待办](https://github.com/google/rune/blob/a8fb12f974736f20eaefb1f614df68411dac7bc8/TODO)

### Zed：自动规划已有核心，广泛能力尚未证实

已检查的 `4598c42` 有实际 ZIR 内存规划器、借用推断、最后使用释放和引用计数运行时。更新主线 `63662d8d7f1646ff6230275f1f270dae9747de2a` 中相关文件未变。完整集合融合、广泛后端支持及完整验证体系仍需实现证据；证书 crate 仍只有模块注释。本地 macOS 构建限制阻止了端到端内存实验，因此暂不能把设计组合当作已经验证的能力。[内存规划器](https://github.com/zedlanguage/zed/blob/63662d8d7f1646ff6230275f1f270dae9747de2a/crates/zedc-zir/src/zir/memory.rs) · [证书 crate](https://github.com/zedlanguage/zed/blob/63662d8d7f1646ff6230275f1f270dae9747de2a/crates/zed-cert/src/lib.rs)

### Zig、Odin、C3、Blood 和 DIL

Zig、Odin、C3 让显式分配、arena、临时区域和清理更方便，但仍是手动管理内存的系统语言。区域辅助设施或 defer 不会自动解除生命周期责任，其通用指针模型不满足完整的自动安全要求。这里依据文档判断，没有为三者新增内存实验。[Zig 生命周期责任](https://ziglang.org/documentation/master/#Lifetime-and-Ownership) · [Odin 分配器](https://odin-lang.org/docs/overview/#allocators) · [C3 内存管理](https://c3-lang.org/language-common/memory/)

本轮没有可验证的 Blood 内存规范或可运行实现。DIL 现有材料描述界面 DSL，没有建立独立的原生内存模型，二者均不足以判断是否实现上述目标。[Blood 笔记](../languages/blood.zh-CN.md) · [DIL 笔记](../languages/dil.zh-CN.md)

## 怎样证明更强的突破

更有说服力的结果，需要同时给出明确安全子集、很少的源码管理工作、规定的回收策略，并在独占与共享树、环图、变长记录、长期增删及跨线程传递中提供可复现的分配和活跃性测量。对照应包含 C／Rust 中设计合理的区域与池，也包含常见的逐对象分配实现。

当前证据支持重点关注 **Goose 的区域型数据与紧凑表示**，以及 **Koka／Lean 的自动引用计数与复用**。二者都能减少大量手动工作。若进一步要求任意对象图和及时自动回收，就需要具体评估新增成本或限制；不能据此把最初三个目标说成逻辑上不可兼得。
