---
id: attention-heads
module: network
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-attention-heads-v1]
---
# MHA与MQA及GQA

注意力头组织决定 Q、K、V 如何分组，也影响解码时 KV Cache 的体积。它是模型结构选择，不能仅通过替换服务端缓存配置完成。

前置学习：[Transformer与自回归生成](Transformer与自回归生成.md)。所属模块：[模型网络](../modules/模型网络.md)。

## 学习目标

- 区分查询头与KV头。
- 计算共享比例。
- 识别结构转换的验证条件。

## 前置知识

先掌握Transformer中的多头表示和KV缓存。理解同一个查询组可以读取共享的K/V，但不同查询仍通过各自Q投影形成不同的注意力分布。

## 基本机制

MHA 为不同查询头配置独立的 K/V 头；MQA 让多个查询头共享一组 K/V；GQA 把查询头分组，每组共享一组 K/V。若查询头数为 Hq、KV 头数为 Hkv，则同组查询使用同一 K/V 表示。固定层数、序列长度和 head dimension 时，KV 存储量与 Hkv 成正比，Q 头数并未因此变成 Hkv。

依据：[GQA 原论文](https://arxiv.org/html/2305.13245v3)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

设Hq=16、Hkv=4、每头维度64，则每4个查询头共享一组K/V。每token每层K/V合计是2×4×64=512个元素；MHA使用16个KV头时为2048个元素。FP16下分别是1024与4096字节。

这一变化不意味着注意力得分的查询头维度从16降成4；得分仍按查询头计算。若把已有MHA权重转换为GQA，应区分初始化方法、继续训练预算与最终质量评估。原GQA论文给出的转换和训练过程属于特定实验配方，不能只改配置后宣称无损。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[GQA 原论文](https://arxiv.org/html/2305.13245v3)；[Stanford CS336](https://cs336.stanford.edu/spring2025/)。

## 方法演进

GQA 原论文将其置于 MHA 与 MQA 之间，并讨论从 MHA checkpoint 转换后继续训练。论文中的质量与速度表现依赖实验配方，不能推出任意 checkpoint 改头数都无损。

## 适用条件与限制

显存估算只覆盖 K/V 张量，不含权重、激活和分配碎片。已有模型若不支持对应头布局，强行修改配置会改变计算或使权重不兼容。

## 常见误区

GQA 不等于减少上下文长度；MQA 也不是只剩一个查询头。缓存更小不保证所有负载延迟都按相同比例降低。

## 实践任务

绘制16个Q头到4组K/V的映射，计算两种头布局在同长度下的理论缓存。再为结构转换列出验证清单：权重shape、输出有效性、任务质量与服务性能；此任务只设计实验，不直接改造生产checkpoint。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：能正确画共享关系；推导：能区分元素数与字节数；实践：能检查模型配置与权重兼容；评估：同时报告质量和内存，不把内存节省当成等比例加速。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

同一模型有 32 个 Q 头、8 个 KV 头。与 32 个 KV 头的版本相比，理论 KV 张量体积是多少？说明比较所需的固定条件。

<details>
<summary>展开答案要点</summary>

为原来的四分之一。需固定 batch、序列长度、层数、每头维度、K/V 数据类型；这是张量体积推导，不是端到端速度结论。

</details>

进阶追问：两个GQA模型KV头数相同，为何缓存占用仍可能不同？

<details>
<summary>展开进阶答案要点</summary>

还取决于层数、每头维度、缓存长度、batch、数据类型、窗口策略和分片复制；只比较一个头数不足以归因。

</details>

## 课程与下一步

[GQA 原论文](https://arxiv.org/html/2305.13245v3)；[Stanford CS336](https://cs336.stanford.edu/spring2025/)；[LLM Systems](https://llmsystem.github.io/llmsystem2025spring/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-attention-heads-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[GQA 原论文](https://arxiv.org/html/2305.13245v3)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。

关联阅读：[KV缓存原理与显存估算](KV缓存原理与显存估算.md)。
