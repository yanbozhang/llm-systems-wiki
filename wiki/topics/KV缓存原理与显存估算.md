---
id: kv-cache
module: inference
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-kv-cache-v1]
---
# KV缓存原理与显存估算

KV Cache 保存每层已处理 token 的 K/V，使生成新 token 时复用历史投影。它缓存模型中间状态，不是问答答案缓存，也不是 Agent 的长期记忆。

前置学习：[Prefill与Decode](Prefill与Decode.md)。所属模块：[推理](../modules/推理.md)。

## 基本机制

对标准全注意力解码器，缓存张量的近似字节数为 2×B×T×L×Hkv×Dh×S，其中 2 对应 K 和 V，B 为批大小，T 为缓存长度，L 为层数，Hkv 为 KV 头数，Dh 为每头维度，S 为每元素字节。新 token 的 Q 与历史 K 计算注意力，再加权历史 V；缓存通常仍随上下文增长。

依据：[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)；[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

MQA/GQA 从结构上减少 KV 头数；分页缓存改善分配与共享；前缀缓存跨请求复用兼容前缀；量化改变存储精度。这些是不同方向，可在满足实现条件时组合。

## 适用条件与限制

该公式不含权重、临时激活、缓存块填充、元数据或分片复制；滑动窗口、压缩状态和其他架构需改写估算。不同 prompt、模型、adapter 或位置语义不兼容时不可随意复用。

## 常见误区

缓存历史 K/V 不表示下一 token 的注意力无需访问历史；也不能把缓存字节节省比例当成端到端延迟收益。

## 学习练习

设 B=1、T=4096、L=32、Hkv=8、Dh=128、S=2，估算缓存占用。若 Hkv 变成 32 又如何？

<details>
<summary>展开答案要点</summary>

结果为 536,870,912 字节，即 512 MiB；32 个 KV 头时为 2 GiB。此为给定参数下的推导练习，未运行硬件实验。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-kv-cache-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)；[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[GQA 原论文](https://arxiv.org/html/2305.13245v3)。

关联阅读：[MHA与MQA及GQA](MHA与MQA及GQA.md)；[位置编码与RoPE](位置编码与RoPE.md)；[Agent记忆与保鲜](Agent记忆与保鲜.md)。
