---
id: task-loop
module: agents
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-task-loop-v1]
---
# 业务Agent任务闭环

业务 Agent 的目标是改变外部任务状态。结果要按业务终态判断，过程中的自然语言解释、调用成功和视觉反馈分别是辅助证据。

前置学习：[Harness任务循环](Harness任务循环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 基本机制

将任务定义为初始状态、用户目标、允许动作、成功条件与不可接受副作用。循环读取环境，执行一步，再观察动作效果。对于跨应用任务，记录每一步的产物和可恢复点；成功判断尽量来自可执行的状态检查。

依据：[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

OSWorld 用真实应用环境、初始配置与执行式评估组织任务；工程指南讨论工具反馈与检查点。首版借用这种任务定义方式，不声称某一通用策略已解决所有应用。

## 适用条件与限制

评估脚本只能覆盖它定义的条件，可能漏掉副作用或与真实用户意图不一致。人工偏好评价、规则判定和执行结果应互相补充。

## 常见误区

“Agent 说已完成”不是验收；截图中出现绿色提示也可能只表明局部动作成功。

## 学习练习

把“整理三份文档并生成汇总表”写成可验收任务，列出失败后保留的最小恢复信息。

<details>
<summary>展开答案要点</summary>

核对三份来源版本、表格行列与引用、输出位置及重复文件；恢复记录含已处理来源、已产生文件、未完成项与可安全重试的动作。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-task-loop-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。

关联阅读：[GUI定位与执行](GUI定位与执行.md)；[AI代码开发与反馈](AI代码开发与反馈.md)；[Agent评测与失败归因](Agent评测与失败归因.md)。
