# 业务Agent

本模块包含12个主题、36个知识点。每个知识点都有公式、Python教学实现、结构图与固定版本来源。先选择希望获得的能力，再按前置关系进入主题；主题提供具体示例与实践设计，未完成实验不会标记为已验证。

## 核心知识单元

| 主题 | 学习目标 | 教学代码 |
|---|---|---|
| [业务Agent任务闭环](../topics/业务Agent任务闭环.md) | 把用户目标转换成终态契约；区分过程和结果；设计恢复与补偿 | [示例](../../examples/agents/task-loop.py) |
| [GUI定位与执行](../topics/GUI定位与执行.md) | 统一截图与坐标空间；区分定位和执行；设计视觉状态验证 | [示例](../../examples/agents/gui-agent.py) |
| [AI代码开发与反馈](../topics/AI代码开发与反馈.md) | 按契约形成补丁；区分测试缺口与修复；记录可复查证据 | [示例](../../examples/agents/coding-agent.py) |
| [Agent评测与失败归因](../topics/Agent评测与失败归因.md) | 建立分层评测；按轨迹归因；衔接Benchmark模块 | [示例](../../examples/agents/agent-evaluation.py) |
| [OpenHands事件流与运行时](../topics/OpenHands事件流与运行时.md) | 区分Canvas、SDK与托管服务的职责；推演事件分支和模型消息投影；核对动作与观察的关联契约 | [示例](../../examples/agents/openhands.py) |
| [SWEAgent与智能体计算机接口](../topics/SWEAgent与智能体计算机接口.md) | 解释ACI怎样改变观察与编辑反馈；推演编辑失败后的纠错与轨迹状态；区分任务停止、补丁生成和代码任务评测 | [示例](../../examples/agents/swe-agent.py) |
| [Aider仓库地图与编辑协议](../topics/Aider仓库地图与编辑协议.md) | 推导RepoMap图排序与token预算选择；解释SEARCH/REPLACE匹配和失败反馈；区分用户未提交改动、工具编辑与版本控制边界 | [示例](../../examples/agents/aider.py) |
| [MobileAgent多智能体协作](../topics/MobileAgent多智能体协作.md) | 追踪视觉感知与像素坐标；区分进度事实历史的信息流；核验反思状态更新与恢复观测 | [示例](../../examples/agents/mobile-agent.py) |
| [AppAgent探索与技能学习](../topics/AppAgent探索与技能学习.md) | 追踪元素UID与临时标签；解释探索文档的产生与更新；核算部署检索和网格坐标 | [示例](../../examples/agents/app-agent.py) |
| [UITARS感知与动作执行](../topics/UITARS感知与动作执行.md) | 区分模型SDK与桌面宿主职责；追踪动作解析及坐标字段；核验轮数预算和终端动作 | [示例](../../examples/agents/ui-tars.py) |
| [CodexCLI架构与执行](../topics/CodexCLI架构与执行.md) | 区分CLI入口、执行前端与核心运行层；追踪模型工具调用到执行策略；区分输出截断、命令停止与业务验收 | [示例](../../examples/agents/codex-cli.py) |
| [ClaudeCode工作流与扩展边界](../topics/ClaudeCode工作流与扩展边界.md) | 区分产品说明、公开SDK与未公开实现；解释回调控制协议与进程边界；设计工具扩展及其错误处理 | [示例](../../examples/agents/claude-code.py) |

## 四层能力与产物

- 区分感知、动作和业务终态；产物：概念关系说明与反例。
- 推演坐标、任务状态与重试结果；产物：可复核的手算或状态推演。
- 设计可回查的GUI或代码任务；产物：带输入、步骤和预期的实践设计。
- 按执行证据和协议比较系统可靠性；产物：协议、失败分析与结论限制。

完整对应关系见[能力地图](../../docs/能力地图.md)。模块内次序是阅读建议，正式先修以关系清单为准。

## 系统学习入口

[Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction)；[LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)；[Full Stack LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/)；[OpenCompass 文档](https://opencompass.readthedocs.io/en/latest/)。

材料类型、适用基础、归档年份和维护状态见[系统学习资源指南](../../docs/系统学习资源指南.md)。公开入口可读不代表本库已完成整门课程。

## 模块实践与自测

选一个主题，先独立完成推导或状态推演，再设计最小实践；提交时写明条件、预期、判据和结果。解释一个失败样例通常比只展示成功输出更能检查理解。评价模板见[评测协议模板](../../templates/评测协议模板.md)。

## 后续缺口

跨应用真实任务、长期任务恢复、多Agent协作及失败归因案例。本版已补齐逐点公式、教学代码与结构图，真实规模实验仍待执行，不宣称覆盖本领域全部知识。后续按[研究队列](../../docs/研究队列.md)和证据质量推进。

返回[知识地图](../../docs/大模型持续学习知识库.md)。
