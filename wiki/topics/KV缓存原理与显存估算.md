---
id: kv-cache
module: inference
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-kv-cache-v1]
---
# KV缓存原理与显存估算

KV Cache 保存每层已处理 token 的 K/V，使生成新 token 时复用历史投影。它缓存模型中间状态，不是问答答案缓存，也不是 Agent 的长期记忆。

前置学习：[Prefill与Decode](Prefill与Decode.md)。所属模块：[推理](../modules/推理.md)。

## 学习目标

- 估算不同请求的缓存。
- 区分逻辑长度与物理分配。
- 验证缓存兼容条件。

## 前置知识

先掌握Prefill/Decode、GQA和数据类型的字节数。模型权重与KV状态是不同内存项；batch中的请求长度也未必相同。

## 基本机制

对标准全注意力解码器，缓存张量的近似字节数为 2×B×T×L×Hkv×Dh×S，其中 2 对应 K 和 V，B 为批大小，T 为缓存长度，L 为层数，Hkv 为 KV 头数，Dh 为每头维度，S 为每元素字节。新 token 的 Q 与历史 K 计算注意力，再加权历史 V；缓存通常仍随上下文增长。

依据：[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)；[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

标准全注意力下，变长batch可用2L Hkv Dh S×ΣTi估计有效KV张量。如果两个请求长度分别1024和3072，按两个请求都填充到3072估算会多算2048个token位置；实际引擎的块分配和共享策略决定物理占用。

以32层、8个KV头、每头128、FP16为例，每token KV约为128KiB，因此4096个有效token约512MiB。若每块16token，一个长度17的独立请求需要两块，尾块会有未用位置。这些是张量与块布局的推导，尚不包含权重和临时工作区。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)；[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)。

## 方法演进

MQA/GQA 从结构上减少 KV 头数；分页缓存改善分配与共享；前缀缓存跨请求复用兼容前缀；量化改变存储精度。这些是不同方向，可在满足实现条件时组合。

## 适用条件与限制

该公式不含权重、临时激活、缓存块填充、元数据或分片复制；滑动窗口、压缩状态和其他架构需改写估算。不同 prompt、模型、adapter 或位置语义不兼容时不可随意复用。

## 常见误区

缓存历史 K/V 不表示下一 token 的注意力无需访问历史；也不能把缓存字节节省比例当成端到端延迟收益。

## 实践任务

做一张请求长度表，计算有效KV、padding布局与分页布局的估计值。再列出跨请求复用所需身份：模型版本、adapter、token序列、位置与缓存精度等，并设计一个不兼容前缀的反例。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：缓存保存对象正确；推导：变长请求和字节单位正确；实践：能区分逻辑与物理内存；评估：同时考虑质量、命中率和实际服务指标。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

设 B=1、T=4096、L=32、Hkv=8、Dh=128、S=2，估算缓存占用。若 Hkv 变成 32 又如何？

<details>
<summary>展开答案要点</summary>

结果为 536,870,912 字节，即 512 MiB；32 个 KV 头时为 2 GiB。此为给定参数下的推导练习，未运行硬件实验。

</details>

进阶追问：前缀文本完全相同但adapter不同，是否可以直接共用KV？

<details>
<summary>展开进阶答案要点</summary>

不能仅按文本判断；adapter会改变计算状态，必须由引擎的缓存身份与兼容规则确认。

</details>

## 课程与下一步

[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)；[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[vLLM 文档入口](https://docs.vllm.ai/en/stable/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-kv-cache-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)；[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[GQA 原论文](https://arxiv.org/html/2305.13245v3)。

关联阅读：[MHA与MQA及GQA](MHA与MQA及GQA.md)；[位置编码与RoPE](位置编码与RoPE.md)；[Agent记忆与保鲜](Agent记忆与保鲜.md)。
