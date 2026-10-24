# README

**大模型持续学习知识库 · v0.2**

围绕模型网络、训练、推理、Harness、知识库、业务Agent与Benchmark，持续积累可学习、可练习、可查证的知识。

当前包含 **7个模块、35个知识主题、4条学习路径、28项能力目标、57份公开来源**。原有24个主题均已扩写，新增11个Benchmark主题，并整理17个系统学习入口。

从[知识地图](docs/大模型持续学习知识库.md)开始，按[能力地图](docs/能力地图.md)选择希望证明的能力，再查阅[系统学习资源指南](docs/系统学习资源指南.md)。

| 模块 | 主要内容 |
|---|---|
| [模型网络](wiki/modules/模型网络.md) | Transformer、注意力头、RoPE、FFN与归一化 |
| [训练](wiki/modules/训练.md) | 预训练、SFT与LoRA、偏好学习、策略优化 |
| [推理](wiki/modules/推理.md) | Prefill/Decode、KV缓存、分页调度、框架实验 |
| [Harness](wiki/modules/Harness.md) | 状态循环、上下文、记忆、工具协议与Skill |
| [知识库](wiki/modules/知识库.md) | RAG、来源版本、混合检索、图与Wiki |
| [业务Agent](wiki/modules/业务Agent.md) | 任务闭环、GUI、代码开发、失败分析 |
| [Benchmark](wiki/modules/Benchmark.md) | 协议、统计、污染、通用/代码/多模态/Agent/RAG评测、裁判、性能与稳健性 |

学习路径：[基础入门](wiki/paths/基础入门路径.md) · [系统工程](wiki/paths/系统工程路径.md) · [Agent开发](wiki/paths/Agent开发路径.md) · [Benchmark](wiki/paths/Benchmark学习路径.md)。

每个知识单元包含学习目标、前置知识、原理、推导或案例、条件、实践任务和掌握标准。内容成熟度与个人学习进度分开：本版提供实践设计，尚未执行大模型基准或复现实验。

维护入口：[持续更新指南](docs/持续更新指南.md) · [编纂规范](schema/编纂规范.md) · [研究队列](docs/研究队列.md) · [本版变化](wiki/changes/学习体系升级.md)。GitHub Actions每日上海时间08:00巡检来源，候选保存到独立分支；新结论仍经过阅读与复核后更新。
