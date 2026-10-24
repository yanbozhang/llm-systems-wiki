---
id: benchmark-rag
module: benchmark
status: published
page_version: 1
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-benchmark-rag-v1]
---
# RAG检索与回答评测

RAG评测应同时看组件与最终答案。检索更相关可能改善结果，也可能被重排、上下文或生成问题抵消。

## 学习目标

- 分开评估检索与回答。
- 手算检索指标。
- 检查引用支持与无答案处理。

## 前置知识

先阅读[评测协议与可复现性](评测协议与可复现性.md)；[RAG与引用回答](RAG与引用回答.md)，并能区分样本、任务、协议、指标和结论。缺少统计基础时先完成[共同基础](../../docs/共同基础.md)中的概率与实验自测。

## 基本机制

先建立查询及需要的证据集合，再评价Recall@k、排名指标和上下文选择；回答层检查正确性、忠实于证据的程度、引用支持和信息不足时的行为。Ragas文档明确区分端到端、组件及业务指标；自动评分还需要核对所需参考答案与模型裁判依赖。

依据：[Ragas 评测指标](https://docs.ragas.io/en/stable/concepts/metrics/overview/)；[Hugging Face RAG 实践](https://huggingface.co/learn/cookbook/en/advanced_rag)。这里整理方法定义与作者说明，不把项目自述的效果作为本库实测结论。

## 推导或示例

相关文档集合为{A,B,C}，前三条召回为[B,D,A]，则Precision@3=2/3，Recall@3=2/3，首个相关结果在第1位时倒数排名为1。只有一条正确引用不能证明回答中的全部声明都有支持。

再把每个回答拆成可核验声明，检查其引用是否真的支持该声明。忠实复述错误来源仍可能事实错误；使用真实链接但引用不相关，也不能算有依据回答。

以上数值和场景用于教学，不是任何模型或平台的实测成绩。

## 适用条件与限制

检索相关集合不完整会影响指标；自动裁判存在偏差与成本。来自生产流量的业务指标还有用户和流程因素，不能直接当成模型质量。

## 常见误区

提高top-k并不总改善答案；相关性、支持度与事实正确性必须分开。

## 实践任务

建立单源、多源、无答案、冲突和过期版本五类问题，每类至少设计两个。先冻结证据与判据，再对比检索候选、实际上下文和最终回答，逐层记录误差。

使用[评测协议模板](../../templates/评测协议模板.md)和[实验记录模板](../../templates/实验记录模板.md)保存设计；本页状态为“已设计”，未执行大模型基准。

## 掌握标准

指标分母正确；引用逐声明可回查；无答案和冲突场景明确；能根据分层证据定位改进位置。

复核时应展示协议、计算过程或失败样例。不能只提交一个分数而没有可查证的输入、版本与判据。

## 自测与复盘

在本主题中找出一个会改变分数却不代表模型能力改变的因素；设计一组对照以隔离它。再说明当前结论尚不能证明什么。

<details>
<summary>复盘要点</summary>

检查提示、数据版本、解析器、采样预算、工具权限、环境与聚合规则。对照应固定其余变量；说明样本范围、随机性、未测条件及可能的评估器误差。

</details>

## 来源与继续学习

[Ragas 评测指标](https://docs.ragas.io/en/stable/concepts/metrics/overview/)；[Hugging Face RAG 实践](https://huggingface.co/learn/cookbook/en/advanced_rag)；[GraphRAG 官方文档](https://microsoft.github.io/graphrag/)。来源读取范围见[来源索引](../../sources/来源索引.md)，学习顺序见[Benchmark学习路径](../paths/Benchmark学习路径.md)。

返回[Benchmark模块](../modules/Benchmark.md)，或查看[能力地图](../../docs/能力地图.md)。
