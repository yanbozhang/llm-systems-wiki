---
id: coding-agent
module: agents
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-coding-agent-v1]
---
# AI代码开发与反馈

代码 Agent 的任务包括理解仓库、定位问题、修改、验证与交付。代码可编译、测试通过、修复了用户问题是不同层次的判断。

前置学习：[业务Agent任务闭环](业务Agent任务闭环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 学习目标

- 按契约形成补丁。
- 区分测试缺口与修复。
- 记录可复查证据。

## 前置知识

前置为版本控制、调用链、测试和构建。理解补丁解决的是哪个行为，而不是只追求消除一条错误日志。

## 基本机制

先固定仓库与基线，读取项目约定、调用链和已有验证，再形成最小可解释改动。检查应覆盖变更的行为契约，失败输出回流为下一轮输入。交付记录改了什么、为什么、验证了什么和剩余风险。新写测试必须来源于需求或调用契约，不能简单复制实现逻辑。

依据：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

某函数对空列表崩溃，先核对接口约定：它可能应返回空结果，也可能应明确拒绝输入。若只是把异常吞掉，测试可能不再报错，却把真实失败隐藏成成功。

一份可审阅补丁应包含触发条件、预期与实际行为、修改位置、验证覆盖及未验证范围。评价代码Agent时，既要看任务是否解决，也要看是否引入无关变更、破坏测试或产生不可解释的副作用。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)。

## 方法演进

SWE-bench 把真实仓库与 issue 组织成生成补丁的任务，并提供执行评估；其容器化机制有助于固定环境。不同数据集子集、评估版本和工具预算会改变可比性。

## 适用条件与限制

通过已知测试不能证明没有所有缺陷；修改测试让它适应错误实现也不构成修复。依赖安装、构建失败和业务断言失败需要分开归因。

## 常见误区

把生成行数或提交次数当作成功，会鼓励无效改动。只展示补丁而没有适当验证，也不足以证明满足需求。

## 实践任务

选择一个自建小函数定义契约和反例，在修改前写下期望结果，再比较最小补丁与替代方案。冻结隐藏验证点的设计，不让实现本身决定全部断言。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：问题来自独立契约；推导：反例能区分正确与错误实现；实践：补丁范围可解释；评估：记录环境失败、测试失败和业务失败。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

为“修复空输入导致异常”设计验收：应核对哪些契约？如果原文没有规定空输入行为怎么办？

<details>
<summary>展开答案要点</summary>

核对接口约定、调用方与既有测试，确认返回值或异常语义；若未知，记录问题并选择有依据的行为，不把当前实现当作正确答案。

</details>

进阶追问：一个补丁删除了失败测试后全部变绿，能否作为修复成功的证据？

<details>
<summary>展开进阶答案要点</summary>

不能。要核对测试是否代表有效契约；删除有效断言只减少了验证范围，并未证明行为被修复。

</details>

## 课程与下一步

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[Stanford CS336](https://cs336.stanford.edu/spring2025/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-coding-agent-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。

关联阅读：[Agent评测与失败归因](Agent评测与失败归因.md)。
