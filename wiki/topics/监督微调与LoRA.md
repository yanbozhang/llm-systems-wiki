---
id: sft
module: training
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-sft-v1]
---
# 监督微调与LoRA

SFT 用输入及示范输出训练模型遵循任务格式和行为。LoRA 是参数更新方式，两者处在不同维度：SFT 可以全参数训练，也可以使用 LoRA。

前置学习：[预训练目标与数据](预训练目标与数据.md)。所属模块：[训练](../modules/训练.md)。

## 学习目标

- 验证标签mask与对话模板。
- 计算LoRA参数。
- 设计数据和适配器消融。

## 前置知识

需掌握预训练损失和线性层shape。SFT是学习任务，LoRA是参数化更新方式；数据格式、损失位置与可训练参数应分别登记。

## 基本机制

对问答训练，先固定对话模板、角色和结束符，再确定哪些 token 参与损失。常见做法只对目标回复计算损失，但必须核对 trainer 的真实 mask 行为。LoRA 将权重更新写为 ΔW=BA，冻结基础权重，学习低秩矩阵；若 W 为 d×k、秩为 r，新增参数为 r(d+k)，而非 dk。

依据：[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)；[LoRA 原论文](https://arxiv.org/html/2106.09685v2)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

设一条训练样本包含系统提示、用户问题和助手回复。若目标是只训练回复部分，前两段及padding的label需要按训练器约定屏蔽；先打印文本对应的token位置与有效label位置，比只检查总loss更容易发现模板错误。

LoRA若使用W=W₀+(α/r)BA，应说明缩放约定。秩r改变参数数目和更新容量，α/r改变更新尺度；不同实现也可能采用不同缩放。对同一任务比较全参数与LoRA时，应固定数据、划分和评测，再分别记录可训练参数、显存及目标质量。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[LoRA 原论文](https://arxiv.org/html/2106.09685v2)；[Hugging Face LLM Course](https://huggingface.co/learn/llm-course/chapter1/1)。

## 方法演进

InstructGPT 将示范数据 SFT 作为后续偏好训练的起点；LoRA 解决任务适配的可训练参数成本。任务数据、训练阶段、优化器和适配方式应分别登记。

## 适用条件与限制

低秩更新不自动消除数据偏差或遗忘；实际训练显存还包含激活、梯度与优化器状态。能合并 adapter 时可评估合并推理，不能推断所有多适配器服务都没有额外开销。

## 常见误区

“LoRA 是一种奖励学习算法”错误；训练 loss 很低也可能只是记住示范答案或泄漏模板。

## 实践任务

手工标注两条对话样本的训练位置，一条含多轮对话，一条有padding。随后设计“正确模板/错误模板”和“不同秩但相同数据”的两组独立比较，避免一次改变全部变量。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：区分训练阶段和适配方式；推导：能核算低秩参数；实践：能定位mask错位；评估：关注独立任务、长度和格式，不只看训练loss。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

当 d=k=4096、r=8，比较 ΔW 全参数与低秩参数数目。再列出检查对话模板至少需要的两项内容。

<details>
<summary>展开答案要点</summary>

全矩阵为 16,777,216 个参数，低秩为 65,536 个；这里只算一个权重。模板需检查角色边界、终止符以及 label mask 是否与目标回复一致。

</details>

进阶追问：使用LoRA后输出大量重复角色标签，首先应怀疑秩太小吗？

<details>
<summary>展开进阶答案要点</summary>

应先排查训练与推理chat template、终止符和label mask是否一致，再讨论模型容量与训练超参数。

</details>

## 课程与下一步

[LoRA 原论文](https://arxiv.org/html/2106.09685v2)；[Hugging Face LLM Course](https://huggingface.co/learn/llm-course/chapter1/1)；[Stanford CS336](https://cs336.stanford.edu/spring2025/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-sft-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[InstructGPT 原论文](https://arxiv.org/html/2203.02155v1)；[LoRA 原论文](https://arxiv.org/html/2106.09685v2)；[TRL 训练文档](https://huggingface.co/docs/trl/index)。

关联阅读：[偏好学习与DPO](偏好学习与DPO.md)。
