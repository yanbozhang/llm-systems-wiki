---
id: graph-wiki
module: knowledge
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-graph-wiki-v1]
---
# GraphRAG与LLMWiki

图检索组织实体、关系和社区，LLM Wiki 组织可读、可修订的长期知识。两者可分别作用于检索与编纂，也可组合为同一系统。

前置学习：[RAG与引用回答](RAG与引用回答.md)。所属模块：[知识库](../modules/知识库.md)。

## 基本机制

GraphRAG 的官方流程从文本提取图，构建社区层次及摘要，再按查询类型利用这些结构；局部问题和全局综合问题使用不同路径。LLM Wiki 的原始模式保留来源，持续修订实体页、主题页、对比和索引，记录新来源改变了什么。

依据：[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[Microsoft 的 LLM Wiki 实现](https://raw.githubusercontent.com/microsoft/llmwiki/main/README.md)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

Microsoft 的实现偏向 VS Code 与 MCP 接入；nashsu 提供桌面应用、摄入队列和可选向量检索。它们是作者实现，不构成本仓库采用的依赖。本仓库选择普通 Markdown 链接和 JSON 稳定 ID，便于 GitHub 阅读与增量校验。

## 适用条件与限制

共享来源、相似文字或图邻居只能产生候选关系；正式“前置于、扩展了、反驳了”需要逐项解释。图越密不等于知识越可靠，自动摘要也可能放大来源错误。

## 常见误区

把 LLM Wiki 说成“必然不用 RAG”或“能零成本维护”超出了已验证证据；产品自述的效果数字不能充当本库结果。

## 学习练习

新论文提出缓存调度方法，应如何从一条来源形成可学习的知识网络？

<details>
<summary>展开答案要点</summary>

登记版本，提取机制与条件，更新对应主题和框架页，链接 KV Cache 前置概念，在比较页保留同口径差异，写变化记录；没有影响的基础定义不随意重写。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-graph-wiki-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[Microsoft 的 LLM Wiki 实现](https://raw.githubusercontent.com/microsoft/llmwiki/main/README.md)；[nashsu 的 LLM Wiki 实现](https://raw.githubusercontent.com/nashsu/llm_wiki/main/README.md)；[GraphRAG 官方文档](https://microsoft.github.io/graphrag/)。

关联阅读：[来源接入与版本管理](来源接入与版本管理.md)；[缓存分页与连续批处理](缓存分页与连续批处理.md)。
