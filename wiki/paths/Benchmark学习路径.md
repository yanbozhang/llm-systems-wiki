# Benchmark学习路径

把评测目标转成冻结的输入、预算、判据与分母，并区分测量器可靠性和被评系统能力。

## 前置与证据边界

能阅读结构化逐题记录，理解比率、条件概率与均值；缺少基础时先补共同基础。 基础入口见[共同基础](../../docs/共同基础.md)，能力身份见[能力地图](../../docs/能力地图.md)。

已完成的是已有主题与标准库教学示例的编纂。本路径把它们组织为学习行动和可提交产物；端到端项目、真实模型、GPU服务或真机实验尚未执行。阅读、手算、示例验证与真实实验需分别记录；教学代码运行结果以对应版本的CI为准。

## 四层学习行动

| 层级与能力ID | 代表知识点及示例函数 | 学习行动与提交 | 验收判据 |
| --- | --- | --- | --- |
| 理解<br>`benchmark-understand` | [benchmark-protocol-identity](../topics/评测协议与可复现性.md) → [protocol_fingerprint()](../../examples/benchmark/benchmark-protocol.py#L7)<br>[benchmark-general-likelihood](../topics/通用能力基准与选型.md) → [choice_prediction()](../../examples/benchmark/benchmark-general.py#L7)<br>[benchmark-multimodal-input-contract](../topics/多模态与界面感知评测.md) → [square_pad_geometry()](../../examples/benchmark/benchmark-multimodal.py#L6) | 制作模型/数据/提示/解析器/预处理/预算的协议卡，提交长度归一化与图像填充反例。 | 同名基准不等于同一协议；候选分数、单位和模型实际可见输入可回查。 |
| 推导<br>`benchmark-derive` | [benchmark-metrics-aggregation](../topics/评测指标与统计推断.md) → [grouped_accuracy()](../../examples/benchmark/benchmark-metrics.py#L7)<br>[benchmark-metrics-wilson](../topics/评测指标与统计推断.md) → [wilson_interval()](../../examples/benchmark/benchmark-metrics.py#L24)<br>[benchmark-reasoning-code-passk](../topics/推理与代码生成评测.md) → [pass_at_k()](../../examples/benchmark/benchmark-reasoning-code.py#L24)<br>[benchmark-rag-context-ranking](../topics/RAG检索与回答评测.md) → [context_precision_profile()](../../examples/benchmark/benchmark-rag.py#L4) | 分别手算micro/macro、Wilson、pass@k与上下文AP，逐项标明抽样单位和分母。 | 不混不同量纲指标；n=5、正确2、k=2给出0.7；上下文AP不能替代全库召回。 |
| 实践<br>`benchmark-build` | [benchmark-protocol-splits](../topics/评测协议与可复现性.md) → [split_overlap()](../../examples/benchmark/benchmark-protocol.py#L16)<br>[benchmark-protocol-ledger](../topics/评测协议与可复现性.md) → [score_run()](../../examples/benchmark/benchmark-protocol.py#L31)<br>[benchmark-agents-task-acceptance](../topics/Agent任务基准与执行评估.md) → [grade_patch()](../../examples/benchmark/benchmark-agents.py#L4)<br>[benchmark-systems-latency-statistics](../topics/推理系统性能基准.md) → [loadgen_latency_profile()](../../examples/benchmark/benchmark-systems.py#L5) | 为代码、Agent与服务请求设计独立评分记录；冻结切分、测试ID和计时口径。 | 未运行、超时、环境错误与任务失败分别保存；没有运行证据不能算修复成功；ID不重叠仍不证明无语义污染。 |
| 评估<br>`benchmark-evaluate` | [benchmark-contamination-release](../topics/数据污染与评测集治理.md) → [release_membership()](../../examples/benchmark/benchmark-contamination.py#L31)<br>[benchmark-judge-order-mapping](../topics/模型裁判与人工校准.md) → [swapped_pair_summary()](../../examples/benchmark/benchmark-judge.py#L4)<br>[benchmark-judge-human-agreement](../topics/模型裁判与人工校准.md) → [agreement_audit()](../../examples/benchmark/benchmark-judge.py#L37)<br>[benchmark-judge-probability-calibration](../topics/模型裁判与人工校准.md) → [calibration_audit()](../../examples/benchmark/benchmark-judge.py#L60)<br>[benchmark-robustness-utility-security-denominators](../topics/稳健性与工具安全评测.md) → [security_metrics()](../../examples/benchmark/benchmark-robustness.py#L4) | 提交快照成员、双顺序裁判、人工混淆矩阵、概率分箱与正常/受扰动对照表。 | 错误不是平局，kappa可能未定义；拟合校准与选阈值不用最终测试集；正常效用和案例ASR分母独立。 |

## 专题分支与实现边界

按对象延伸：[RAG检索与回答评测](../topics/RAG检索与回答评测.md)使用独立声明支持标签；[多模态与界面感知评测](../topics/多模态与界面感知评测.md)保留预处理和错误层；[Agent任务基准与执行评估](../topics/Agent任务基准与执行评估.md)固定任务、尝试和预算；[推理系统性能基准](../topics/推理系统性能基准.md)区分自测与正式提交。工具课程入口见[系统学习资源指南](../../docs/系统学习资源指南.md)。

## 结业产物与复核

交付一份至少含无答案、无法解析、超时、未运行和重复采样的评测设计包。由他人凭协议恢复样本与评分规则，并能指出一个综合分无法支持的结论。

复核者应能从能力ID、unit_id、主题版本、示例路径/函数、输入和预期重建推演。至少保留一个失败或未知样例，并说明源码已覆盖与教学省略的部分；任何实测结果都需另附原始记录，不能用预期值填写。

使用[学习记录模板](../../templates/学习记录模板.md)、[实验记录模板](../../templates/实验记录模板.md)和[评测协议模板](../../templates/评测协议模板.md)组织产物。可将本路径接入[三个跨模块实践项目](../../docs/跨模块实践项目.md)；真实剩余实验见[研究队列](../../docs/研究队列.md)。

下一步：[系统工程路径](系统工程路径.md)、[GUI智能体实践路径](GUI智能体实践路径.md)、[AI编程智能体实践路径](AI编程智能体实践路径.md)。
