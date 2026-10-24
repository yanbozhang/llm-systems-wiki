# Benchmark

本模块目前包含11个知识单元。先选择希望获得的能力，再按前置关系进入主题；主题提供具体示例与实践设计，未完成实验不会标记为已验证。

## 核心知识单元

| 主题 | 学习目标 |
|---|---|
| [评测协议与可复现性](../topics/评测协议与可复现性.md) | 定义评测对象与成功标准；冻结可复现协议；区分开发集与报告集 |
| [评测指标与统计推断](../topics/评测指标与统计推断.md) | 选择与任务匹配的指标；计算样例与不确定性；正确做配对比较 |
| [数据污染与评测集治理](../topics/数据污染与评测集治理.md) | 识别数据泄漏路径；区分污染风险与证据；建立评测集更新规则 |
| [通用能力基准与选型](../topics/通用能力基准与选型.md) | 选择通用能力评测组合；区分题型与随机基线；解读领域分层结果 |
| [推理与代码生成评测](../topics/推理与代码生成评测.md) | 区分答案判定与过程解释；计算pass@k；设计代码执行边界 |
| [多模态与界面感知评测](../topics/多模态与界面感知评测.md) | 区分感知、推理和交互；固定多模态预处理；设计分层误差分析 |
| [Agent任务基准与执行评估](../topics/Agent任务基准与执行评估.md) | 选择Agent任务基准；冻结环境与预算；解释执行式评分 |
| [RAG检索与回答评测](../topics/RAG检索与回答评测.md) | 分开评估检索与回答；手算检索指标；检查引用支持与无答案处理 |
| [模型裁判与人工校准](../topics/模型裁判与人工校准.md) | 定义模型裁判任务；设计盲化与交换顺序；校准人工一致性 |
| [推理系统性能基准](../topics/推理系统性能基准.md) | 定义系统负载与计时边界；比较质量约束下的吞吐；区分自测与正式提交 |
| [稳健性与工具安全评测](../topics/稳健性与工具安全评测.md) | 定义稳健性威胁模型；区分正常效用与安全失效；设计隔离评测 |

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

更多语言与领域、长上下文和训练评测、统计工具实验与公开可复查结果。本版补齐学习框架与核心主题，不宣称覆盖本领域全部知识。后续按[研究队列](../../docs/研究队列.md)和证据质量推进。

返回[知识地图](../../docs/大模型持续学习知识库.md)。
