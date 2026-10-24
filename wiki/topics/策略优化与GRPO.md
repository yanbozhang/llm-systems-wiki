---
id: policy-optimization
module: training
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-policy-optimization-v1]
---
# 策略优化与GRPO

策略优化把模型生成看作带反馈的采样过程。学习时必须记录采样策略、奖励定义、参考约束和评测，才能解释算法实际改变了什么。

前置学习：[偏好学习与DPO](偏好学习与DPO.md)。所属模块：[训练](../modules/训练.md)。

## 学习目标

- 区分策略、参考与奖励。
- 推导组内优势。
- 检查奖励投机。

## 前置知识

需理解偏好学习、采样和均值方差。旧策略用于采样概率比，参考策略用于约束偏离，奖励或验证器用于评价生成，三者不能混为一谈。

## 基本机制

PPO 使用新旧策略的概率比与裁剪目标限制更新，并通常借助价值估计构造优势。DeepSeekMath 的 GRPO 对同一问题采样一组输出，用组内奖励统计估计相对优势，省去独立 critic。理解其公式时要分清旧策略、当前策略和参考策略，裁剪与 KL 约束并非同一项。

依据：[DeepSeekMath 与 GRPO 原论文](https://arxiv.org/html/2402.03300v3)；[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

对同一题采样四个回答，奖励为[0,0,1,1]。组均值0.5，若按总体标准差0.5归一化，优势为[-1,-1,1,1]。所有奖励相同则无区分信号，必须处理零方差。

这是组内相对信号的教学例子，不是完整GRPO损失。真实配方还涉及概率比裁剪、token或序列聚合、KL约束与采样更新频率。结果奖励与过程奖励也对应不同监督设计；不能把一个实现的默认归一化方式当成所有GRPO变体的定义。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[DeepSeekMath 与 GRPO 原论文](https://arxiv.org/html/2402.03300v3)；[Stanford CS336](https://cs336.stanford.edu/spring2025/)。

## 方法演进

GRPO 原文将 outcome supervision 和 process supervision 分开讨论；后续实现可能调整归一化与损失聚合方式。因此这里使用 DeepSeekMath 的固定版本讲原理，不把任意同名 trainer 的默认参数视为原论文定义。

## 适用条件与限制

组内相同奖励会弱化相对学习信号；奖励可被投机利用，验证器本身也可能有漏洞。没有固定模型、任务、样本预算与评估设置时，不能比较不同方法的分数。

## 常见误区

去掉 critic 不代表不需要奖励信号；最终答案正确也不自动验证所有中间解释。训练 reward 与业务成功率要分别统计。

## 实践任务

为一个可校验的小任务分别设计正确性奖励和格式奖励，并列出可能的投机行为。记录组大小、采样温度、归一化与验证器版本；先用人工小样本检查奖励逻辑。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：三类策略/反馈对象分工清楚；推导：组内优势和零方差处理正确；实践：能构造奖励漏洞；评估：独立于训练奖励验证任务能力与失败分布。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

一组四个结果的奖励都为 1，组内相对优势能提供什么区分？若只奖励输出格式，会出现什么偏差？

<details>
<summary>展开答案要点</summary>

组内没有质量差异信号，归一化还须防止零方差。只奖励格式可能让策略优先满足形式而忽略问题内容，需要任务有效性反馈。

</details>

进阶追问：训练奖励持续上升而独立评测下降，能否直接增加训练轮数？

<details>
<summary>展开进阶答案要点</summary>

应先检查奖励过拟合、验证器漏洞、样本分布和约束强度；继续优化错误目标可能扩大问题。

</details>

## 课程与下一步

[DeepSeekMath 与 GRPO 原论文](https://arxiv.org/html/2402.03300v3)；[Stanford CS336](https://cs336.stanford.edu/spring2025/)；[OpenCompass 文档](https://opencompass.readthedocs.io/en/latest/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-policy-optimization-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[DeepSeekMath 与 GRPO 原论文](https://arxiv.org/html/2402.03300v3)；[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)；[TRL 训练文档](https://huggingface.co/docs/trl/index)。

关联阅读：[Agent评测与失败归因](Agent评测与失败归因.md)。
