# Goose

[English](goose.md) | 简体中文

[Goose](https://github.com/aardappel/goose) 是 Wouter van Oortmerssen 设计的系统语言，围绕编译器管理的数据栈、稳定引用、紧凑内联数据和隔离工作线程构建。它把整个程序编译为 C，也提供进程内 TinyCC 运行方式。

调研日期为 2026-11-11，源码固定在 [`f4637bfb342fb70d42bea0474eab9e62a3c99d68`](https://github.com/aardappel/goose/tree/f4637bfb342fb70d42bea0474eab9e62a3c99d68)。本地构建报告 `goose f4637bf (runtime d521138194f1)`。编译器使用 C++ 实现，采用 Apache-2.0 许可。[构建定义](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/CMakeLists.txt)

## 通过引用根和限制保障正确性

引用与 slice 具有推断得到的 root，描述目标依赖哪块存储存活。编译器拒绝把引用存入比其 root 更长寿的位置，也阻止在仍有活引用时收缩数组。允许多个别名，无需 Rust 式独占借用或生命周期注解。只读内容用 `const` 表达，`let` 本身只限制重新绑定。[生命周期规则](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#12-lifetimes-roots-stores-and-writability)

无法证明安全的索引保留边界检查，`checkfree fn` 则要求编译器证明检查已消除。无符号算术回绕，有符号算术在发布构建中回绕、调试构建中检查，因此不能从内存安全推导为拒绝整数溢出。池中槽位复用后，旧引用可能读到新对象，这仍是程序员需要处理的逻辑错误。[索引类型与 checkfree](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#15-index-types-and-checkfree-functions) · [算术](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#3-scalars-and-arithmetic) · [池](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#14-reusable-pools)

本次未建立程序满足规格的通用证明。实际贡献在于由编译器执行、并有测试支持的受限存储模型。

## 数据栈与紧凑表示

动态值存放在编译器选定的数据栈上，底层预留虚拟地址空间。增长推进指针，退出作用域恢复栈顶；每个栈至多有一个位于顶部的可增长值，因此增长不移动已有元素，引用可以跨越增长保持有效，嵌套值的存储回收也可以只恢复一个指针。扁平嵌套数据、可变大小枚举和窄相对引用有助于减少填充、指针和复制成本。[内存模型](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#4-where-values-live) · [运行时实现](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/runtime/runtime_impl.h)

相应限制也很具体：递归调用不能任意保留可增长的临时数据，可变大小元素数组若要随机访问需要额外建立引用索引，长期存活且频繁修改的数据通常需要显式池。“没有堆分配器”描述的是语言数据模型；线程和队列等运行时设施仍会分配内存，虚拟地址预留也有操作系统成本。[递归限制](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#19-recursion) · [线程运行时](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/runtime/runtime_threads.h)

## 系统编程与并发

Goose 可以输出 C、构建可执行文件和动态库、通过类型化声明调用 C，并导出函数和头文件。外部 C 必须遵守声明的类型，不能在调用结束后保留借用参数。数据栈依赖虚拟内存支持，仅能输出可移植 C 还不足以证明适用于裸机。全程序编译、尚有限的 OS／库覆盖，以及没有运行时函数指针和逃逸闭包，也是实际约束。[C 接口](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#24-calling-c-and-being-called-from-c) · [规范与待办](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/goose_spec.md#appendix-b-todo--open-items)

`thread_fn` 工作者具有自己的数据栈，以及所用全局变量的副本。参数和类型化队列消息必须是内部不含引用或 slice 的扁平值，从而避免在线程之间共享可变 Goose 存储。复制、分配和同步由运行时内部实现，队列仍可能阻塞或死锁。线程通过显式 spawn／wait 管理，contained worker 可把中止情况报告给等待者。TinyCC 无法提供所需线程局部存储，因此使用线程的程序必须构建为原生程序。[线程模型](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#22-threads)

## 元编程

泛型根据类型和推断的存储 root 特化。函数值与尾随代码块是编译期实体，可以生成直接调用，无需运行时闭包对象。`const for` 可以遍历字段、枚举变体、类型列表或编译器已知的常量，`const if` 在特化时选择片段，适合序列化和通用数据变换。规范明确说明这一机制不提供任意编译期执行；逃逸闭包和运行时函数指针仍不可用。[泛型与函数值](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/reference.md#18-generics-and-function-values) · [展开实现](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/src/typecheck_expansion.h)

## 本地实验

另有[跨语言内存研究](../research/memory-models.zh-CN.md)检查变长记录：Goose 在标记的构建与遍历阶段没有调用插桩的 malloc，逐条分配的 C 实现调用 10,001 次，手写紧凑 C 区域调用一次。运行时启动和虚拟映射单独记录，结果仅检查分配调用点，不提供 RSS 或速度排名。

[实验脚本](../experiments/goose-2026-11-11/run.py) · [结果](../experiments/goose-2026-11-11/results.json) · [上游检查日志](../experiments/goose-2026-11-11/upstream-checks.txt)

八项本地探针均符合预期。四个编译反例覆盖类型不匹配、引用逃逸、持有活引用时收缩数组，以及写入 `const` 内容；运行时越界被检测。三个正例分别验证引用跨数组增长保持有效、字段反射统计出两个字段，以及工作线程将自己的全局变量改为 `7`、父线程仍保持 `1`。

上游测试脚本以 `--nocgen --no-jit -j4` 运行通过，包含 1,528 项解析／往返／类型检查、1,958 项类型错误用例和 80 项解析错误用例。此次主动跳过 C 后端执行与 TinyCC 测试，八项本地探针另行提供了原生执行证据；没有运行完整 sanitizer 或图形测试集。

五千万步 UInt32 xorshift 对照使用 Apple M4 Max、128 GiB 内存，预热后计时五次构建和七次运行。按轮次串行构建，每次使用新源码文件名；Goose 运行时目标文件缓存和其他工具链已预热，Zig 使用新本地缓存并关闭增量编译。所有程序输出校验值 `376378803`，运行耗时包含启动与输出。

| 语言 | 构建中位数 | 运行中位数 |
| --- | ---: | ---: |
| Goose f4637bf，`-O2`，Clang `-O2` | 0.21078 s | 0.07625 s |
| C／Clang 22.1.8，`-O3` | 0.13091 s | 0.07550 s |
| Rust 1.95.0-nightly，opt-level 3 | 0.10860 s | 0.07556 s |
| Go 1.27.3，默认选项 | 0.10907 s | 0.08926 s |
| Zig 0.16.0，ReleaseFast | 0.10296 s | 0.07705 s |

在这个小程序中，Goose 构建耗时约为 Go 的 1.93 倍、Zig 的 2.05 倍，运行耗时与 C、Rust 相差约 1%。Goose 运行时目标文件缓存为空时，首次构建耗时 0.7175 秒。这些结果尚未验证其独特的分配、布局或多核优势，计时也没有使用不做优化的 TinyCC 进程内运行方式。[构建行为](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/docs/command_line.md#3-building-an-executable)

上游另有 16 类工作负载，对比多种 C++ 实现、安全 Rust 和内存使用，在 Windows／AMD 硬件上测量，并包含 Goose 落后的项目。它们反映具体布局和完整生命周期成本，不能当作本地复测或通用排名；带日期的基准报告也比 README 的摘要比例更精确。[基准报告](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/bench/results.md) · [基准设计](https://github.com/aardappel/goose/blob/f4637bfb342fb70d42bea0474eab9e62a3c99d68/bench/design.md)

复现时用 CMake 的 Release 配置构建固定版本，将可选 builtin 库保持为空，再在 Clang、Rust、Go、Zig 可用的环境运行 `python3 experiments/goose-2026-11-11/run.py --goose-bin /path/to/goose`。脚本会建立隔离的临时 `GOOSE_HOME`。
