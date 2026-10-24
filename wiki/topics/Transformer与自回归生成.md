---
id: transformer
module: network
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-transformer-v1]
---
# Transformer与自回归生成

理解一个 token 如何变成下一 token 的分布，是阅读后续训练、缓存与 Agent 文献的共同起点。Transformer 用注意力在位置间交换信息，用逐位置前馈网络变换特征；原始论文是编码器—解码器结构，现代自回归大模型常采用仅解码器结构。

前置学习：[共同基础](../../docs/共同基础.md)。所属模块：[模型网络](../modules/模型网络.md)。

## 基本机制

先由 tokenizer 把文本变成离散 ID，再查 embedding 得到向量。注意力构造 Q、K、V，按 softmax(QKᵀ/√dₖ + M)V 汇聚信息。因果掩码 M 使位置 t 看不到未来位置。每层通过注意力、FFN、残差与归一化变换表示，最后投影到词表并生成概率分布。训练可并行计算已知序列各位置的损失；生成时下一步输入依赖刚产生的 token，因而通常逐步推进。

依据：[Transformer 原论文](https://arxiv.org/html/1706.03762v7)；[LLaMA 原论文](https://arxiv.org/html/2302.13971v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

原始 Transformer 为翻译任务设计；LLaMA 等仅解码器模型保留注意力和前馈结构，调整归一化、激活和位置编码。不要把“Transformer”与某一个聊天产品、参数规模或训练阶段等同。

## 适用条件与限制

常规稠密自注意力的得分矩阵随序列长度平方增长；实际执行的显存还取决于内核是否物化该矩阵。模型输出概率不构成外部世界事实的证明。

## 常见误区

“训练时一次只学一个 token”不准确：因果掩码允许用 teacher forcing 并行学习多个位置；“没有循环网络所以生成可完全并行”也不成立。

## 学习练习

对四个 token 画出因果掩码；解释第四行为什么有四个可见位置。再说明原始编码器注意力与自回归注意力的差别。

<details>
<summary>展开答案要点</summary>

四行的可见位置数依次是 1、2、3、4；未来位置被屏蔽。原始编码器可双向看输入，解码器自注意力限制未来输出。训练的真实历史与生成的采样历史要区分。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-transformer-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[Transformer 原论文](https://arxiv.org/html/1706.03762v7)；[LLaMA 原论文](https://arxiv.org/html/2302.13971v1)。

关联阅读：[预训练目标与数据](预训练目标与数据.md)；[Prefill与Decode](Prefill与Decode.md)；[位置编码与RoPE](位置编码与RoPE.md)。
