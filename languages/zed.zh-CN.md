# Zed

[English](zed.md) | 简体中文

[Zed](https://github.com/zedlanguage/zed) 是 Luke Hutchison 开发的数据流语言，以不可变定义和多层 map 为中心，目标是结合集合处理、增量计算、编译器检查和自动并行。本次研究对象是 `zedlanguage/zed` 的编程语言。

调研日期为 2026-11-11，源码固定在 [`4598c420ab65fba1942f12a0888bc9f638fba9f9`](https://github.com/zedlanguage/zed/tree/4598c420ab65fba1942f12a0888bc9f638fba9f9)。**项目仍在构建中，README 明确说明其介绍的是完成后的语言**，实现进度和源码对应的可用核心范围更小。项目采用 MIT 许可。[README](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/README.md) · [实现进度](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/STATUS.md)

## 以正确性为目标的设计

设计将失败表示为结果联合类型中的值，提供范围与精化检查，并要求明确处理查找缺失、集合重映射中的键冲突。例如改变 map 的键可能使多个值落到同一位置，需要选择保留、丢弃或合并；过滤失败行也可能改变聚合结果的含义。这些设计很适合数据变换，但不能据此认定 README 的全部示例已能运行。[示例与检查](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/README.md#checks-at-compile-time)

源码和进度记录已包含检查器、类型精化、Presburger 推理、阶段求值、参考解释器、ZIR 降低和差分测试。规划中的 `law` 区分证明、穷举检查与抽样测试，只有已证明的定律才能用于优化重写。但更完整的证明体系仍需实现证据：本次快照的 `zed-cert/src/lib.rs` 只有五行模块注释，描述未来的独立证书检查器；仅有 crate 名称不足以说明当前已经检查重写证书。[检查器源码](https://github.com/zedlanguage/zed/tree/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc-check/src) · [证书 crate](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-cert/src/lib.rs)

## 内存管理

这部分已有具体实现。ZIR 内存规划器推断借用，在最后使用处安排引用计数复制与释放，并融合解构操作；配套执行模型逐步检查计数。原生运行时使用标签和载荷表示值，常见标量无需装箱，其余值进入引用计数堆。单元释放后更新 generation，从而识别访问已释放单元的旧引用。这为研究自动内存管理成本提供了实际基础。[内存规划器](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc-zir/src/zir/memory.rs) · [运行时堆](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-rt/src/heap.rs)

完整语言还计划消除中间集合、在唯一引用时原地更新、检查分配上界，以及摊销释放成本。这些目标需要与目前针对标量、元组和闭包的内存规划分别验证。本次没有完成分配量或常驻内存基准。

## 并发、系统支持与元编程

设计从依赖关系推导并行工作，承诺不同核心数下结果一致，包含浮点归约，并列出外部事件等例外。**当前运行时源码明确将工作窃取和 wave 调度器安排在后续层次**，因此尚不能据此认定完整自动多核模型已经可用。[运行时范围](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-rt/src/lib.rs)

当前原生路径使用 Cranelift 并链接 Rust 运行时。MLIR／LLVM、GPU、分布式执行、硬件综合和微控制器在项目布局和计划中属于后续目标。C 导入导出、外部内存布局和有界分配注解已有设计说明，本次未完成端到端验证，系统编程适用性仍需继续研究。[原生后端](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-native/src/lib.rs) · [仓库布局](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/docs/layout.md)

元编程方向包括以普通求值执行编译期代码、部分求值、结构反射、将函数源码作为数据，以及编译生成代码。语法定义驱动的解析与序列化、符号代数是主要设计示例。仓库已有阶段处理模块，但这本身无法验证完整反射、语法机制和携带证明的重写能力。[阶段处理源码](https://github.com/zedlanguage/zed/tree/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc-stage/src)

## 本地检查与性能边界

[复现说明](../experiments/zed-2026-11-11/README.md) · [记录结果](../experiments/zed-2026-11-11/results.json)

使用已安装的 Rust 1.99，在 macOS／ARM64 上构建未修改的原生编译器失败，原因包括运行时依赖 Linux 的 `sysinfo`、`MAP_STACK` API。只调用 `zedc` 库的解释器入口也因包定位使用 `OFlags::PATH` 而构建失败。这说明该快照存在平台移植限制，不能据此推断 Linux 构建失败。[栈实现](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zed-rt/src/stack.rs) · [包定位](https://github.com/zedlanguage/zed/blob/4598c420ab65fba1942f12a0888bc9f638fba9f9/crates/zedc/src/place.rs)

三个上游 kernel 位运算测试在 macOS 上运行通过，检查机器整数路径与精确算术路径的一致性，以及拒绝超出定义域的操作数。这只验证了一个小组件；本次没有成功运行完整 Zed 程序，也没有性能对照结果。

因此暂不提供与 Go／Zig 的编译耗时比例或与 Rust／C 的执行比例。当前原生后端为控制编译成本，刻意默认使用 Cranelift 的 `opt_level=none` 和单遍寄存器分配器，更强的 ZIR 优化器留待后续实现。后续基准应明确这一取舍，并加入集合处理、分配量和确定性多核扩展测试。
