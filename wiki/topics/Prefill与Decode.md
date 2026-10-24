---
id: prefill-decode
module: inference
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-prefill-decode-v1]
---
# Prefill与Decode

同一个生成请求通常包含处理提示的 Prefill 和逐 token 生成的 Decode。把二者拆开，才能解释首 token 延迟、后续 token 延迟和系统吞吐。

前置学习：[Transformer与自回归生成](Transformer与自回归生成.md)。所属模块：[推理](../modules/推理.md)。

## 基本机制

Prefill 计算提示各位置的表示及可缓存 K/V；Decode 每步处理新 token，并读取历史缓存。TTFT 从请求到达至首 token 返回，通常包含排队与 Prefill；TPOT 或每 token 延迟关注后续生成；吞吐应明确是输入 token、输出 token 还是完成请求数。

依据：[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

缓存减少历史重复计算，连续批处理改变请求如何共享设备。长提示、短输出与短提示、长输出是不同负载，优化优先级可能不同。调度器还可能采用分块 Prefill，以协调两类工作。

## 适用条件与限制

Prefill 常有更高并行度，Decode 常受存储带宽影响，但具体瓶颈依赖模型、batch、硬件和并行方式，不能视为普遍定律。

## 常见误区

只报告平均延迟会隐藏排队与长尾；只用 tokens/s 判断交互体验会漏掉首 token 等待。吞吐提升可能伴随单请求延迟变化。

## 学习练习

两个系统输出吞吐相同，其中一个 TTFT 很高。为聊天应用列出还应比较的指标和负载设置。

<details>
<summary>展开答案要点</summary>

比较 p50/p95 TTFT、逐 token 延迟、完成率、排队时间；固定输入/输出长度分布、到达率、并发、模型精度和硬件。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-prefill-decode-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。

关联阅读：[缓存分页与连续批处理](缓存分页与连续批处理.md)。
