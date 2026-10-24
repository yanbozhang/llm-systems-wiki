# LLM Systems Wiki

[简体中文](README.md) · **English**

[**Open the knowledge library →**](https://yanbozhang.github.io/llm-systems-wiki/)

**Learn LLM systems from equations to source code.**

An open engineering field guide that connects research papers, official documentation, and pinned source code with derivations, runnable teaching examples, and implementation diagrams. Explore Transformer architecture, training, inference, RAG, agent harnesses, applied agents, and evaluation.

[![Knowledge checks](https://github.com/yanbozhang/llm-systems-wiki/actions/workflows/check.yml/badge.svg)](https://github.com/yanbozhang/llm-systems-wiki/actions/workflows/check.yml)
[![Release](https://img.shields.io/github/v/release/yanbozhang/llm-systems-wiki)](https://github.com/yanbozhang/llm-systems-wiki/releases)
[![Stars](https://img.shields.io/github/stars/yanbozhang/llm-systems-wiki?style=social)](https://github.com/yanbozhang/llm-systems-wiki/stargazers)

**7 areas · 45 topics · 135 knowledge units · 45 Python examples · 6 learning paths.** Every knowledge unit connects equations and assumptions, code and implementation notes, a Mermaid diagram, and traceable references.

The website supports search, module filters, learning paths, article navigation, code highlighting, mathematical notation, diagrams, saved articles, light/dark themes, and Chinese/English navigation. **The knowledge articles are currently written in Chinese.** This English README and the translated interface do not imply that the full library has been translated.

[Browse the library](https://yanbozhang.github.io/llm-systems-wiki/library/) · [Learning paths](https://yanbozhang.github.io/llm-systems-wiki/paths/) · [Capability map](docs/能力地图.md) · [Agent framework guide](docs/Agent开源方案导读.md) · [Changelog](CHANGELOG.md)

[![Knowledge library website preview](assets/site-preview.png)](https://yanbozhang.github.io/llm-systems-wiki/)

## Start with a question

| What would you like to understand? | Read | Teaching example |
|---|---|---|
| Why is attention scaled by the square root of the head dimension? | [Transformer and autoregressive generation](wiki/topics/Transformer与自回归生成.md) | [transformer.py](examples/network/transformer.py) |
| How does GQA change the KV cache budget? | [MHA, MQA, and GQA](wiki/topics/MHA与MQA及GQA.md) · [KV cache](wiki/topics/KV缓存原理与显存估算.md) | [kv-cache.py](examples/inference/kv-cache.py) |
| What do LoRA and DPO optimize? | [SFT and LoRA](wiki/topics/监督微调与LoRA.md) · [DPO](wiki/topics/偏好学习与DPO.md) | [preference.py](examples/training/preference.py) |
| Why can a RAG system retrieve evidence and still answer incorrectly? | [RAG and cited answers](wiki/topics/RAG与引用回答.md) · [RAG evaluation](wiki/topics/RAG检索与回答评测.md) | [rag.py](examples/knowledge/rag.py) |
| How does a Codex CLI tool call reach execution? | [Codex CLI architecture](wiki/topics/CodexCLI架构与执行.md) | [codex-cli.py](examples/agents/codex-cli.py) |
| What are Claude Code's public workflow and extension boundaries? | [Claude Code workflow and extensions](wiki/topics/ClaudeCode工作流与扩展边界.md) | [claude-code.py](examples/agents/claude-code.py) |
| How does a mobile agent move from a screenshot to task completion? | [Mobile-Agent](wiki/topics/MobileAgent多智能体协作.md) · [AppAgent](wiki/topics/AppAgent探索与技能学习.md) · [UI-TARS](wiki/topics/UITARS感知与动作执行.md) | [mobile-agent.py](examples/agents/mobile-agent.py) |
| Why do agents need checkpoints as well as conversation history? | [LangGraph](wiki/topics/LangGraph状态图与持久化.md) · [AutoGen](wiki/topics/AutoGen对话团队与终止.md) | [langgraph.py](examples/harness/langgraph.py) |
| How do coding agents read, edit, and verify a repository? | [OpenHands](wiki/topics/OpenHands事件流与运行时.md) · [SWE-agent](wiki/topics/SWEAgent与智能体计算机接口.md) · [Aider](wiki/topics/Aider仓库地图与编辑协议.md) | [aider.py](examples/agents/aider.py) |
| Are two leaderboard scores actually comparable? | [Evaluation protocols](wiki/topics/评测协议与可复现性.md) · [Metrics and statistics](wiki/topics/评测指标与统计推断.md) | [benchmark-metrics.py](examples/benchmark/benchmark-metrics.py) |

## The knowledge stack

| Area | Topics / units | Coverage |
|---|---:|---|
| [Architecture](wiki/modules/模型网络.md) | 4 / 12 | Transformers, attention heads, RoPE, feed-forward networks, normalization |
| [Training](wiki/modules/训练.md) | 4 / 12 | Pretraining, SFT, LoRA, DPO, GRPO |
| [Inference](wiki/modules/推理.md) | 4 / 12 | Prefill/decode, KV cache, paging, scheduling, performance |
| [Agent harnesses](wiki/modules/Harness.md) | 6 / 18 | State, context, memory, tools, LangGraph, AutoGen |
| [Knowledge and RAG](wiki/modules/知识库.md) | 4 / 12 | Retrieval, source versions, hybrid search, GraphRAG, LLMWiki |
| [Applied agents](wiki/modules/业务Agent.md) | 12 / 36 | Task completion, GUI, coding, failure analysis, eight implementation case studies |
| [Evaluation](wiki/modules/Benchmark.md) | 11 / 33 | Protocols, statistics, contamination, model/agent/RAG/multimodal tasks, judges, systems, safety |

Choose a path: [foundations](wiki/paths/基础入门路径.md), [systems engineering](wiki/paths/系统工程路径.md), [agent development](wiki/paths/Agent开发路径.md), [evaluation](wiki/paths/Benchmark学习路径.md), [GUI agents](wiki/paths/GUI智能体实践路径.md), or [coding agents](wiki/paths/AI编程智能体实践路径.md). The [resource guide](docs/系统学习资源指南.md) connects courses, papers, source code, and exercises.

## Use the library

1. Choose a knowledge unit and work through its assumptions, symbols, and small numerical or state example.
2. Run the teaching function, change one condition, and explain the resulting behavior.
3. Follow the pinned source links and identify what the teaching model leaves out.
4. Keep a [learning record](templates/学习记录模板.md), document experiments, or contribute a correction.

The examples use **Python 3.11+ and its standard library**. They do not require an API key, GPU, or network access.

```bash
git clone https://github.com/yanbozhang/llm-systems-wiki.git
cd llm-systems-wiki
python examples/inference/kv-cache.py
python examples/harness/langgraph.py
```

Teaching tests verify small-scale mathematical properties, state invariants, and documented boundaries. They do not establish full model benchmark results, real-device task success, or end-to-end framework reproduction. Claude Code coverage is limited to public product behavior and SDK interfaces; Codex CLI coverage is based on pinned public source code.

## Contribute

A corrected derivation, a source-code walkthrough, a useful counterexample, or a reproducible experiment can improve this library. See [CONTRIBUTING.md](CONTRIBUTING.md) for content contracts, development commands, checks, and pull request expectations.

Use the [knowledge issue template](https://github.com/yanbozhang/llm-systems-wiki/issues/new?template=knowledge.yml) to suggest an improvement. If an article helps, **star the repository** or share its direct link so another reader can follow the code and evidence.

## Website development

The Astro frontend lives in `web/` and reads the repository's Markdown and knowledge manifests directly. It does not maintain a separate copy of the articles. See the [website development notes](web/README.md) for setup, type checking, builds, and tests. GitHub Pages hosts the public reading site.

## Sources and license

The [source index](sources/来源索引.md) and [knowledge-unit manifest](knowledge/units.json) connect explanations to specific papers, documents, and source versions. Original repository content and teaching code use the [MIT License](LICENSE). Referenced papers, courses, trademarks, and third-party code retain their respective rights and licenses.
