---
id: position
module: network
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-position-v1]
---
# 位置编码与RoPE

注意力需要可用的位置信息来区分顺序。位置编码的选择同时影响训练长度、推理缓存位置和长上下文扩展。

前置学习：[Transformer与自回归生成](Transformer与自回归生成.md)。所属模块：[模型网络](../modules/模型网络.md)。

## 基本机制

绝对位置嵌入把位置信息加入 token 表示；RoPE 对 Q/K 的成对维度做随位置变化的旋转。二维旋转矩阵可写为 R(θ)=[[cosθ,-sinθ],[sinθ,cosθ]]。对位置 m、n，旋转后点积包含 R(m)ᵀR(n) 的相对位置信息。这是“用绝对位置构造旋转、使点积呈现相对位置关系”的关键。

依据：[RoFormer 与 RoPE 原论文](https://arxiv.org/html/2104.09864v5)；[Transformer 原论文](https://arxiv.org/html/1706.03762v7)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

原 Transformer 使用正弦位置编码；RoFormer 给出旋转位置编码。延长上下文的缩放与插值方案是后续独立设计，不应被当成 RoPE 定义的必然性质。

## 适用条件与限制

位置表示可计算到更大下标，不代表模型在该长度上保持质量；训练分布、检索难度和缓存实现仍会限制效果。本文不提供未经校验的长上下文缩放参数。

## 常见误区

把 RoPE 描述为“直接把相对距离相加到 embedding”会丢失其对 Q/K 旋转的机制；也不能把最大配置长度当成有效理解长度。

## 学习练习

手算二维向量在 θ=0 和 θ=π/2 时的旋转。若缓存沿用了过去位置，而新 token 的 position 被错误重置，会破坏什么？

<details>
<summary>展开答案要点</summary>

零角度不变，π/2 旋转为 (-y,x)。错误重置会使新旧 Q/K 的相对位置语义不一致；应结合模型缓存与位置接口查验，而非只看张量 shape。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-position-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[RoFormer 与 RoPE 原论文](https://arxiv.org/html/2104.09864v5)；[Transformer 原论文](https://arxiv.org/html/1706.03762v7)。

关联阅读：[KV缓存原理与显存估算](KV缓存原理与显存估算.md)；[上下文选择与压缩](上下文选择与压缩.md)。
