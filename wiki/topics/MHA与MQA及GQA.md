---
id: attention-heads
module: network
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-attention-heads-v1]
---
# MHA与MQA及GQA

注意力头组织决定 Q、K、V 如何分组，也影响解码时 KV Cache 的体积。它是模型结构选择，不能仅通过替换服务端缓存配置完成。

前置学习：[Transformer与自回归生成](Transformer与自回归生成.md)。所属模块：[模型网络](../modules/模型网络.md)。

## 基本机制

MHA 为不同查询头配置独立的 K/V 头；MQA 让多个查询头共享一组 K/V；GQA 把查询头分组，每组共享一组 K/V。若查询头数为 Hq、KV 头数为 Hkv，则同组查询使用同一 K/V 表示。固定层数、序列长度和 head dimension 时，KV 存储量与 Hkv 成正比，Q 头数并未因此变成 Hkv。

依据：[GQA 原论文](https://arxiv.org/html/2305.13245v3)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

GQA 原论文将其置于 MHA 与 MQA 之间，并讨论从 MHA checkpoint 转换后继续训练。论文中的质量与速度表现依赖实验配方，不能推出任意 checkpoint 改头数都无损。

## 适用条件与限制

显存估算只覆盖 K/V 张量，不含权重、激活和分配碎片。已有模型若不支持对应头布局，强行修改配置会改变计算或使权重不兼容。

## 常见误区

GQA 不等于减少上下文长度；MQA 也不是只剩一个查询头。缓存更小不保证所有负载延迟都按相同比例降低。

## 学习练习

同一模型有 32 个 Q 头、8 个 KV 头。与 32 个 KV 头的版本相比，理论 KV 张量体积是多少？说明比较所需的固定条件。

<details>
<summary>展开答案要点</summary>

为原来的四分之一。需固定 batch、序列长度、层数、每头维度、K/V 数据类型；这是张量体积推导，不是端到端速度结论。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-attention-heads-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[GQA 原论文](https://arxiv.org/html/2305.13245v3)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。

关联阅读：[KV缓存原理与显存估算](KV缓存原理与显存估算.md)。
