---
id: agent-evaluation
module: agents
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-agent-evaluation-v1]
---
# Agent评测与失败归因

评测首先固定任务与成功条件，再记录模型、Harness、工具、环境和预算。只有控制这些变量，才能解释一次改动是否有帮助。

前置学习：[业务Agent任务闭环](业务Agent任务闭环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 学习目标

- 建立分层评测。
- 按轨迹归因。
- 衔接Benchmark模块。

## 前置知识

需要任务闭环与成功判据。把任务能力、运行可靠性和评估器正确性分成三个检查对象，避免模型自评形成循环证明。

## 基本机制

区分单步定位或工具调用正确率、完整任务成功率、成本与耗时、副作用和恢复能力。每次运行保留任务 ID、环境版本、动作轨迹、终态判据和失败阶段。可把失败候选分为目标理解、检索、规划、定位、执行、环境、验证与预算，再依据实际日志归因。

依据：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

五个任务中三项首次成功、一项重试后成功、一项失败，可以分别报告首轮成功3/5、允许一次重试后的成功4/5。不能只保留四条成功轨迹后报告100%。

进一步按检索、规划、定位、执行、环境、验证与预算标记失败，需要实际轨迹支持；标签只是待核验的归因假设。Benchmark模块负责评测协议、统计与代表基准，本页保留面向业务落地的失败分析。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)。

## 方法演进

SeeClick、OSWorld 与 SWE-bench 展示了不同层次的测试任务。本文不合并不同基准的分数，也不把某年的论文模型结果当作当前排行榜。

## 适用条件与限制

单次成功可能含随机性；重复次数、失败分布、选择样本的方法和统计不确定性需要说明。评估器本身应检查假阳性与假阴性。

## 常见误区

用模型自评分代替外部验收会形成自证循环；将所有超时归因于规划错误也会掩盖环境或资源问题。

## 实践任务

为五个模拟任务填写结果表，至少包含一次结果未知和一次评估器误判。然后设计怎样复核假阳性、怎样保留重试历史及怎样比较两版Harness。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：评测对象分层；推导：分母与重试口径正确；实践：归因有轨迹证据；评估：给出不确定性和适用范围，不用一次成功外推总体能力。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

同一任务运行五次，四次成功一次工具超时。如何报告，而不是只选一次最好轨迹？

<details>
<summary>展开答案要点</summary>

报告五次运行及成功口径、耗时和错误类别；超时单独回查是否已产生副作用。样本很小，不外推总体成功率，也不把重试后结果覆盖首次失败。

</details>

进阶追问：一个模型在工具调用基准领先，是否可以直接替换桌面任务Agent？

<details>
<summary>展开进阶答案要点</summary>

不能直接推断。桌面任务还需要感知、状态恢复、环境知识和终态验证，应在目标任务上进行受控评估。

</details>

## 课程与下一步

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)；[HELM 评测框架](https://raw.githubusercontent.com/stanford-crfm/helm/main/README.md)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-agent-evaluation-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[SeeClick 原论文](https://arxiv.org/html/2401.10935v1)。

关联阅读：[推理框架与性能实验](推理框架与性能实验.md)；[策略优化与GRPO](策略优化与GRPO.md)。
