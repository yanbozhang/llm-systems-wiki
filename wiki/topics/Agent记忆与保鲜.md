---
id: memory
module: harness
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-memory-v1]
---
# Agent记忆与保鲜

Agent 记忆是跨步骤或跨任务保存并再次使用的信息。信息是否被保存、是否被召回、是否仍然有效，是三个独立问题。

前置学习：[上下文选择与压缩](上下文选择与压缩.md)。所属模块：[Harness](../modules/Harness.md)。

## 基本机制

区分工作状态、任务过程记录、长期偏好与已验证知识。写入时记录来源、适用范围和有效时间；读取时按当前任务筛选；出现更正时保留修订依据并让旧内容失效。结构化笔记可以减少重复探索，但检索到旧笔记后仍需核对它是否适用于本次任务。

依据：[有效上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

上下文工程文章的结构化 note-taking 提供长期任务思路；LLM Wiki 把可复用理解组织成互链页面。本仓库进一步将个人学习记录独立存放，避免公共知识更新覆盖个人笔记。

## 适用条件与限制

来源摘要与自我生成答案不是独立证据；重复写入可能让错误显得更可信。撤销和删除策略必须传播到召回层，不能只删可见正文。

## 常见误区

KV Cache 不是语义记忆；更大的向量库也不等于更好的记忆。关键在于何时写、按什么条件读、如何修正过时信息。

## 学习练习

一条笔记写着“框架默认开启某优化”，半年后默认值改变。设计这条笔记的必要元数据和召回处理。

<details>
<summary>展开答案要点</summary>

保存框架版本、原文定位、检查日期与适用配置；新版本请求召回时标记过期并核对官方说明，不能直接沿用旧默认值。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-memory-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[有效上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

关联阅读：[来源接入与版本管理](来源接入与版本管理.md)；[GraphRAG与LLMWiki](GraphRAG与LLMWiki.md)。
