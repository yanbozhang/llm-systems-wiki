---
id: policy-optimization
module: training
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-policy-optimization-v1]
---
# 策略优化与GRPO

策略优化把模型生成看作带反馈的采样过程。学习时必须记录采样策略、奖励定义、参考约束和评测，才能解释算法实际改变了什么。

前置学习：[偏好学习与DPO](偏好学习与DPO.md)。所属模块：[训练](../modules/训练.md)。

## 基本机制

PPO 使用新旧策略的概率比与裁剪目标限制更新，并通常借助价值估计构造优势。DeepSeekMath 的 GRPO 对同一问题采样一组输出，用组内奖励统计估计相对优势，省去独立 critic。理解其公式时要分清旧策略、当前策略和参考策略，裁剪与 KL 约束并非同一项。

依据：[DeepSeekMath 与 GRPO 原论文](https://arxiv.org/html/2402.03300v3)；[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

GRPO 原文将 outcome supervision 和 process supervision 分开讨论；后续实现可能调整归一化与损失聚合方式。因此这里使用 DeepSeekMath 的固定版本讲原理，不把任意同名 trainer 的默认参数视为原论文定义。

## 适用条件与限制

组内相同奖励会弱化相对学习信号；奖励可被投机利用，验证器本身也可能有漏洞。没有固定模型、任务、样本预算与评估设置时，不能比较不同方法的分数。

## 常见误区

去掉 critic 不代表不需要奖励信号；最终答案正确也不自动验证所有中间解释。训练 reward 与业务成功率要分别统计。

## 学习练习

一组四个结果的奖励都为 1，组内相对优势能提供什么区分？若只奖励输出格式，会出现什么偏差？

<details>
<summary>展开答案要点</summary>

组内没有质量差异信号，归一化还须防止零方差。只奖励格式可能让策略优先满足形式而忽略问题内容，需要任务有效性反馈。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-policy-optimization-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[DeepSeekMath 与 GRPO 原论文](https://arxiv.org/html/2402.03300v3)；[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)；[TRL 训练文档](https://huggingface.co/docs/trl/index)。

关联阅读：[Agent评测与失败归因](Agent评测与失败归因.md)。
