---
id: agent-loop
module: harness
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-agent-loop-v1]
---
# Harness任务循环

Harness 是围绕模型组织上下文、工具、状态和验证的执行系统。模型产生下一步建议，宿主把它转成受约束的动作，并把真实结果送回下一轮。

前置学习：[共同基础](../../docs/共同基础.md)。所属模块：[Harness](../modules/Harness.md)。

## 基本机制

基本循环为接收目标、观察状态、选择动作、校验参数、执行工具、读取结果、判断是否结束。模型回复“完成”只是一个信号，宿主还要检查任务终态。固定 workflow 由预定步骤驱动；Agent 在运行时决定路径，两者可以在一个系统内组合。

依据：[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)；[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

官方工程经验建议从能解决问题的简单调用或 workflow 开始，再按任务需要加入自主循环。规划、检索和反思都需要可观察的实际收益，不能因组件数量增加就推断系统更可靠。

## 适用条件与限制

长任务必须设置步数、时间、成本和重复动作边界；失败重试前检查是否已产生副作用。本文只定义学习用循环，不代表某个宿主具有全部恢复能力。

## 常见误区

把模型、SDK 和 Harness 当成同一对象，会使排障归因混乱；工具返回成功通常只说明调用层成功，不一定满足用户目标。

## 学习练习

用“填写表单并保存”设计四种状态：待执行、已提交、保存成功、失败待核对。为何超时后不能直接再点一次提交？

<details>
<summary>展开答案要点</summary>

超时不代表服务未处理；重复点击可能产生重复记录。先回读记录或用幂等标识核对，再决定恢复动作。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-agent-loop-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)；[MCP 架构说明](https://modelcontextprotocol.io/docs/learn/architecture)。

关联阅读：[业务Agent任务闭环](业务Agent任务闭环.md)；[工具协议与MCP及Skill](工具协议与MCP及Skill.md)；[Agent评测与失败归因](Agent评测与失败归因.md)。
