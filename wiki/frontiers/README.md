# 2026研究进展

核对截止：2026-10-25。本轮按七个模块选择14篇ICML 2026与ACL 2026论文，并对照14个开源项目的发布记录和固定提交。它是与基础知识相连的专题选读，不是全部2026论文的目录。

取得并按注明章节阅读的论文全文为8篇；另外6篇目前只核验了官方摘要与公开说明。每节写明读取范围，未将未读部分、作者报告的收益或教学代码当作已复现实验。

## 从模块进入

| 模块 | 本轮研究问题 | 正文 |
|---|---|---|
| 模型网络 | 从固定计算预算，走向专家宽度、MLA稀疏性与硬件约束。 | [模型网络研究进展](模型网络研究进展.md) |
| 训练 | 把奖励归一化、正负样本与异步训练中的版本差异连起来。 | [训练研究进展](训练研究进展.md) |
| 推理 | 比较缓存淘汰、长上下文推测解码和真实服务预算。 | [推理研究进展](推理研究进展.md) |
| Harness | 让跨轨迹压缩、经验质量与可恢复的运行状态一起工作。 | [Harness研究进展](Harness研究进展.md) |
| 知识库 | 从语义相似检索，走向需要推理且能处理冲突的证据链。 | [知识库研究进展](知识库研究进展.md) |
| 业务Agent | 细化软件任务记忆与GUI步骤监督，理解执行边界的工程变化。 | [业务Agent研究进展](业务Agent研究进展.md) |
| Benchmark | 检查排行榜饱和、冲突证据与评分管线的可比性。 | [Benchmark研究进展](Benchmark研究进展.md) |

## 论文与读取范围

| 论文 | 会议依据 | 本轮正文状态 |
|---|---|---|
| [MoSE: Mixture of Slimmable Experts for Efficient and Adaptive Language Models](../../sources/library/2026-paper-network-mose/README.md) | ICML 2026 · 官方Poster目录 | 全文已取得；按资料卡注明章节阅读 |
| [RoBSA: RoPE-based Blockwise Sparse Multi-head Latent Attention](../../sources/library/2026-paper-network-robsa/README.md) | ACL 2026 · 主会长文 | 全文已取得；按资料卡注明章节阅读 |
| [Reinforcement Learning with Verifiable Rewards: GRPO’s Loss, Dynamics, and Success Amplification](../../sources/library/2026-paper-training-grpo/README.md) | ICML 2026 · 官方Poster目录 | 仅官方摘要与说明；全文尚未取得 |
| [Rethinking Sample Polarity in Reinforcement Learning with Verifiable Rewards](../../sources/library/2026-paper-training-polarity/README.md) | ACL 2026 · 主会长文 | 全文已取得；按资料卡注明章节阅读 |
| [Rethinking KV Cache Eviction via a Unified Information-Theoretic Objective](../../sources/library/2026-paper-inference-eviction/README.md) | ICML 2026 · 官方Poster目录 | 仅官方摘要与说明；全文尚未取得 |
| [LongSpec: Long-Context Lossless Speculative Decoding with Efficient Drafting and Verification](../../sources/library/2026-paper-inference-longspec/README.md) | ACL 2026 · 主会长文 | 全文已取得；按资料卡注明章节阅读 |
| [RE-TRAC: REcursive TRAjectory Compression for Deep Search Agents](../../sources/library/2026-paper-harness-retrac/README.md) | ICML 2026 · 官方Poster目录 | 全文已取得；按资料卡注明章节阅读 |
| [How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior](../../sources/library/2026-paper-harness-memory/README.md) | ACL 2026 · 主会长文 | 仅官方摘要与说明；全文尚未取得 |
| [From Extraction to Deduction: Resolving Functional Misalignment in RAG via a Collaborative Critic-Reasoner Framework](../../sources/library/2026-paper-knowledge-crag/README.md) | ICML 2026 · 官方Poster目录 | 仅官方摘要与说明；全文尚未取得 |
| [ReasonEmbed: Enhanced Text Embeddings for Reasoning-Intensive Document Retrieval](../../sources/library/2026-paper-knowledge-reasonembed/README.md) | ACL 2026 · 主会长文 | 全文已取得；按资料卡注明章节阅读 |
| [Structurally Aligned Subtask-Level Memory for Software Engineering Agents](../../sources/library/2026-paper-agents-subtask/README.md) | ICML 2026 · 官方Poster目录 | 仅官方摘要与说明；全文尚未取得 |
| [WebSTAR: Scalable Data Synthesis for Computer Use Agents with Step-Level Filtering](../../sources/library/2026-paper-agents-webstar/README.md) | ACL 2026 · 主会长文 | 全文已取得；按资料卡注明章节阅读 |
| [When AI Benchmarks Plateau: A Systematic Study of Benchmark Saturation](../../sources/library/2026-paper-benchmark-saturation/README.md) | ICML 2026 · 官方Poster目录 | 仅官方摘要与说明；全文尚未取得 |
| [Benchmarking LLM’s Capability in Reasoning over Conflicting Web References](../../sources/library/2026-paper-benchmark-conflicts/README.md) | ACL 2026 · 主会长文 | 全文已取得；按资料卡注明章节阅读 |

## 怎样比较仓库的最新进展

发布标签、发布日和当前分支提交分别记录。发布标签可能对应不同语言包，候选版不等于稳定版，2026年的提交也不意味着最新release一定发布于2026。公司项目与社区/非营利项目在各页分别标注。

每篇综述同时提供公式或明确标注的教学模型、可运行的小代码、结构图、条件与阅读任务。新增内容指回基础主题，已有135个知识点的身份与历史发布清单保持独立。

## 出处在哪里

论文录用依据来自会议或出版方的官方记录，工程变化来自项目发布记录和固定提交。作者的论文主张与项目的发布说明属于原作者陈述；数值效果未由本库独立核实。OpenReview部分接口/PDF未放行，部分大文件下载超时，未取得的全文不进入“已保存”记录。

[来源资料库](../../sources/README.md)提供每份资料的目录、版本和真实保存状态；[仓库导览](../../docs/仓库导览.md)帮助第一次访问的读者理解内容结构。研究方法是先核对来源身份与版本，再读方法和条件，最后联系现有知识与实现；没有来源支持的结论不补写。

[返回知识正文](../README.md) · [打开研究进展网站](https://yanbozhang.github.io/llm-systems-wiki/research/)
