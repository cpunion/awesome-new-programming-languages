# Bend 2

## 研究快照

- 研究日期为 2026-11-11。
- 研究对象为 `bendlang/bend` 当前主分支的 Bend 2。
- 固定提交为 `d18110b6d6e9a70bb8814b2a8d8db092e301e540`，提交时间为 2026-11-10，CLI 自报版本为 `2.0.40`。该快照包含版本发布后的主分支修改。项目采用 Apache-2.0 许可证。[固定源码](https://github.com/bendlang/bend/tree/d18110b6d6e9a70bb8814b2a8d8db092e301e540)、[版本定义](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/main.ts#L33)、[许可证](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/LICENSE)

当前项目已从早期 Bend 1 演进为依赖类型、仿射资源约束、定律证明和 CPU／GPU 编译结合的语言。官方说明两代程序不兼容，BendRT 论文也明确说明当前运行时采用新的所有权与调度设计。早期围绕 HVM 和交互网的资料有其历史适用范围。[项目说明](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/README.md#limitations)、[BendRT 设计与相关工作](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L579)

## 六个维度的初步判断

| 维度 | 当前判断 | 主要依据 |
| --- | --- | --- |
| 程序正确性 | 值得重点研究，能将用户明确写出的性质纳入证明检查 | 依赖类型、相等性证明、终止检查，以及可额外运行的 BendTT 内核 |
| 内存正确性和效率 | 所有权设计有吸引力，实际成本随共享和数据表示变化 | 原生后端无追踪式 GC，按所有权释放，部分共享使用引用计数，数组可原地修改 |
| 系统编程 | 能编写部分宿主环境应用和计算模块，作为通用底层语言仍有明显能力缺口 | 已有 IO、文件、TCP／UDP、进程和 foreign 效应；原生库输出、数值类型和底层控制仍受限 |
| 编译和执行效率 | 本机小型整数循环接近 C／Rust，完整原生构建耗时高于 Go／Zig 对照 | 本项目可复现实测；官方多工作负载数据同时呈现优势与明显慢项 |
| 并发模型 | 纯计算采用显式 fork-join，IO 通过事件循环协调 | 所有权分配任务参数，性能依赖负载均衡，取消与共享数组有额外边界 |
| 元编程能力 | 擦除参数、类型级计算与闭合模板实参支持泛型和专门化 | `~` 模板编译期展开，证明和类型求值也会影响检查时间 |

以上判断综合下文的官方资料、源码分析和本项目实验。内存峰值、大型项目构建、GPU 以及长期运行服务的表现仍待实测。

## 程序正确性的保障

### 类型、资源与终止

Bend 2 使用显式标注较多的双向类型检查。函数和代数数据类型有静态类型，模式匹配要求覆盖对应情况，依赖类型允许返回类型随输入变化。默认绑定最多消费一次，`+` 绑定允许重复使用，其类型必须属于可复制的 `Data`。闭包和数组受到仿射约束，通用类型属于 `Type`。`-` 标注的参数用于类型和证明，运行时会擦除。[类型与函数](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#types-and-functions)、[数量标注与种类](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#quantities)

安全片段要求递归调用在参数上结构递减，并限制定义调用次序。检查按从左到右的字典序识别递减参数，因此参数顺序会影响程序是否被接受。当前写法对互递归、匹配计算结果、循环和反复调用闭包有额外约束。高阶函数可以使用编译期 `~` 模板参数，以编译期展开换取可重复调用。[递归与终止](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#recursion-and-termination)、[模板](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#templates)

### 定律与证明

`law` 声明一个待证明的类型，配对的 `def` 给出证明。相等命题可以使用归纳、模式匹配、重写和反身性完成。项目惯例把性质放在 `LAWS.bend`，实现及其证明通过 `PROOF.bend` 导入，并运行 `bend PROOF.bend` 作为检查入口。未完成或无法成立的证明会导致检查失败。[定律与证明](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#laws-and-proofs)

**分析判断**，保障范围由实际形式化的命题、命题与实现的关联，以及检查入口的导入闭包决定。例如，排序函数的规格需要同时表达输出有序和元素及其重数保持。仅有“输出有序”的规格会允许总是返回空列表的实现。持续集成也需要覆盖证明入口，才能在修改实现后重新验证这些性质。

### 已形式化的部分与可信边界

BendTT 的 Lean 源码包含合流性、类型保持、进展、空类型性质、运行代码终止、检查器可靠性、一致性和相等性证明充分性等声明与证明。理论采用 `Type : Type`，通过区分运行代码与擦除位置，以及限制运行代码复制函数等机制建立一致性论证。这里的结论具有论文和源码中写明的前提。[元理论和机械化说明](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendTT/main.typ#L773)、[Lean 内核及证明](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/bendtt.lean)

`--verdict` 将前端检查后的程序转换为 BendTT，再交给该内核复核。可信边界仍包含 Bend 源码解析、转换到 BendTT 的过程、后端代码生成、原生运行时、外部编译器及宿主效应。官方明确列出转换和解析尚未经过证明，运行时论文也将 C 运行时正确性列为待验证部分。[转换实现](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/safe.ts)、[机械化的覆盖范围](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendTT/main.typ#L1065)、[运行时限制](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L616)

需要结合任务理解的边界还包括以下几项。

- `@unsafe` 可以放宽递归等限制。普通运行支持这类程序，证明检查会追踪相关依赖，并对受影响的定义报告失败。foreign 代码的实现同样超出前端检查范围。[检查入口与依赖追踪](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/main.ts#L923)
- F32 运算目前通过公理式接口描述。NaN payload、格式化舍入等情况存在后端差异，依赖这些细节的程序需要按具体后端审查。[已知语义差异](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/WONTFIX.txt)
- 理论与有限机器资源之间存在运行时限制。原生 Nat 上限为 `2^48 - 1`，引用计数、块尺寸和任务队列也有上限，耗尽时会终止运行。[运行时资源上限](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L616)、[设计限制记录](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/WONTFIX.txt)

### 本项目的行为实验

本轮编写并执行了 11 项探针。下表中的“拒绝”均指进程返回失败并出现相应诊断，“通过”包含输出或诊断核对。[探针源码](../experiments/bend-2026-11-11/run.py)、[原始结果](../experiments/bend-2026-11-11/results.json)

| 探针 | 观察结果 |
| --- | --- |
| 对任意 Nat 的自反相等定律 | 检查通过 |
| 结构递归函数等于输入的归纳证明 | 检查通过 |
| 尝试用反身性证明 `0n == 1n` | 拒绝，诊断指出等式两侧不同 |
| 留下尚未提供证明的定律 | 拒绝，报告 TODO |
| 在同一结果中使用数组两次 | 拒绝，报告重复消费 |
| 对同一个闭包调用两次 | 拒绝，报告重复消费 |
| 把 Bool 当作 U32 返回 | 拒绝，报告类型不匹配 |
| Bool 匹配遗漏 False 分支 | 拒绝，报告分支覆盖不足 |
| 递归调用传入原参数 | 拒绝，报告缺少递减 |
| 把上述递归标为 `@unsafe` 后进行证明检查 | 拒绝，报告 unsafe 依赖 |
| 8 元素数组写入索引 1，再读取索引 9 | 原生程序输出 42，表现为索引回绕 |

本轮也使用本机已安装的 Lean 4.34.1 检查完整 `bendtt.lean` 并构建内核，再通过官方支持的 `BENDTT` 环境变量执行 `--verdict`。两个正例进入内核并通过，其余证明负例在前置检查阶段被拒绝。官方自动构建路径固定要求 Lean 4.34.0，本次采用 4.34.1 是显式的实验工具链选择。构建过程、版本和结果保存在原始数据中。

## 内存正确性与效率

### 原生所有权和回收

原生后端把项表示为 64 位值。小值可以直接放入字中，其他值通过位置访问统一堆。编译器根据所有权放置移动、借用、共享和释放操作。独占节点在消费时可立即释放，部分可共享数据通过引用计数管理。大型结构的释放仍需要遍历和计数操作，其耗时取决于结构规模。[内存表示与回收设计](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L284)

该机制给内存正确性提供了可检查的语言约束，同时仍依赖运行时正确实现这些操作。共享数据可能产生计数、原子操作及额外节点成本。原生后端的按所有权回收机制与 JS 后端的宿主 GC 有不同成本模型。[所有权操作](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L304)、[JS 后端](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L526)

### 数组、字符串和资源

- 安全片段中的数组沿单一所有权传递。编译后使用平坦块，读写可以直接索引并原地更新，复制通过显式接口完成。普通索引按容量掩码回绕，本轮原生探针验证了这一点。对“越界应报错”的需求，可以通过封装范围检查或携带合法性证明的索引接口来表达。[数组说明](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#arrays)、[数组实现](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/base.bend#L2759)
- 源语言把数组描述为树。普通 get／set 有专门的平坦实现，直接通过树构造器拆分再重组则会产生复制。运行时论文给出遍历树式数组时 `O(n log n)` 的字复制成本。[数组表示与优化](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L329)
- `Array.fork` 通过 `@unsafe` 暴露共享数组，`Array.get_unchecked` 同样标记为 unsafe。使用这些接口时需要自行维护相应约束。[共享数组与原子操作](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/base.bend#L2675)、[unchecked 读取](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/base.bend#L2783)
- `String` 在语言中是字符链表，文本处理的分配和局部性值得关注。官方 lexer 基准明确采用 Bend 链表字符串与 C 字节访问的自然实现。[String 定义](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/base.bend#L73)、[lexer 设计](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bench/runtime/lexer/main.bend)
- File／Socket 使用仿射句柄。效应接口通过显式 close 关闭描述符，Chan 的共享和释放另由引用计数处理。**由接口与表示推断**，文件句柄的仿射限制允许丢弃，文件最终关闭需要程序管理。[效应所有权约定](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/EFFECTS.md#the-c-side)、[File.close](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/effs/file_close.c)、[句柄表示](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/comp.ts#L5346)

本轮内存研究的证据主要来自机制与源码。五语言循环几乎只做整数运算，内存效率还需要树、共享结构、数组、文本及资源生命周期等工作负载的峰值与分配测量。官方 SPACE 数据使用主机 RSS，GPU 总驻留量需要另行测量。[官方测量脚本](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/gen_pins.ts)

## 系统编程能力

| 能力 | 当前观察 | 对本项目关注点的影响 |
| --- | --- | --- |
| 原生执行 | C 输出由 clang 构建宿主可执行程序 | 已具备原生程序路径 |
| OS 接口 | Base 包含文件、TCP／UDP、进程、环境、时间等，还提供图形与音频接口 | 能开发部分应用层系统工具与服务 |
| 并发 | IO 由事件循环协调，部分阻塞工作交给辅助线程，纯计算可显式 fork-join | 需要结合调度和效应模型评估服务行为 |
| FFI | foreign 效应提供 `.c` 和 `.js` 实现，C 代码嵌入生成的程序 | 可连接宿主能力，边界代码需要遵守运行时所有权约定 |
| 导出原生库 | 当前 C 输出含程序入口，稳定的纯函数库及头文件输出列为后续工作 | 嵌入现有 C／Rust 工程的路径仍有限 |
| 数值能力 | 当前核心数值为 Nat、U32、F32，U64／F64 列为后续工作 | 64 位二进制协议、地址计算和双精度数值需求受到影响 |
| 布局与分配器控制 | 已查指南未提供通用的 C 兼容布局、裸指针操作或用户分配器控制接口 | 对 ABI、设备内存布局和精确资源控制的需求仍需单独核验 |
| 平台 | 官方以 Linux／macOS 为宿主，GPU 为 Metal／CUDA，Windows 使用 WSL | 平台支持范围较集中 |

表中能力来自指南、Base 和当前构建实现，原生库及数值限制来自项目的限制记录。[IO 与并发](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#io-and-concurrency)、[效应扩展](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/EFFECTS.md)、[Base API](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/base.bend)、[构建实现](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/main.ts#L481)、[限制记录](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/WONTFIX.txt)

**分析判断**，Bend 当前更适合研究可证明的计算核心，以及与宿主服务组合的实现方式。通用内核、驱动和裸机编程还需要 freestanding 目标、硬件接口、布局和分配器等证据。此次研究覆盖的原生运行时依赖宿主内存映射、线程和事件循环。[宿主运行时实现](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/comp.ts#L4694)

## 并发模型

纯计算通过多调用绑定显式创建 fork-join 任务。调度器采用固定分派的任务网格，调用需要把工作分得较均匀。每个任务拥有自己的参数，安全片段中的纯函数与仿射约束支持独立执行。`!` 在受支持的位置将计算交给 GPU，当前 CPU 与 GPU 按阶段交替工作。共享原子数组通过 `@unsafe` 接口暴露，相关程序需要维护额外约束。[并行语法与约定](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#parallelism)、[任务调度](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L369)、[共享数组接口](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/base.bend#L2675)

IO 使用单个事件循环交错推进计算，等待套接字、时间或通道的计算让出执行机会，部分阻塞效应由辅助线程处理。`IO.fork`／`IO.join` 提供启动和等待结果的方式，剩余计算全部等待时运行时可以报告死锁。`IO.within` 返回超时后，输掉竞争的操作仍会继续执行，因此需要结合实际 API 设计任务和资源生命周期。JS 后端顺序执行纯计算中的并行调用。[IO 与并发](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#io-and-concurrency)、[效应执行与辅助线程](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/EFFECTS.md#the-c-side)

本轮并发结论来自源码与文档。任务调度开销、负载偏斜、通道争用、取消和服务吞吐仍需专门工作负载验证。

## 元编程能力

擦除参数可用于泛型类型与证明，类型本身可以通过函数计算。`~` 模板把实参当作语法在编译期替换，实参需要闭合，可以引用顶层定义。不同模板实参产生不同展开实例，使高阶调用可以在编译期专门化，也会增加生成代码和后端编译工作。[数量与擦除](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#quantities)、[模板规则](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#templates)

当前编译期设施集中于这些显式机制，项目还列出 traits、类型类和模板之外的宏系统等能力缺口。类型规约和证明检查可能遇到昂贵计算或栈溢出，运行代码的终止保障与编译器检查过程的成本需要分别评估。大型模板库的实例数、代码体积、诊断体验和编译时间尚待实测。[语言限制](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/README.md#limitations)、[检查器复杂度边界](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/WONTFIX.txt)

## 编译效率与执行效率

### 编译路径

原生构建大致经过读取与检查、编译期展开和擦除、C 生成、clang 优化与链接。使用 GPU 的程序还有设备程序构建步骤。官方原生构建当前默认采用 `-O3`，每个程序生成一个 C 文件。主线工具缺少独立编译与原生增量构建，仓库另有 `tools/bend-cache` 为开发时的证明检查缓存结果。[CLI 构建路径](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/main.ts#L416)、[原生构建限制](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/README.md#limitations)、[检查缓存工具](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/tools/bend-cache/README.md)

大量显式标注和有限推断有助于常见检查路径的速度。类型转换和求值仍可能昂贵，项目的限制记录列出了指数级及栈溢出的情况。官方快速证明检查数据需要结合命题结构、类型规约和所用检查入口来理解。[检查器限制](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/WONTFIX.txt)、[官方检查基准](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bench/checker/_pin_/apple_m4_max.txt)

### 本项目五语言微基准

工作负载为从种子 1 开始执行 5,000 万步 xorshift32，最后打印校验和 `376378803`。五种实现使用相同移位和异或运算，并按 U32 语义执行。该循环提供小型原生编译、单核整数运算和进程启动的对照。[完整源码与命令](../experiments/bend-2026-11-11/run.py)、[原始测量](../experiments/bend-2026-11-11/results.json)

测量环境为 Apple M4 Max、16 核、128 GiB 内存、macOS 27.0.1。工具链为 Bun 1.2.21、Bend 源码 CLI 2.0.40、clang 22.1.8、Rust 1.95.0-nightly、Go 1.27.3、Zig 0.16.0。Rust 使用本机 PATH 中的 rustup 工具链。Bend 使用完整源码 CLI 入口，官方安装版的启动成本可以进一步测量。

每种构建先预热一次，再计时五次，标准库及文件系统缓存保持预热。每轮生成新的文件名与注释以触发应用重新构建，Zig 使用新的本地缓存目录并关闭增量编译。运行先预热一次，再串行轮转计时七次。Bend 固定单线程、关闭 GPU。构建计时包含检查、生成、后端优化与链接，运行计时包含进程启动和打印。详细命令与每次耗时保存在 JSON 中。

| 语言 | 构建耗时中位数 | 构建范围 | 运行耗时中位数 |
| --- | --- | --- | --- |
| Bend 2 | 0.903 s | 0.805–1.131 s | 0.1107 s |
| Go | 0.143 s | 0.141–0.215 s | 0.1291 s |
| Zig | 0.145 s | 0.142–0.146 s | 0.1106 s |
| Rust | 0.138 s | 0.133–0.204 s | 0.1106 s |
| C | 0.177 s | 0.172–0.222 s | 0.1102 s |

优化选项分别使用 Bend 默认原生构建、Go 默认优化构建、Zig `ReleaseFast`、Rust `opt-level=3` 和 C `-O3`。Zig 示例链接 libc 并调用 printf，Go 使用 fmt，Rust 使用 println，因此构建时间也包含各自入口与依赖的成本。表中的范围给出五次构建的最小值和最大值。

按未取整的中位数计算，Bend 完整构建耗时约为 Go 的 6.30 倍、Zig 的 6.24 倍。Bend 执行耗时约为 C 的 1.005 倍、Rust 的 1.001 倍，差距处于本轮测量波动范围内。

本次比较只支持该小型整数循环的结论。大型项目的冷构建、单文件编辑、泛型与模板规模、证明规模和 GPU 编译仍需对应实验。编译测量也存在本机后台活动带来的波动。

### 官方多工作负载结果

下表摘录固定快照中 `apple_m4_max.txt` 的数据。该文件标注测量日期为 2026-09-17，测量版本为 `d0db7b3e`。数据由项目方测量，本轮仅核对文件和脚本。每个执行时间单位为秒，倍数为 Bend 单核耗时除以对应 C 耗时。[官方原始数据](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bench/runtime/_pin_/apple_m4_max.txt)、[测量脚本](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/gen_pins.ts)

| 工作负载 | Bend 单核 | C 单核 | 耗时倍数 | Bend 多核 | Bend GPU |
| --- | --- | --- | --- | --- | --- |
| tree-matmul | 2.064 | 2.964 | 0.70× | 0.226 | 0.231 |
| nbody | 5.758 | 5.126 | 1.12× | 0.516 | 0.059 |
| mandelbrot | 4.473 | 3.750 | 1.19× | 0.395 | 0.057 |
| merkle | 4.222 | 3.423 | 1.23× | 0.422 | 0.071 |
| queens | 5.406 | 3.599 | 1.50× | 0.455 | 0.933 |
| lexer | 2.144 | 1.036 | 2.07× | 0.198 | 1.075 |
| hashmap | 2.741 | 0.622 | 4.41× | 0.238 | 0.521 |

这组数据覆盖部分接近 C 的单核工作负载，也出现文本和哈希表的明显差距。lexer 与 hashmap 的源文件说明了表示差异，例如链表字符串、boxed 链节点与 C 的字节及索引节点池。数据有助于研究各语言自然实现的成本，进一步优化比较需要记录表示和算法选择。[Bend lexer](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bench/runtime/lexer/main.bend)、[C hashmap](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bench/runtime/hashmap/main.c)

官方 GPU 和多核数据反映了不同硬件资源下的扩展表现。同硬件资源的比较还需要 C／Rust 多线程实现，以及等价 CUDA／Metal 实现。本轮尚未复现上述官方工作负载，也未扩展其 Rust 对照。

### 并行能力的条件

并行来自显式的多调用绑定，`!` 标记在支持的位置将调用交给 GPU。调度器采用固定分派的 fork-join 设计，依赖程序把工作分得较均匀。负载平衡属于程序需要满足的性能条件。当前 CPU 与 GPU 按阶段交替计算，JS 后端顺序执行。[并行语法](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/guide/GUIDE.md#parallelism)、[调度设计](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L369)、[GPU 执行边界](https://github.com/bendlang/bend/blob/d18110b6d6e9a70bb8814b2a8d8db092e301e540/bend2/docs/BendRT/main.typ#L477)

## 与研究目标的匹配

Bend 最值得继续研究的是把依赖类型证明、仿射所有权、擦除和高效原生执行放进同一条工具链。此次本机实验提供了小型正确性机制和整数执行的直接证据。作为目标语言的进一步判断，还需要大型编辑构建、分配密集程序、文本处理、共享结构、实际服务和跨后端语义的测量。

按本项目的六个维度，当前可以记录为以下状态。

- 正确性机制已有明确设计、实现和形式化材料，两个示例证明经过独立内核复核。
- 内存管理机制完成源码研究，峰值、分配成本和长期资源生命周期仍待工作负载验证。
- 宿主应用接口已经存在，广泛系统编程所需的数值类型、ABI、布局和目标平台控制仍有限。
- 小型单核整数执行达到本轮 C／Rust 对照附近的耗时，Go／Zig 级的原生编译体验仍有差距。大型项目结论保留为待测。
- 并发设计围绕纯计算 fork-join 与 IO 事件循环展开，任务平衡和超时后的生命周期具有明确约束。
- 元编程具有擦除、类型级计算和显式模板，生成规模及其检查成本还需大型程序测量。

## 实验复现

使用空目录保存固定源码，然后在本项目根目录运行实验。`--lean-bin` 指向已经安装且同时含 `lean` 和 `leanc` 的目录，省略它时仅运行行为探针和性能实验。脚本会核对 Bend 提交、诊断、退出码与执行校验和，产物放在临时目录，结果写到指定 JSON 文件。

```sh
git clone https://github.com/bendlang/bend.git /tmp/bend-research-source
git -C /tmp/bend-research-source checkout d18110b6d6e9a70bb8814b2a8d8db092e301e540

python3 experiments/bend-2026-11-11/run.py \
  --bend-source /tmp/bend-research-source \
  --lean-bin /path/to/lean-4.34.1/bin \
  --output /tmp/bend-research-results.json
```

五语言实验使用 Python 3、Bun、clang、rustc、Go、Zig 和 Git。本轮脚本采用 macOS 的 sysctl 记录硬件信息。Bend 的联网版本检查被定向到本机关闭端口，计时过程使用本地源码。
