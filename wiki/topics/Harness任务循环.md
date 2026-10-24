---
id: agent-loop
module: harness
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-agent-loop-v1]
---
# Harness任务循环

Harness 是围绕模型组织上下文、工具、状态和验证的执行系统。模型产生下一步建议，宿主把它转成受约束的动作，并把真实结果送回下一轮。

前置学习：[共同基础](../../docs/共同基础.md)。所属模块：[Harness](../modules/Harness.md)。

## 学习目标

- 画出可恢复状态机。
- 区分模型与宿主责任。
- 定义停止和重试条件。

## 前置知识

应先理解一次模型调用和工具调用的区别。任务目标、环境状态、计划文本与实际执行记录需要各自有身份，不能用一段对话摘要替代全部状态。

## 基本机制

基本循环为接收目标、观察状态、选择动作、校验参数、执行工具、读取结果、判断是否结束。模型回复“完成”只是一个信号，宿主还要检查任务终态。固定 workflow 由预定步骤驱动；Agent 在运行时决定路径，两者可以在一个系统内组合。

依据：[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)；[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

以“查询库存后生成草稿”为例，状态可分为待查询、已查询、待写草稿、已写待验证、完成。工具超时后进入“结果未知”，而不是直接退回待写状态；下一步应回查草稿是否已创建。

每次状态转移记录输入、工具结果、产物定位和是否允许重试。模型可以建议下一步，但宿主要约束可用工具、参数、预算和终态。固定工作流与模型决策可以混用，例如查询和保存由确定步骤控制，内容组织由模型完成。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)。

## 方法演进

官方工程经验建议从能解决问题的简单调用或 workflow 开始，再按任务需要加入自主循环。规划、检索和反思都需要可观察的实际收益，不能因组件数量增加就推断系统更可靠。

## 适用条件与限制

长任务必须设置步数、时间、成本和重复动作边界；失败重试前检查是否已产生副作用。本文只定义学习用循环，不代表某个宿主具有全部恢复能力。

## 常见误区

把模型、SDK 和 Harness 当成同一对象，会使排障归因混乱；工具返回成功通常只说明调用层成功，不一定满足用户目标。

## 实践任务

为一个无真实副作用的文件整理任务画状态图，枚举工具失败、重复返回、结果未知与用户更改目标四种情况。把恢复检查点写成结构化表格，并说明哪些动作幂等。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：责任分工清楚；推导：每个状态都有可解释出口；实践：能从检查点恢复；评估：按最终产物验收，不按模型自称完成验收。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

用“填写表单并保存”设计四种状态：待执行、已提交、保存成功、失败待核对。为何超时后不能直接再点一次提交？

<details>
<summary>展开答案要点</summary>

超时不代表服务未处理；重复点击可能产生重复记录。先回读记录或用幂等标识核对，再决定恢复动作。

</details>

进阶追问：多加一个反思步骤是否必然提高成功率？

<details>
<summary>展开进阶答案要点</summary>

不能保证。它增加调用和延迟，应与简单循环在同一任务、预算和判据下对比，并检查是否引入重复动作。

</details>

## 课程与下一步

[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)；[Full Stack LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-agent-loop-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)；[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)。

关联阅读：[业务Agent任务闭环](业务Agent任务闭环.md)；[工具协议与MCP及Skill](工具协议与MCP及Skill.md)；[Agent评测与失败归因](Agent评测与失败归因.md)。
