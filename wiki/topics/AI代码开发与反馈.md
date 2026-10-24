---
id: coding-agent
module: agents
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-coding-agent-v1]
---
# AI代码开发与反馈

代码 Agent 的任务包括理解仓库、定位问题、修改、验证与交付。代码可编译、测试通过、修复了用户问题是不同层次的判断。

前置学习：[业务Agent任务闭环](业务Agent任务闭环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 基本机制

先固定仓库与基线，读取项目约定、调用链和已有验证，再形成最小可解释改动。检查应覆盖变更的行为契约，失败输出回流为下一轮输入。交付记录改了什么、为什么、验证了什么和剩余风险。新写测试必须来源于需求或调用契约，不能简单复制实现逻辑。

依据：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

SWE-bench 把真实仓库与 issue 组织成生成补丁的任务，并提供执行评估；其容器化机制有助于固定环境。不同数据集子集、评估版本和工具预算会改变可比性。

## 适用条件与限制

通过已知测试不能证明没有所有缺陷；修改测试让它适应错误实现也不构成修复。依赖安装、构建失败和业务断言失败需要分开归因。

## 常见误区

把生成行数或提交次数当作成功，会鼓励无效改动。只展示补丁而没有适当验证，也不足以证明满足需求。

## 学习练习

为“修复空输入导致异常”设计验收：应核对哪些契约？如果原文没有规定空输入行为怎么办？

<details>
<summary>展开答案要点</summary>

核对接口约定、调用方与既有测试，确认返回值或异常语义；若未知，记录问题并选择有依据的行为，不把当前实现当作正确答案。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-coding-agent-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。

关联阅读：[Agent评测与失败归因](Agent评测与失败归因.md)。
