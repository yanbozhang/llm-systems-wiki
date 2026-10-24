---
id: graph-wiki
module: knowledge
status: published
page_version: 2
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-graph-wiki-v1]
---
# GraphRAG与LLMWiki

图检索组织实体、关系和社区，LLM Wiki 组织可读、可修订的长期知识。两者可分别作用于检索与编纂，也可组合为同一系统。

前置学习：[RAG与引用回答](RAG与引用回答.md)。所属模块：[知识库](../modules/知识库.md)。

## 学习目标

- 区分编纂与检索。
- 建立类型化关系。
- 设计增量知识更新。

## 前置知识

先理解RAG、来源版本和声明支持。实体共现、主题相近、必要先修、方法扩展是不同关系，不能只用一条无类型链接表达。

## 基本机制

GraphRAG 的官方流程从文本提取图，构建社区层次及摘要，再按查询类型利用这些结构；局部问题和全局综合问题使用不同路径。LLM Wiki 的原始模式保留来源，持续修订实体页、主题页、对比和索引，记录新来源改变了什么。

依据：[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[Microsoft 的 LLM Wiki 实现](https://raw.githubusercontent.com/microsoft/llmwiki/main/README.md)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 推导或示例

新增一篇关于前缀缓存的论文，不应仅新建摘要。先登记来源，再判断它改变的是缓存原理、某个实现条件还是性能对比；只修改受影响主题、实践和比较页。若没有新认识，可记录无知识变化。

GraphRAG的社区摘要服务特定查询组织，Wiki页面服务长期阅读与修订。两者可以共用来源和检索能力，但仍要分别检查摘要支持度、页面一致性与增量维护成本。当前HELM等工具的维护状态也提示我们：来源清单应记录状态，而不只是收藏URL。

本节为教学推导或设计示例，未报告模型实验结果。相关原理与课程入口：[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[GraphRAG 官方文档](https://microsoft.github.io/graphrag/)。

## 方法演进

Microsoft 的实现偏向 VS Code 与 MCP 接入；nashsu 提供桌面应用、摄入队列和可选向量检索。它们是作者实现，不构成本仓库采用的依赖。本仓库选择普通 Markdown 链接和 JSON 稳定 ID，便于 GitHub 阅读与增量校验。

## 适用条件与限制

共享来源、相似文字或图邻居只能产生候选关系；正式“前置于、扩展了、反驳了”需要逐项解释。图越密不等于知识越可靠，自动摘要也可能放大来源错误。

## 常见误区

把 LLM Wiki 说成“必然不用 RAG”或“能零成本维护”超出了已验证证据；产品自述的效果数字不能充当本库结果。

## 实践任务

选一条来源变更，画出“来源→声明→主题→能力目标→练习”的影响链。分别标记正式先修和普通关联，检查是否出现不合理的先修循环。

完成后用[实验记录模板](../../templates/实验记录模板.md)记录假设、条件、输出与未解决问题。本页实践状态为“已设计”，尚未执行该实验。

## 掌握标准

理解：编纂与检索职责清楚；推导：关系类型有依据；实践：能产生可审阅变更；评估：衡量可查证性、更新成本和学习任务完成情况。

每一项都需附自己的解释、推导或产物；阅读过页面不自动表示掌握。能力目标见[能力地图](../../docs/能力地图.md)。

## 学习练习

新论文提出缓存调度方法，应如何从一条来源形成可学习的知识网络？

<details>
<summary>展开答案要点</summary>

登记版本，提取机制与条件，更新对应主题和框架页，链接 KV Cache 前置概念，在比较页保留同口径差异，写变化记录；没有影响的基础定义不随意重写。

</details>

进阶追问：图中一个主题链接最多，是否说明它一定是所有人的先修课？

<details>
<summary>展开进阶答案要点</summary>

不成立。链接数反映关联或编辑习惯，先修应根据学习目标与概念依赖独立确定。

</details>

## 课程与下一步

[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[GraphRAG 官方文档](https://microsoft.github.io/graphrag/)；[Full Stack LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/)。阅读具体章节前先对照[系统学习资源指南](../../docs/系统学习资源指南.md)确认基础要求与材料类型。课程入口已读取，不代表本库已完成该课程全部作业。

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-graph-wiki-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；[Microsoft 的 LLM Wiki 实现](https://raw.githubusercontent.com/microsoft/llmwiki/main/README.md)；[nashsu 的 LLM Wiki 实现](https://raw.githubusercontent.com/nashsu/llm_wiki/main/README.md)；[GraphRAG 官方文档](https://microsoft.github.io/graphrag/)。

关联阅读：[来源接入与版本管理](来源接入与版本管理.md)；[缓存分页与连续批处理](缓存分页与连续批处理.md)。
