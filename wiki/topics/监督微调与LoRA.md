---
id: sft
module: training
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-sft-v1]
---
# 监督微调与LoRA

SFT 用输入及示范输出训练模型遵循任务格式和行为。LoRA 是参数更新方式，两者处在不同维度：SFT 可以全参数训练，也可以使用 LoRA。

前置学习：[预训练目标与数据](预训练目标与数据.md)。所属模块：[训练](../modules/训练.md)。

## 基本机制

对问答训练，先固定对话模板、角色和结束符，再确定哪些 token 参与损失。常见做法只对目标回复计算损失，但必须核对 trainer 的真实 mask 行为。LoRA 将权重更新写为 ΔW=BA，冻结基础权重，学习低秩矩阵；若 W 为 d×k、秩为 r，新增参数为 r(d+k)，而非 dk。

依据：[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)；[LoRA 原论文](https://arxiv.org/html/2106.09685v2)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

InstructGPT 将示范数据 SFT 作为后续偏好训练的起点；LoRA 解决任务适配的可训练参数成本。任务数据、训练阶段、优化器和适配方式应分别登记。

## 适用条件与限制

低秩更新不自动消除数据偏差或遗忘；实际训练显存还包含激活、梯度与优化器状态。能合并 adapter 时可评估合并推理，不能推断所有多适配器服务都没有额外开销。

## 常见误区

“LoRA 是一种奖励学习算法”错误；训练 loss 很低也可能只是记住示范答案或泄漏模板。

## 学习练习

当 d=k=4096、r=8，比较 ΔW 全参数与低秩参数数目。再列出检查对话模板至少需要的两项内容。

<details>
<summary>展开答案要点</summary>

全矩阵为 16,777,216 个参数，低秩为 65,536 个；这里只算一个权重。模板需检查角色边界、终止符以及 label mask 是否与目标回复一致。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-sft-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)；[LoRA 原论文](https://arxiv.org/html/2106.09685v2)；[TRL 训练文档](https://huggingface.co/docs/trl/index)。

关联阅读：[偏好学习与DPO](偏好学习与DPO.md)。
