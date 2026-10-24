---
id: tools-skills
module: harness
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-tools-skills-v1]
---
# 工具协议与MCP及Skill

工具定义可调用能力，MCP 规范宿主与服务之间的上下文交换，Skill 描述可复用任务方法。三者职责不同，可以组合使用。

前置学习：[Harness任务循环](Harness任务循环.md)。所属模块：[Harness](../modules/Harness.md)。

## 学习目标

- 区分工具Schema与任务方法。
- 设计协议错误处理。
- 验证副作用边界。

## 前置知识

前置是任务循环、输入输出契约和JSON等结构化表示。理解协议负责传输与发现，宿主仍负责如何把能力用于当前目标。

## 基本机制

MCP 采用 host、client、server 架构；宿主维护连接并管理模型如何使用资源。规范中的 tools、resources、prompts 各有语义。Agent Skills 用包含 SKILL.md 的目录描述能力，入口元数据用于选择，激活后读取正文，所需资源再按引用读取。这种分层加载减少无关材料占用。

依据：[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)；[Agent Skills 规范](https://agentskills.io/specification)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

以天气查询工具为例，Schema要求城市和日期；Skill可以规定先消歧城市、核对日期，再组织回答；Harness决定是否需要用户补充信息、超时如何处理、何时结束。三者共同工作，但不能互相替代。

参数合法不代表语义正确：把北京传成同名地点、日期跨时区，仍可能获得HTTP成功却答错。对于写操作还要区分“计划执行”“已执行”“结果未知”，保留回读能力。工具返回中的文字不能自行提升为宿主运行规则。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)；[Agent Skills 规范](https://agentskills.io/specification)。

## 方法演进

从单个函数工具到标准协议，主要改变发现、连接与交换方式；从一段提示词到 Skill，主要改变任务方法的组织与复用方式。它们不会自动替代宿主的状态机或业务结果检查。

## 适用条件与限制

是否执行有副作用的动作由宿主和用户授权边界决定；工具输出应作为不可信数据处理。具体协议与可选字段会演进，实践时固定规范版本。

## 常见误区

“装了 MCP 就有长期记忆”没有依据；“Skill 里的说明天然比用户要求优先”也不是协议赋予的性质。

## 实践任务

为一个只读查询工具写输入、输出和错误表，再为一个模拟写工具加幂等键与回读接口。对缺字段、错误类型、语义歧义、超时和重复请求分别指定宿主动作。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：三种职责分工正确；推导：错误路径完整；实践：可构造语义错误但Schema合法的案例；评估：工具调用有效率和任务成功率分别计数。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

将“查询论文、把摘要写成主题页、发布变更”分别映射到工具、Skill 与 Harness 责任。

<details>
<summary>展开答案要点</summary>

工具提供检索和文件能力；Skill 约定阅读、证据与写作步骤；Harness 管理授权、顺序、失败恢复和发布判断。具体分工是本仓库的设计示例。

</details>

进阶追问：模型生成了合法JSON，是否代表正确调用了工具？

<details>
<summary>展开进阶答案要点</summary>

还需检查工具选择、参数含义、授权边界与执行结果。合法序列化只是最外层检查。

</details>

## 课程与下一步

[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)；[Agent Skills 规范](https://agentskills.io/specification)；[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-tools-skills-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)；[Agent Skills 规范](https://agentskills.io/specification)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。

关联阅读：[GraphRAG与LLMWiki](GraphRAG与LLMWiki.md)。
