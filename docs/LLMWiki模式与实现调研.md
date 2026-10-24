# LLMWiki模式与实现调研

检查日期：2026-10-24。LLM Wiki 在这里指由模型辅助持续编纂、互相链接的个人知识库模式，而不是某个统一产品标准。我们选用 Git 和 Markdown，先把学习内容和维护约束做实。

## 原始模式的三个职责

Karpathy 的原始说明区分 raw sources、wiki、schema，并提出 ingest、query、lint 三类操作。新增资料会修订长期页面、索引和日志；有价值的查询结果也可回流为新的研究材料。具体目录、工具和格式是可选设计。原文的“接近零维护成本”等表述是作者观点，本次没有实测支持。

依据：[Karpathy 原始说明](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

## 代表实现与本库取舍

| 方案 | 作者或官方说明的重点 | 对本库的启发 | 本次未验证 |
|---|---|---|---|
| [Microsoft LLM Wiki](https://github.com/microsoft/llmwiki) | VS Code、核心包、MCP、页面与来源视图 | 把维护操作拆成可检查工具 | 安装、运行与维护效果 |
| [nashsu llm_wiki](https://github.com/nashsu/llm_wiki) | 桌面应用、摄入队列、purpose、可选向量检索 | 区分建库目标与结构规则；来源失败要可恢复 | 产品效果、召回数值与资源成本 |
| [GraphRAG](https://microsoft.github.io/graphrag/) | 图提取、社区摘要、局部与全局查询 | 检索和预先综合可以组合 | 本学习语料上的收益 |
| [LightRAG](https://github.com/HKUDS/LightRAG) | 图与文本结合的检索方案 | 作为后续检索对照实现 | 性能与质量复现 |
| [qmd](https://github.com/tobi/qmd) | 全文、向量与重排 | 页面增长后再引入复杂检索 | 本仓库安装与实测 |

本轮读取原始说明、项目 README 与官方正文相关章节；没有直接采用第三方应用作为运行依赖。

## 为什么保留 Wiki 与 RAG 的组合空间

RAG 回答“如何为这次问题找到证据”，持久 Wiki 回答“已形成的理解怎样组织与修订”。GraphRAG 已在索引期生成社区摘要；nashsu 实现也包含向量检索，因此不能把“是否预先总结”或“有没有向量库”作为绝对分界。

依据：[GraphRAG 官方流程](https://microsoft.github.io/graphrag/)、[nashsu 项目说明](https://github.com/nashsu/llm_wiki)。

## 本版落实的设计

以六模块组织稳定主题，用三条路径服务不同目标。核心声明绑定来源版本，普通互链与正式先修分开。先使用 GitHub 原生阅读与文件搜索，日常巡检生成候选，专题编纂和重要结论仍需阅读复核。这样可以先观测学习价值，再决定是否需要向量库、图服务或模型调用。

这些是本仓库的设计选择，不能解读为所有 LLM Wiki 必须遵守的标准。具体维护成本、理解收益与自动化效果，要通过实际更新与读者练习评估。
