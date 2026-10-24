---
id: task-loop
module: agents
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-task-loop-v1]
---
# 业务Agent任务闭环

业务 Agent 的目标是改变外部任务状态。结果要按业务终态判断，过程中的自然语言解释、调用成功和视觉反馈分别是辅助证据。

前置学习：[Harness任务循环](Harness任务循环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 学习目标

- 把用户目标转换成终态契约。
- 区分过程和结果。
- 设计恢复与补偿。

## 前置知识

需要Harness状态机与工具契约。先明确任务输入、允许动作、业务成功和禁止副作用，再选择模型或执行框架。

## 基本机制

将任务定义为初始状态、用户目标、允许动作、成功条件与不可接受副作用。循环读取环境，执行一步，再观察动作效果。对于跨应用任务，记录每一步的产物和可恢复点；成功判断尽量来自可执行的状态检查。

依据：[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

任务“整理两份文档并生成索引”至少要核对来源是否完整、索引是否包含两份资料、链接是否可用、原文件是否被意外覆盖。一次保存成功只覆盖其中一项。

可以用结果表记录：任务ID、初始状态、预期产物、实际产物、成功判据、失败阶段、副作用、是否重试。若重试成功，应保留首次失败，不把最终成功覆盖成“一次完成”。这样才能分析可靠性与恢复成本。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)。

## 方法演进

OSWorld 用真实应用环境、初始配置与执行式评估组织任务；工程指南讨论工具反馈与检查点。首版借用这种任务定义方式，不声称某一通用策略已解决所有应用。

## 适用条件与限制

评估脚本只能覆盖它定义的条件，可能漏掉副作用或与真实用户意图不一致。人工偏好评价、规则判定和执行结果应互相补充。

## 常见误区

“Agent 说已完成”不是验收；截图中出现绿色提示也可能只表明局部动作成功。

## 实践任务

为模拟资料整理任务设计正常、缺资料、重复触发和中途失败四个场景。每个场景明确终态断言与恢复动作，并区分可自动回查和需要人工判断的部分。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：目标与动作分开；推导：验收覆盖完整结果；实践：恢复路径可检查；评估：同时记录首轮成功、重试成功、成本与副作用。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

把“整理三份文档并生成汇总表”写成可验收任务，列出失败后保留的最小恢复信息。

<details>
<summary>展开答案要点</summary>

核对三份来源版本、表格行列与引用、输出位置及重复文件；恢复记录含已处理来源、已产生文件、未完成项与可安全重试的动作。

</details>

进阶追问：文件已经生成，但引用缺失，应算任务成功还是部分成功？

<details>
<summary>展开进阶答案要点</summary>

按事先冻结的任务契约判断。若可追溯引用是目标之一，应报告未满足该项，而不是因为文件存在就判成功。

</details>

## 课程与下一步

[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[Full Stack LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-task-loop-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[构建有效 Agent](https://www.anthropic.com/engineering/building-effective-agents)。

关联阅读：[GUI定位与执行](GUI定位与执行.md)；[AI代码开发与反馈](AI代码开发与反馈.md)；[Agent评测与失败归因](Agent评测与失败归因.md)。
