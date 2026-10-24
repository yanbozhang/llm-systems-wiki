---
id: agent-evaluation
module: agents
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-agent-evaluation-v1]
---
# Agent评测与失败归因

评测首先固定任务与成功条件，再记录模型、Harness、工具、环境和预算。只有控制这些变量，才能解释一次改动是否有帮助。

前置学习：[业务Agent任务闭环](业务Agent任务闭环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 基本机制

区分单步定位或工具调用正确率、完整任务成功率、成本与耗时、副作用和恢复能力。每次运行保留任务 ID、环境版本、动作轨迹、终态判据和失败阶段。可把失败候选分为目标理解、检索、规划、定位、执行、环境、验证与预算，再依据实际日志归因。

依据：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

SeeClick、OSWorld 与 SWE-bench 展示了不同层次的测试任务。本文不合并不同基准的分数，也不把某年的论文模型结果当作当前排行榜。

## 适用条件与限制

单次成功可能含随机性；重复次数、失败分布、选择样本的方法和统计不确定性需要说明。评估器本身应检查假阳性与假阴性。

## 常见误区

用模型自评分代替外部验收会形成自证循环；将所有超时归因于规划错误也会掩盖环境或资源问题。

## 学习练习

同一任务运行五次，四次成功一次工具超时。如何报告，而不是只选一次最好轨迹？

<details>
<summary>展开答案要点</summary>

报告五次运行及成功口径、耗时和错误类别；超时单独回查是否已产生副作用。样本很小，不外推总体成功率，也不把重试后结果覆盖首次失败。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-agent-evaluation-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[SeeClick 原论文](https://arxiv.org/html/2401.10935v1)。

关联阅读：[推理框架与性能实验](推理框架与性能实验.md)；[策略优化与GRPO](策略优化与GRPO.md)。
