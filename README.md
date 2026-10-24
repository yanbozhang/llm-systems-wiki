# README

**大模型持续学习知识库 · v0.1**

围绕模型网络、训练、推理、Harness、知识库和业务 Agent，持续积累可以阅读、练习、查证和修订的知识。首版包含 **6 个模块、24 个核心主题、3 条学习路径、29 份公开来源**。

从[知识地图](docs/大模型持续学习知识库.md)开始，或直接选一条路径：

- [基础入门](wiki/paths/基础入门路径.md)：理解模型、训练、推理与检索。
- [系统工程](wiki/paths/系统工程路径.md)：从注意力、缓存走到服务性能实验。
- [Agent 开发](wiki/paths/Agent开发路径.md)：从任务循环走到工具、记忆和业务评测。

| 模块 | 主要内容 |
|---|---|
| [模型网络](wiki/modules/模型网络.md) | Transformer、注意力头组织、RoPE、FFN 与归一化 |
| [训练](wiki/modules/训练.md) | 预训练、SFT 与 LoRA、偏好学习、策略优化 |
| [推理](wiki/modules/推理.md) | Prefill/Decode、KV Cache、缓存调度、框架与实验 |
| [Harness](wiki/modules/Harness.md) | 任务循环、上下文、记忆、工具与 Skill |
| [知识库](wiki/modules/知识库.md) | RAG、来源接入、混合检索、GraphRAG 与 LLM Wiki |
| [业务 Agent](wiki/modules/业务Agent.md) | 任务闭环、GUI、AI Coding、评测归因 |

每个主题都有机制、演进、条件、误区、练习和答案要点，并能下钻到[原始来源](sources/来源索引.md)。知识页使用普通 Markdown 链接，可直接在 GitHub 阅读，也可作为本地笔记库使用。

维护入口：[持续更新指南](docs/持续更新指南.md) · [编纂规范](schema/编纂规范.md) · [研究队列](docs/研究队列.md) · [变化记录](wiki/changes/初始版本.md) · [LLM Wiki 调研](docs/LLMWiki模式与实现调研.md)。

首版自动化包含结构校验与每日来源候选巡检。**自动发现不等于自动完成专题研究**：新结论经阅读与复核后进入正式页面。没有调用商业模型接口，也没有运行大模型训练或性能复现实验。完整实施边界见[初版范围与验收](docs/初版范围与验收.md)。
