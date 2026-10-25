# Benchmark

本模块包含11个主题、33个知识点。每个知识点都有公式、Python教学实现、结构图与固定版本来源。先选择希望获得的能力，再按前置关系进入主题；主题提供具体示例与实践设计，未完成实验不会标记为已验证。

## 核心知识单元

| 主题 | 学习目标 | 教学代码 |
|---|---|---|
| [评测协议与可复现性](../topics/评测协议与可复现性.md) | 能把模型、数据、提示、评分与预算写成明确的协议对象，并解释指纹能证明什么。；能识别开发集和报告集之间的显式重叠，区分ID检查与污染检测。；能用包含运行错误的逐题记录计算不同分母的指标，拒绝把重试或失败悄悄隐藏。 | [示例](../../examples/benchmark/benchmark-protocol.py) |
| [评测指标与统计推断](../topics/评测指标与统计推断.md) | 能根据目标分布选择micro或macro，并从逐题记录还原分母。；能推导并计算Wilson比例区间，解释适用假设与边界情形。；能按相同题目的配对关系重采样，区分均值差分布、置信区间与胜负结论。 | [示例](../../examples/benchmark/benchmark-metrics.py) |
| [数据污染与评测集治理](../topics/数据污染与评测集治理.md) | 能定义并解释文本规范化规则，区分字节相同、规范化相同与语义相同。；能手算n-gram Jaccard并说明阈值的误报和漏报来源。；能按发布时间和移除时间冻结评测快照，解释版本变化如何影响成绩可比性。 | [示例](../../examples/benchmark/benchmark-contamination.py) |
| [通用能力基准与选型](../topics/通用能力基准与选型.md) | 能从对数似然构造选择题预测，解释长度归一化可能改变排序。；能计算不同选项数量下的均匀随机基线，并说清基线调整的局限。；能将答案解析视为版本化评分协议，保留无法解析与相互矛盾的输出。 | [示例](../../examples/benchmark/benchmark-general.py) |
| [推理与代码生成评测](../topics/推理与代码生成评测.md) | 能为数值答案定义明确的等价与未解析状态，避免用任意文本清洗代替判定。；能推导HumanEval常用pass@k估计，并区分样本池组合概率与单次成功率。；能从代码执行器追到逐样本结果，保留超时、运行失败与未运行状态。 | [示例](../../examples/benchmark/benchmark-reasoning-code.py) |
| [多模态与界面感知评测](../topics/多模态与界面感知评测.md) | 区分感知、推理和交互；固定多模态预处理；设计分层误差分析 | [示例](../../examples/benchmark/benchmark-multimodal.py) |
| [Agent任务基准与执行评估](../topics/Agent任务基准与执行评估.md) | 构造包含有效运行、目标和回归的验收判据；区分终态整题分与条件满足分；重建任务、尝试、环境故障和预算的统计分母 | [示例](../../examples/benchmark/benchmark-agents.py) |
| [RAG检索与回答评测](../topics/RAG检索与回答评测.md) | 分开评估检索与回答；手算检索指标；检查引用支持与无答案处理 | [示例](../../examples/benchmark/benchmark-rag.py) |
| [模型裁判与人工校准](../topics/模型裁判与人工校准.md) | 还原成对顺序交换中的身份并报告解析覆盖率；从混淆矩阵计算人工一致率与kappa；核算概率校准及接受阈值的覆盖与条件错误 | [示例](../../examples/benchmark/benchmark-judge.py) |
| [推理系统性能基准](../topics/推理系统性能基准.md) | 定义系统负载与计时边界；比较质量约束下的吞吐；区分自测与正式提交 | [示例](../../examples/benchmark/benchmark-systems.py) |
| [稳健性与工具安全评测](../topics/稳健性与工具安全评测.md) | 审计正常效用、安全效用与ASR的不同分母；区分模型行为、运行时校验和宿主权限隔离；以同题正常对照解释防御收益与退化 | [示例](../../examples/benchmark/benchmark-robustness.py) |

## 四层能力与产物

- 识别基准任务、协议与测量范围；产物：概念关系说明与反例。
- 计算统计、排名和采样指标；产物：可复核的手算或状态推演。
- 设计可复现的多类评测协议；产物：带输入、步骤和预期的实践设计。
- 校准裁判、检查污染并解释结论边界；产物：协议、失败分析与结论限制。

完整对应关系见[能力地图](../../docs/能力地图.md)。模块内次序是阅读建议，正式先修以关系清单为准。

## 系统学习入口

[Stanford CS336](https://cs336.stanford.edu/spring2025/)；[vLLM 文档入口](https://docs.vllm.ai/en/stable/)；[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[Full Stack LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/)；[Hugging Face RAG 实践](https://huggingface.co/learn/cookbook/en/advanced_rag)；[LM Evaluation Harness](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/README.md)；[OpenCompass 文档](https://opencompass.readthedocs.io/en/latest/)；[Ragas 评测指标](https://docs.ragas.io/en/stable/concepts/metrics/overview/)；[HELM 评测框架](https://raw.githubusercontent.com/stanford-crfm/helm/main/README.md)；[MLPerf Inference](https://raw.githubusercontent.com/mlcommons/inference/master/README.md)。

材料类型、适用基础、归档年份和维护状态见[系统学习资源指南](../../docs/系统学习资源指南.md)。公开入口可读不代表本库已完成整门课程。

## 模块实践与自测

选一个主题，先独立完成推导或状态推演，再设计最小实践；提交时写明条件、预期、判据和结果。解释一个失败样例通常比只展示成功输出更能检查理解。评价模板见[评测协议模板](../../templates/评测协议模板.md)。

## 后续缺口

更多语言与领域、长上下文和训练评测、统计工具实验与公开可复查结果。本版已补齐逐点公式、教学代码与结构图，真实规模实验仍待执行，不宣称覆盖本领域全部知识。后续按[研究队列](../../docs/研究队列.md)和证据质量推进。

返回[知识地图](../../docs/大模型持续学习知识库.md)。

## 2026研究进展

检查排行榜饱和、冲突证据与评分管线的可比性。 阅读[Benchmark研究进展](../frontiers/Benchmark研究进展.md)，对照会议论文、作者版本与当前开源实现。来源及本地保存情况见[来源资料库](../../sources/README.md)。
