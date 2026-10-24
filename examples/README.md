# 教学示例

45份独立的Python 3.11+标准库示例，每份对应一个主题的三个知识点。直接运行文件会打印demo的合成输入结果；导入文件只定义函数。示例不联网、不调用模型、不连接真机。

例如：

```bash
python examples/inference/kv-cache.py
python examples/agents/codex-cli.py
```

在仓库根目录运行。代码中的返回字段、公式推导、图示、条件与源码差异见对应文章；单元测试验证教学机制，不代表上游端到端复现。

## 模型网络

| 示例 | 文章 |
|---|---|
| [transformer.py](network/transformer.py) | [Transformer与自回归生成](../wiki/topics/Transformer与自回归生成.md) |
| [attention-heads.py](network/attention-heads.py) | [MHA与MQA及GQA](../wiki/topics/MHA与MQA及GQA.md) |
| [position.py](network/position.py) | [位置编码与RoPE](../wiki/topics/位置编码与RoPE.md) |
| [ffn-norm.py](network/ffn-norm.py) | [前馈网络与归一化](../wiki/topics/前馈网络与归一化.md) |

## 训练

| 示例 | 文章 |
|---|---|
| [pretraining.py](training/pretraining.py) | [预训练目标与数据](../wiki/topics/预训练目标与数据.md) |
| [sft.py](training/sft.py) | [监督微调与LoRA](../wiki/topics/监督微调与LoRA.md) |
| [preference.py](training/preference.py) | [偏好学习与DPO](../wiki/topics/偏好学习与DPO.md) |
| [policy-optimization.py](training/policy-optimization.py) | [策略优化与GRPO](../wiki/topics/策略优化与GRPO.md) |

## 推理

| 示例 | 文章 |
|---|---|
| [prefill-decode.py](inference/prefill-decode.py) | [Prefill与Decode](../wiki/topics/Prefill与Decode.md) |
| [kv-cache.py](inference/kv-cache.py) | [KV缓存原理与显存估算](../wiki/topics/KV缓存原理与显存估算.md) |
| [cache-scheduling.py](inference/cache-scheduling.py) | [缓存分页与连续批处理](../wiki/topics/缓存分页与连续批处理.md) |
| [inference-frameworks.py](inference/inference-frameworks.py) | [推理框架与性能实验](../wiki/topics/推理框架与性能实验.md) |

## Harness

| 示例 | 文章 |
|---|---|
| [agent-loop.py](harness/agent-loop.py) | [Harness任务循环](../wiki/topics/Harness任务循环.md) |
| [context.py](harness/context.py) | [上下文选择与压缩](../wiki/topics/上下文选择与压缩.md) |
| [memory.py](harness/memory.py) | [Agent记忆与保鲜](../wiki/topics/Agent记忆与保鲜.md) |
| [tools-skills.py](harness/tools-skills.py) | [工具协议与MCP及Skill](../wiki/topics/工具协议与MCP及Skill.md) |
| [langgraph.py](harness/langgraph.py) | [LangGraph状态图与持久化](../wiki/topics/LangGraph状态图与持久化.md) |
| [autogen.py](harness/autogen.py) | [AutoGen对话团队与终止](../wiki/topics/AutoGen对话团队与终止.md) |

## 知识库

| 示例 | 文章 |
|---|---|
| [rag.py](knowledge/rag.py) | [RAG与引用回答](../wiki/topics/RAG与引用回答.md) |
| [ingestion.py](knowledge/ingestion.py) | [来源接入与版本管理](../wiki/topics/来源接入与版本管理.md) |
| [hybrid-search.py](knowledge/hybrid-search.py) | [混合检索与重排](../wiki/topics/混合检索与重排.md) |
| [graph-wiki.py](knowledge/graph-wiki.py) | [GraphRAG与LLMWiki](../wiki/topics/GraphRAG与LLMWiki.md) |

## 业务Agent

| 示例 | 文章 |
|---|---|
| [task-loop.py](agents/task-loop.py) | [业务Agent任务闭环](../wiki/topics/业务Agent任务闭环.md) |
| [gui-agent.py](agents/gui-agent.py) | [GUI定位与执行](../wiki/topics/GUI定位与执行.md) |
| [coding-agent.py](agents/coding-agent.py) | [AI代码开发与反馈](../wiki/topics/AI代码开发与反馈.md) |
| [agent-evaluation.py](agents/agent-evaluation.py) | [Agent评测与失败归因](../wiki/topics/Agent评测与失败归因.md) |
| [openhands.py](agents/openhands.py) | [OpenHands事件流与运行时](../wiki/topics/OpenHands事件流与运行时.md) |
| [swe-agent.py](agents/swe-agent.py) | [SWEAgent与智能体计算机接口](../wiki/topics/SWEAgent与智能体计算机接口.md) |
| [aider.py](agents/aider.py) | [Aider仓库地图与编辑协议](../wiki/topics/Aider仓库地图与编辑协议.md) |
| [mobile-agent.py](agents/mobile-agent.py) | [MobileAgent多智能体协作](../wiki/topics/MobileAgent多智能体协作.md) |
| [app-agent.py](agents/app-agent.py) | [AppAgent探索与技能学习](../wiki/topics/AppAgent探索与技能学习.md) |
| [ui-tars.py](agents/ui-tars.py) | [UITARS感知与动作执行](../wiki/topics/UITARS感知与动作执行.md) |
| [codex-cli.py](agents/codex-cli.py) | [CodexCLI架构与执行](../wiki/topics/CodexCLI架构与执行.md) |
| [claude-code.py](agents/claude-code.py) | [ClaudeCode工作流与扩展边界](../wiki/topics/ClaudeCode工作流与扩展边界.md) |

## Benchmark

| 示例 | 文章 |
|---|---|
| [benchmark-protocol.py](benchmark/benchmark-protocol.py) | [评测协议与可复现性](../wiki/topics/评测协议与可复现性.md) |
| [benchmark-metrics.py](benchmark/benchmark-metrics.py) | [评测指标与统计推断](../wiki/topics/评测指标与统计推断.md) |
| [benchmark-contamination.py](benchmark/benchmark-contamination.py) | [数据污染与评测集治理](../wiki/topics/数据污染与评测集治理.md) |
| [benchmark-general.py](benchmark/benchmark-general.py) | [通用能力基准与选型](../wiki/topics/通用能力基准与选型.md) |
| [benchmark-reasoning-code.py](benchmark/benchmark-reasoning-code.py) | [推理与代码生成评测](../wiki/topics/推理与代码生成评测.md) |
| [benchmark-multimodal.py](benchmark/benchmark-multimodal.py) | [多模态与界面感知评测](../wiki/topics/多模态与界面感知评测.md) |
| [benchmark-agents.py](benchmark/benchmark-agents.py) | [Agent任务基准与执行评估](../wiki/topics/Agent任务基准与执行评估.md) |
| [benchmark-rag.py](benchmark/benchmark-rag.py) | [RAG检索与回答评测](../wiki/topics/RAG检索与回答评测.md) |
| [benchmark-judge.py](benchmark/benchmark-judge.py) | [模型裁判与人工校准](../wiki/topics/模型裁判与人工校准.md) |
| [benchmark-systems.py](benchmark/benchmark-systems.py) | [推理系统性能基准](../wiki/topics/推理系统性能基准.md) |
| [benchmark-robustness.py](benchmark/benchmark-robustness.py) | [稳健性与工具安全评测](../wiki/topics/稳健性与工具安全评测.md) |
