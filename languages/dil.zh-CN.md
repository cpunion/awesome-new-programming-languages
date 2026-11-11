# DIL

[English](dil.md) | 简体中文

DIL 是一份 2026 年 10 月的 ChatGPT 逆向观察报告所描述的界面 DSL，结合 Markdown、组件标签和 JavaScript 表达式。研究日期为 2026-11-11，证据限于观察报告与教学图解。[观察者报告](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works)、[图解及证据范围](https://kejun.github.io/demos/chatgpt-intelligent-ui/)

报告描述了组件校验、表达式错误恢复、JavaScript 执行，以及 Worker 和消息边界。正确性保障、分配回收、调度语义和用户元编程能力仍待核验，观察到的接口面向宿主组件与动作。本轮材料未提供可复现编译器和 Go／Zig／Rust／C 对照。

该线索可用于研究流式 UI 语言设计。语言可靠性、沙箱强度和实际性能仍需额外证据。图解声明其交互属于教学演示，页面不执行真实 DIL。[图解源码快照](https://github.com/kejun/demos/blob/150c9dcfc7b62239e2208c258bb87fe0e868f40f/chatgpt-intelligent-ui/index.html)
