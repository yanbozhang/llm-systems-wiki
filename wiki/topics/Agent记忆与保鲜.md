---
id: memory
module: harness
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-memory-v1]
---
# Agent记忆与保鲜

Agent 记忆是跨步骤或跨任务保存并再次使用的信息。信息是否被保存、是否被召回、是否仍然有效，是三个独立问题。

前置学习：[上下文选择与压缩](上下文选择与压缩.md)。所属模块：[Harness](../modules/Harness.md)。

## 学习目标

- 定义记忆写入与失效条件。
- 区分个人偏好和公共事实。
- 验证召回适用性。

## 前置知识

先理解上下文选择与来源版本。记忆条目应说明它记录的是事件、偏好、方法还是事实，以及谁可以使用它。

## 基本机制

区分工作状态、任务过程记录、长期偏好与已验证知识。写入时记录来源、适用范围和有效时间；读取时按当前任务筛选；出现更正时保留修订依据并让旧内容失效。结构化笔记可以减少重复探索，但检索到旧笔记后仍需核对它是否适用于本次任务。

依据：[有效上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

同一句“服务默认使用配置A”，如果没有服务版本与检查时间，很容易在升级后误用。一个更可用的条目应包含主题、版本、来源位置、适用条件、最后复核时间和失效触发条件。

写入、索引、召回和注入是四个阶段。删除展示页不一定清除了检索索引或答案缓存；同一错误被多次摘要也不构成独立证据。对共享知识应保留修订链，对私人偏好应保留个人范围。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[有效上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

## 方法演进

上下文工程文章的结构化 note-taking 提供长期任务思路；LLM Wiki 把可复用理解组织成互链页面。本仓库进一步将个人学习记录独立存放，避免公共知识更新覆盖个人笔记。

## 适用条件与限制

来源摘要与自我生成答案不是独立证据；重复写入可能让错误显得更可信。撤销和删除策略必须传播到召回层，不能只删可见正文。

## 常见误区

KV Cache 不是语义记忆；更大的向量库也不等于更好的记忆。关键在于何时写、按什么条件读、如何修正过时信息。

## 实践任务

创建三条模拟记忆：项目版本事实、个人阅读偏好、一次失败过程。给它们分别制定召回条件、更新时间和删除传播清单，再设计一条不应被当前任务采用的旧记忆。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：条目类型与范围清楚；推导：失效规则可解释；实践：能沿来源修订记忆；评估：同时检查相关性、正确性、过期误用和不当跨域使用。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

一条笔记写着“框架默认开启某优化”，半年后默认值改变。设计这条笔记的必要元数据和召回处理。

<details>
<summary>展开答案要点</summary>

保存框架版本、原文定位、检查日期与适用配置；新版本请求召回时标记过期并核对官方说明，不能直接沿用旧默认值。

</details>

进阶追问：命中率提高但错误回答增多，可能是哪一环出了问题？

<details>
<summary>展开进阶答案要点</summary>

可能是过宽召回、旧版本混入或错误记忆重复强化；需要看命中内容的有效性，而非只提高检索覆盖率。

</details>

## 课程与下一步

[有效上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-memory-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[有效上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

关联阅读：[来源接入与版本管理](来源接入与版本管理.md)；[GraphRAG与LLMWiki](GraphRAG与LLMWiki.md)。
