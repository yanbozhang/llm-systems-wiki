---
id: prefill-decode
module: inference
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-prefill-decode-v1]
---
# Prefill与Decode

同一个生成请求通常包含处理提示的 Prefill 和逐 token 生成的 Decode。把二者拆开，才能解释首 token 延迟、后续 token 延迟和系统吞吐。

前置学习：[Transformer与自回归生成](Transformer与自回归生成.md)。所属模块：[推理](../modules/推理.md)。

## 学习目标

- 分解请求时间线。
- 计算TTFT和逐token延迟。
- 定位吞吐与长尾矛盾。

## 前置知识

需了解自回归生成与KV缓存。客户端观测、服务端计算和排队时间属于不同计时边界，比较前先明确时钟和起止事件。

## 基本机制

Prefill 计算提示各位置的表示及可缓存 K/V；Decode 每步处理新 token，并读取历史缓存。TTFT 从请求到达至首 token 返回，通常包含排队与 Prefill；TPOT 或每 token 延迟关注后续生成；吞吐应明确是输入 token、输出 token 还是完成请求数。

依据：[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

请求在t=0进入客户端测量，首token在0.8秒返回，最后一个token在1.2秒返回，总共5个输出token。按该口径TTFT=0.8秒，后续平均token间隔=(1.2-0.8)/(5-1)=0.1秒。

这个平均值隐藏了每个间隔的波动；流式输出被网络缓冲合并时，客户端间隔也不等于单步GPU执行时间。测量应分别报告排队、prefill、decode和传输的可观测部分，并明确只有一个输出token时TPOT不可按该式计算。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[LLM Systems](https://llmsystem.github.io/llmsystem2025spring/)。

## 方法演进

缓存减少历史重复计算，连续批处理改变请求如何共享设备。长提示、短输出与短提示、长输出是不同负载，优化优先级可能不同。调度器还可能采用分块 Prefill，以协调两类工作。

## 适用条件与限制

Prefill 常有更高并行度，Decode 常受存储带宽影响，但具体瓶颈依赖模型、batch、硬件和并行方式，不能视为普遍定律。

## 常见误区

只报告平均延迟会隐藏排队与长尾；只用 tokens/s 判断交互体验会漏掉首 token 等待。吞吐提升可能伴随单请求延迟变化。

## 实践任务

画出两个请求的到达、首token和完成时间线，分别计算延迟与观测区间吞吐。设计长提示/短输出与短提示/长输出两类负载，不把它们平均成一个无法解释的数字。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：阶段边界清晰；推导：分母和单位正确；实践：能记录时间戳；评估：能解释吞吐、TTFT与尾延迟的权衡。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

两个系统输出吞吐相同，其中一个 TTFT 很高。为聊天应用列出还应比较的指标和负载设置。

<details>
<summary>展开答案要点</summary>

比较 p50/p95 TTFT、逐 token 延迟、完成率、排队时间；固定输入/输出长度分布、到达率、并发、模型精度和硬件。

</details>

进阶追问：客户端按块收到多个token时，能直接把块间隔当成每token延迟吗？

<details>
<summary>展开进阶答案要点</summary>

不能。应记录流协议及缓冲行为，使用真实token事件或明确标注块级观测口径。

</details>

## 课程与下一步

[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[LLM Systems](https://llmsystem.github.io/llmsystem2025spring/)；[MLPerf Inference](https://raw.githubusercontent.com/mlcommons/inference/master/README.md)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-prefill-decode-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[PagedAttention 原论文](https://arxiv.org/html/2309.06180v1)；[Transformers 缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)。

关联阅读：[缓存分页与连续批处理](缓存分页与连续批处理.md)。
