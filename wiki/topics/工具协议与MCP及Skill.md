---
id: tools-skills
module: harness
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-tools-skills-v1]
---
# 工具协议与MCP及Skill

工具定义可调用能力，MCP 规范宿主与服务之间的上下文交换，Skill 描述可复用任务方法。三者职责不同，可以组合使用。

前置学习：[Harness任务循环](Harness任务循环.md)。所属模块：[Harness](../modules/Harness.md)。

## 基本机制

MCP 采用 host、client、server 架构；宿主维护连接并管理模型如何使用资源。规范中的 tools、resources、prompts 各有语义。Agent Skills 用包含 SKILL.md 的目录描述能力，入口元数据用于选择，激活后读取正文，所需资源再按引用读取。这种分层加载减少无关材料占用。

依据：[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)；[Agent Skills 规范](https://agentskills.io/specification)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

从单个函数工具到标准协议，主要改变发现、连接与交换方式；从一段提示词到 Skill，主要改变任务方法的组织与复用方式。它们不会自动替代宿主的状态机或业务结果检查。

## 适用条件与限制

是否执行有副作用的动作由宿主和用户授权边界决定；工具输出应作为不可信数据处理。具体协议与可选字段会演进，实践时固定规范版本。

## 常见误区

“装了 MCP 就有长期记忆”没有依据；“Skill 里的说明天然比用户要求优先”也不是协议赋予的性质。

## 学习练习

将“查询论文、把摘要写成主题页、发布变更”分别映射到工具、Skill 与 Harness 责任。

<details>
<summary>展开答案要点</summary>

工具提供检索和文件能力；Skill 约定阅读、证据与写作步骤；Harness 管理授权、顺序、失败恢复和发布判断。具体分工是本仓库的设计示例。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-tools-skills-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)；[Agent Skills 规范](https://agentskills.io/specification)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。

关联阅读：[GraphRAG与LLMWiki](GraphRAG与LLMWiki.md)。
