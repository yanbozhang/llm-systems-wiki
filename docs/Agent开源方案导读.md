# Agent开源方案导读

本导读按2026-10-24已经归档的论文、官方说明和固定commit源码，比较十个有代表性的Agent方案。选择目的是覆盖不同的观测、编辑、执行和恢复机制，帮助读者决定先研究什么、需要补做哪些实验。Claude Code在这里是公开产品说明与开源SDK的对照案例，其客户端核心不能据此称为开源；其余项目的代码开放范围也不自动延伸到模型权重和托管服务。

本文依据本库已归档的阅读证据，不包含框架安装或横向实测结果。源码可以支持“这个版本如何工作”，不能单独证明真实使用率、任务成功率或生产收益。完整学习映射见[系统学习资源指南](系统学习资源指南.md)，日常更正与复习流程见[持续更新指南](持续更新指南.md)。

## 为什么选择这十个方案

入选遵循三个条件：有可定位的公开一手材料；能揭示一种有区分度的机制；已经有本库正文和独立教学示例。Mobile-Agent、AppAgent和UI-TARS分别展示分角色决策、探索文档积累、截图动作模型与执行SDK；OpenHands、SWE-agent、Aider、Codex CLI和Claude Code展示事件协议、ACI、仓库地图、客户端运行层、公开扩展边界；LangGraph和AutoGen则展示状态图与对话团队的不同编排方式。它们既可能替代，也可能处于同一系统的不同层。

GitHub关注度只作发现项目与观察维护背景的辅助信号，不作为技术胜负依据。没有统一任务、模型、工具、预算、人工干预和验收协议，就不能把项目README的分数拼成排行榜。本文的适用性建议是依据机制做出的工程判断，尚未经本库真实任务对照验证。

| 方案与文章入口 | 本文固定的读取对象 | 开放范围及不能外推的部分 |
| --- | --- | --- |
| [Mobile-Agent](../wiki/topics/MobileAgent多智能体协作.md) | X-PLUG/MobileAgent的Mobile-Agent-v2；[11cea575561f](https://github.com/X-PLUG/MobileAgent/blob/11cea575561fb7800b5fb6b6cafa56f7a91de11f/Mobile-Agent-v2/run.py) | 公开v2执行与提示代码，根许可MIT；不能混入v3/v3.5或把外部视觉模型、API条款算作同一许可 |
| [AppAgent](../wiki/topics/AppAgent探索与技能学习.md) | **TencentQQGYLab/AppAgent**；[2c1900422caf](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/scripts/task_executor.py) | 公开探索、文档生成、部署与ADB接口，根许可MIT；所用模型服务和目标应用是外部条件 |
| [UI-TARS](../wiki/topics/UITARS感知与动作执行.md) | bytedance/UI-TARS-desktop的LocalComputer链；[3ac2cb8d946d](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/apps/ui-tars/src/main/services/runAgent.ts) | Desktop、SDK、解析器与Operator代码，Apache-2.0；模型论文与权重、Agent TARS其他路径分别核对 |
| [OpenHands](../wiki/topics/OpenHands事件流与运行时.md) | Canvas [fee10e3d2909](https://github.com/OpenHands/OpenHands/blob/fee10e3d2909ebbf9950578575b1ee011492171e/README.md)；SDK [acd96e6fa424](https://github.com/OpenHands/software-agent-sdk/blob/acd96e6fa424c02432304395b9208f99be24b54d/README.md) | 当前社区仓库是Agent Canvas；SDK/Agent Server有独立仓库，SDK README标注MIT；Cloud与Enterprise属于部署及产品层 |
| [SWE-agent](../wiki/topics/SWEAgent与智能体计算机接口.md) | SWE-agent/SWE-agent；[3ea751c087f3](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/config/default.yaml) | agent循环、工具和配置可读；研究原型、当前默认配置、后继mini-swe-agent不能合并成一个实现 |
| [Aider](../wiki/topics/Aider仓库地图与编辑协议.md) | Aider-AI/aider；[5dc9490bb35f](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repomap.py) | RepoMap、编辑器和Git集成可读；代码开放不等于所有模型连接和生成质量都有保证 |
| [Codex CLI](../wiki/topics/CodexCLI架构与执行.md) | openai/codex；[970111f6cb62](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/README.md#L1) | 公开Rust客户端与运行层，Apache-2.0；不代表模型权重、服务条款或托管产品全部开放 |
| [Claude Code](../wiki/topics/ClaudeCode工作流与扩展边界.md) | 产品仓库 [318b7e6ac4e7](https://github.com/anthropics/claude-code/blob/318b7e6ac4e726e88a4ad326214866a93c373b1b/README.md#L1)；Python SDK [0e89b298e771](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/README.md#L1) | 产品仓库保留所有权利，SDK为MIT；SDK接入代码不能当成客户端主循环的完整源码 |
| [LangGraph](../wiki/topics/LangGraph状态图与持久化.md) | langchain-ai/langgraph；[4c52e129eb1a](https://github.com/langchain-ai/langgraph/blob/4c52e129eb1ab69a3da58b799f67929f77d81149/README.md#L1) | MIT的状态编排与检查点接口；外部副作用、模型服务和特定生产存储能力另验 |
| [AutoGen](../wiki/topics/AutoGen对话团队与终止.md) | microsoft/autogen的AgentChat路径；[004749e6b710](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/README.md#L1) | 代码MIT、文档CC BY 4.0；README顶部归档公告优先保留，不将历史教程视为当前维护承诺 |

短SHA仅为表格显示，链接目标均含完整commit。许可依据分别见[Mobile-Agent许可](https://github.com/X-PLUG/MobileAgent/blob/11cea575561fb7800b5fb6b6cafa56f7a91de11f/LICENSE)、[AppAgent许可](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/LICENSE)、[UI-TARS许可](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/LICENSE)、[Codex许可](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/LICENSE#L1)、[Claude Code产品仓库条款](https://github.com/anthropics/claude-code/blob/318b7e6ac4e726e88a4ad326214866a93c373b1b/LICENSE.md#L1)、[Claude SDK许可](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/LICENSE#L1)、[LangGraph许可](https://github.com/langchain-ai/langgraph/blob/4c52e129eb1ab69a3da58b799f67929f77d81149/LICENSE#L1)和[AutoGen代码许可](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/LICENSE-CODE#L1)。SWE-agent与Aider的仓库API许可字段分别为MIT、Apache-2.0，本文没有对应许可全文的新增核验记录；分发时仍需核对对应代码与依赖的完整条款。

## 主循环、状态、恢复和接口比较

这里的“恢复”按已读实现描述：回退页面、重新询问模型、切换事件分支、载入检查点和恢复外部业务是不同动作。表中出现保存或resume接口，不表示整个任务具有事务性。

| 方案 | 主循环与状态单位 | 接口及反馈 | 恢复边界 |
| --- | --- | --- | --- |
| Mobile-Agent-v2 | 感知 → 决策 → ADB动作 → 前后图反思 → 成功后更新进度；历史、进度、事实记忆分开 | 文本动作标记、OCR/图标列表、截图和ADB；反思A/B/C | B执行back，C修正操作；back不是撤销业务，B分支内没有再次截图 |
| AppAgent | 探索阶段形成按UID及动作槽位存储的文档；部署阶段按当前界面取文档再决策 | UI XML与截图数字标签；必要时切网格动作；文本响应解析 | 文档跨运行复用，但自主探索排除集合有自己的生命周期；布局变更需重新定位 |
| UI-TARS Desktop | GUIAgent反复截图、模型请求、解析和顺序派发；保存消息、循环计数及运行状态 | Model适配器、action-parser、Operator；宿主接状态回调与中断 | 截图、模型、执行分层重试；暂停/终态不自动恢复外部应用，动作重试可能重复生效 |
| OpenHands SDK | LocalConversation推进agent；事件追加、活动分支、模型消息投影相互区分 | ActionEvent与ObservationEvent；Agent Server提供REST/WebSocket及typed client | 按父事件链选会话上下文；事件分支不包含自动的workspace文件回滚 |
| SWE-agent | DefaultAgent生成动作、处理异常或重询、记正式step；history与trajectory不同 | YAML装配工具、函数调用解析、窗口或字符串编辑反馈 | 重询保留失败尝试；轨迹可用于分析，不据此保证重启后环境完整恢复 |
| Aider | 仓库地图进入上下文，模型返回编辑块，编辑器应用，Git集成记录改动 | 定义/引用图、SEARCH/REPLACE、检查点与补丁反馈 | Git支持版本回查，匹配策略依具体编辑器；不构成外部副作用或业务语义的自动回滚 |
| Codex CLI | CLI选前端；exec经进程内App Server客户端进入Thread/Turn；core处理工具 | ToolRouter → ToolRegistry → ToolOrchestrator；增量输出与终态分开 | 已读到线程resume入口、取消/超时及输出回收；不声称外部命令恢复后恰好执行一次 |
| Claude Code / SDK | 官方描述为收集上下文、行动、验证；公开SDK管理请求与消息窗口 | stream-json子进程传输、控制回调、进程内MCP；ResultMessage结束一次响应 | SDK可发中断，公开产品说明提到上下文压缩；未公开核心的调度和持久化实现不补写 |
| LangGraph | Pregel超步 → 通道归并 → 检查点；另存pending writes和恢复输入 | typed state、通道update、checkpointer、interrupt/Command | interrupt后从节点开头重跑，恢复答案按调用顺序匹配；内存保存器不跨进程持久 |
| AutoGen AgentChat | 管理器收增量消息、判断终止、选下一发言者；角色状态与游标分开 | run_stream、增量消息、状态化终止条件、save_state/load_state | 静止边界保存整个团队；不能遗漏管理器，也不能假设任意终止器状态都在快照内 |

各行的具体调用链、固定函数和反例在下面展开。模型返回“完成”、驱动返回成功、协议响应结束都只是其中一层状态；实际任务仍需独立终态证据。

## 界面任务：先选择观测和知识复用方式

### Mobile-Agent：学习分角色循环与反馈提交

本库采用v2作为“感知、决策、反思、规划怎样传递状态”的案例。`get_perception_infos`将OCR文字和图标描述转换为当前屏幕的坐标列表；动作执行后，反思读取前后图。A分支追加成功历史并用 `get_process_prompt`更新完成内容，B分支调用back，C保留失败标记。多个角色是多组提示与调用职责，不能仅凭名称推断独立进程、并行执行或训练方式。[Mobile-Agent-v2论文第三节](https://arxiv.org/html/2406.01014v1)；[v2 run.py主循环](https://github.com/X-PLUG/MobileAgent/blob/11cea575561fb7800b5fb6b6cafa56f7a91de11f/Mobile-Agent-v2/run.py)。

适合研究没有业务API、需要屏幕观测的移动端流程，以及动作成功后何时应提交进度。若需要同一应用的知识长期复用，应对比AppAgent，而不是把v2追加的事实文本当成完整知识库。源码中Stop在后续反思前退出，B分支调用back后没有在该分支重新截图；选型时应检查独立验收和观测更新能否满足任务要求。[决策、反思与进度提示](https://github.com/X-PLUG/MobileAgent/blob/11cea575561fb7800b5fb6b6cafa56f7a91de11f/Mobile-Agent-v2/MobileAgent/prompt.py)；[ADB动作接口](https://github.com/X-PLUG/MobileAgent/blob/11cea575561fb7800b5fb6b6cafa56f7a91de11f/Mobile-Agent-v2/MobileAgent/controller.py)。

学习入口：[MobileAgent多智能体协作](../wiki/topics/MobileAgent多智能体协作.md)。用[mobile-agent.py](../examples/agents/mobile-agent.py)中的 `perception_index`、`planning_projection`、`reflection_transition`手算框合并和A/B/C状态；这只验证给定判断后的记账，不验证模型对截图的判断准确率。

### AppAgent：学习探索文档与当前界面的连接

正确官方仓库是 **TencentQQGYLab/AppAgent**。它把探索与部署分开：元素UID关联动作效果文档，部署时遍历当前元素，通过UID取文档并重新标注本轮数字标签。数字标签不是长期身份；resource-id、父级、描述、尺寸和index变化都可能改变UID或其适用性。无数字标签的目标可转入网格模式，当前所读网格提示分支不拼接元素文档。[AppAgent官方两阶段说明](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/README.md)；[元素身份构造](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/scripts/and_controller.py)；[部署检索和area_to_xy](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/scripts/task_executor.py)。

适合研究稳定应用中的重复操作知识如何积累和复用。代价在于先探索或演示、检查文档质量，以及维护应用版本变化后的失效知识。自主探索中已有动作槽位会保留，演示文档生成则有 `DOC_REFINE`分支；这不是无条件自动合并全部经验。BACK也可能形成通用动作说明，SUCCESS则只表示一步推进，不能直接当整项任务成功。[AppAgent论文第三节](https://arxiv.org/html/2312.13771v1)；[自主探索反思与槽位写入](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/scripts/self_explorer.py)；[演示文档更新分支](https://github.com/TencentQQGYLab/AppAgent/blob/2c1900422caf6f9e94e96d5dd984b530e5a5fbf8/scripts/document_generation.py)。

学习入口：[AppAgent探索与技能学习](../wiki/topics/AppAgent探索与技能学习.md)。[app-agent.py](../examples/agents/app-agent.py)提供 `element_identity`、`learn_action_document`、`deployment_context`；先比较同控件改index后的UID，再检查四类反思怎样改文档，最后手算元素与网格坐标。不要用文档填充率替代动作知识正确率。

### UI-TARS：学习模型动作协议与真实执行链

本库只沿Desktop的LocalComputer导入链读 `runAgent → GUIAgent → UITarsModel/actionParser → NutJSElectronOperator/NutJSOperator`。模型论文解释截图和历史如何形成动作预测；桌面应用、SDK与Operator解释预测如何落到设备。模型训练中的长期经验或反思机制，不能直接说成桌面SDK每轮都在训练或拥有另一个反思agent。[UI-TARS模型论文第四节](https://arxiv.org/html/2501.12326v1)；[Desktop宿主装配](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/apps/ui-tars/src/main/services/runAgent.ts)；[SDK执行过程说明](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/packages/ui-tars/sdk/README.md)。

适合研究原生截图动作模型、桌面适配和显示坐标的一致性。选择时先核对具体模型版本、归一化分母、截图尺寸和实际Operator消费的字段：V1_0常量因子和V1_5的smart resize不是同一空间，附加 `start_coords`也不等于NutJS实际重算的点击点。一次模型响应可以含多个动作，循环次数不能当鼠标动作次数；分层重试也不自动保证幂等。[动作与版本分支解析](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/packages/ui-tars/action-parser/src/actionParser.ts)；[坐标转换与图像窗口](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/packages/ui-tars/sdk/src/utils.ts)；[GUIAgent.run](https://github.com/bytedance/UI-TARS-desktop/blob/3ac2cb8d946d78d5ff92ad17b318eaafa18c178c/packages/ui-tars/sdk/src/GUIAgent.ts)。

学习入口：[UITARS感知与动作执行](../wiki/topics/UITARS感知与动作执行.md)。[ui-tars.py](../examples/agents/ui-tars.py)的 `parse_action`、`grounding_coordinates`、`agent_loop_transition`分别检查协议、坐标、预算与终态；实际定位正确率及实机任务成功率必须另测。

## 编程任务：先决定需要改变哪一层

### OpenHands：需要可编排的会话与动作观察协议

当前 `OpenHands/OpenHands`负责Agent Canvas界面、后端选择及本地栈编排；`OpenHands/software-agent-sdk`拥有agent、工具、会话、workspace、事件与Agent Server接口。Canvas、SDK/运行时、Cloud/Enterprise需要分别评估。社区源码足以说明公开接口如何连接，不能用于反推托管系统的全部内部部署。[Canvas仓库职责](https://github.com/OpenHands/OpenHands/blob/fee10e3d2909ebbf9950578575b1ee011492171e/README.md)；[SDK与Agent Server职责](https://github.com/OpenHands/software-agent-sdk/blob/acd96e6fa424c02432304395b9208f99be24b54d/README.md)。

它适合需要在自己的产品中嵌入编程任务、观察会话过程或定制执行工具的研究。主循环入口读 `LocalConversation.run/_run`，事件结构读 `EventLog.path_to_root`与 `LLMConvertibleEvent.events_to_messages`，执行连接读 `Agent._execute_action_event`。事件追加顺序与活动分支不同；一个模型响应中的多个动作还要还原为正确的模型消息。观察通过tool_call_id、action_id、tool_name连接动作，而不是靠展示文字猜关联。[会话运行入口](https://github.com/OpenHands/software-agent-sdk/blob/acd96e6fa424c02432304395b9208f99be24b54d/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)；[EventLog活动分支](https://github.com/OpenHands/software-agent-sdk/blob/acd96e6fa424c02432304395b9208f99be24b54d/openhands-sdk/openhands/sdk/conversation/event_store.py)；[事件到模型消息转换](https://github.com/OpenHands/software-agent-sdk/blob/acd96e6fa424c02432304395b9208f99be24b54d/openhands-sdk/openhands/sdk/event/base.py)；[ObservationEvent接口](https://github.com/OpenHands/software-agent-sdk/blob/acd96e6fa424c02432304395b9208f99be24b54d/openhands-sdk/openhands/sdk/event/llm_convertible/observation.py)。

选型时重点检查workspace、事件保存和业务验收是否覆盖自己的恢复要求。切换历史分支并不会自动把真实文件恢复到旧状态；相同事件重新执行工具也可能产生不同副作用。学习入口：[OpenHands事件流与运行时](../wiki/topics/OpenHands事件流与运行时.md)，配合[openhands.py](../examples/agents/openhands.py)的 `conversation_path`、`project_action_batches`、`observation_links`检查分支、批次和身份。

### SWE-agent：需要研究观察和编辑反馈怎样影响任务

SWE-agent的研究价值在ACI：界面不仅提供工具名，还决定模型能看见多大的文件窗口、如何定位行、编辑失败会返回什么信息。本文固定配置使用function_calling，工具bundle是registry、edit_anthropic、review_on_submit_m，历史处理器为cache_control；窗口实现仍可读，但不能把论文窗口式设计描述为这个默认配置的全部行为。[SWE-agent的ACI论文](https://arxiv.org/html/2405.15793v1)；[当前读取的default.yaml](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/config/default.yaml)；[字符串编辑器工具配置](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/tools/edit_anthropic/config.yaml)。

适合做工具接口或反馈形式的受控对照：固定任务、模型与预算，只改变观察或编辑契约。`EditTool.str_replace`的唯一匹配反馈与 `DefaultAgent.forward_with_handling`的重询逻辑说明，同一个正式step可能含多个失败尝试；轨迹与模型实际看到的history并非同一份记录。保存trajectory有助于分析，但不足以证明环境可完整重建。[EditTool.str_replace](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/tools/edit_anthropic/bin/str_replace_editor)；[DefaultAgent循环与轨迹](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/sweagent/agent/agents.py)；[轨迹字段文档](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/docs/usage/trajectories.md)。

README已经建议新使用者转向mini-swe-agent，并说明主要开发投入迁移到后者。本库保留SWE-agent作为ACI案例，未读取并验证一套迁移实现，也不把README的性能措辞当成独立复测结果。[SWE-agent维护说明](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/README.md)。学习入口：[SWEAgent与智能体计算机接口](../wiki/topics/SWEAgent与智能体计算机接口.md)；[swe-agent.py](../examples/agents/swe-agent.py)提供 `file_window`、`unique_edit`、`retry_trace`。

### Aider：需要研究仓库上下文与可控文本编辑

Aider把三个问题拆得比较清楚：RepoMap从定义/引用建立加权图，个性化PageRank将聊天涉及文件和符号纳入排序；再把排名渲染为预算附近的代码地图；编辑协议处理模型输出的SEARCH/REPLACE；Git集成管理改动历史。地图选择不是“把整个仓库塞入提示”。该版本预算搜索允许约15%的相对误差，不能称为严格硬token上限。[Repository map官方说明](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/website/docs/repomap.md)；[get_ranked_tags与get_ranked_tags_map_uncached](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/repomap.py)。

适合关注交互式仓库修改、上下文预算与补丁可靠性的读者。所读 `perfect_replace`取第一个精确匹配；后续还有缩进和省略号分支，而编辑距离模糊匹配调用位于提前return之后，在这条路径不可达。因此不能将Aider描述成统一“唯一匹配编辑器”，也不能仅按函数名推断模糊匹配一定执行。[编辑格式说明](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/website/docs/more/edit-formats.md)；[SEARCH/REPLACE实际匹配路径](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/editblock_coder.py)。

`check_for_dirty_commit`在启用相关配置且文件有已有改动时安排编辑前检查点，Git集成还可以被关闭。检查点帮助区分文件改动来源和回退依据，并不等于每个hunk都能准确归属，更不证明修改满足业务任务。动态导入可能漏出静态图，重复代码可能让首匹配落在错误位置。[Coder编辑准备与提交逻辑](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/coders/base_coder.py)；[Git集成与关闭条件](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/website/docs/git.md)。学习入口：[Aider仓库地图与编辑协议](../wiki/topics/Aider仓库地图与编辑协议.md)，配合[aider.py](../examples/agents/aider.py)的 `repo_map`、`search_replace`、`commit_plan`。

### Codex CLI：需要研究公开客户端与工具运行层

这里指openai/codex的客户端，不是历史代码生成研究中的同名模型。固定版本的exec前端使用进程内App Server客户端，经Thread/Turn接口开始会话；共享tools crate没有承接所有核心编排，依赖会话与审批的逻辑仍留在core。入口、前端、核心工具层和模型配置应分开看。[codex-core说明](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/core/README.md#L1)；[codex-tools职责与迁移边界](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/tools/README.md#L1)；[run_main与run_exec_session](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/exec/src/lib.rs#L854)。

适合研究工具注册、执行前策略、事件输出与进程生命周期。`ToolRouter.build_tool_call`先规范化不同工具项，注册表检查工具及载荷类型，`ToolOrchestrator.run`再处理执行前要求；工具被注册不等于必然向模型可见。输出保留字节数、可发送增量事件数、取消与超时各有独立机制，丢掉部分输出不能直接当作执行失败。[ToolRouter](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/core/src/tools/router.rs#L257)；[ToolRegistry](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/core/src/tools/registry.rs#L691)；[ToolOrchestrator](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/core/src/tools/orchestrator.rs#L125)；[进程与输出回收](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/core/src/exec.rs#L982)。

归档记录中OpenAI产品文档站未取得可用正文。因此本文不补写账号能力、当前发行默认配置、服务端实现或未核验文档结论。学习入口：[CodexCLI架构与执行](../wiki/topics/CodexCLI架构与执行.md)，[codex-cli.py](../examples/agents/codex-cli.py)的 `launch_plan`、`route_call`、`capture_output`只模拟入口、准入与输出上限。

### Claude Code：需要公开扩展接口，而非假定核心可改

归档的官方工作机制核验记录说明产品按收集上下文、采取行动、验证结果循环；接近上下文容量时会清理旧工具输出并按需压缩。本库对该网页仅保留精简观察记录，不声称持有完整正文指纹，也不据此编造压缩函数、阈值或内部存储结构。产品仓库条款与MIT的Python SDK许可不同。[官方工作机制说明及已登记读取范围](https://code.claude.com/docs/en/how-claude-code-works)；[产品仓库许可边界](https://github.com/anthropics/claude-code/blob/318b7e6ac4e726e88a4ad326214866a93c373b1b/LICENSE.md#L1)；[Python SDK许可](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/LICENSE#L1)。

适合研究如何将已有客户端能力接入应用、增加hook或进程内MCP工具。实际可读链是 `SubprocessCLITransport`启动和传输、`ClaudeSDKClient.query/receive_response`管理一次响应窗口、`Query._handle_control_request`分发控制回调、`create_sdk_mcp_server`适配工具。`ResultMessage`结束响应不等于代码任务通过；hook协议返回success可以同时包含deny，外层状态不能替代动作决策。[SDK子进程传输](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L570)；[SDK响应边界](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/src/claude_agent_sdk/client.py#L272)；[SDK控制回调](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/src/claude_agent_sdk/_internal/query.py#L577)；[SDK MCP工具适配](https://github.com/anthropics/claude-agent-sdk-python/blob/0e89b298e771259378a6cd3734e00d323dff5703/src/claude_agent_sdk/__init__.py#L620)。

如果目标是修改完整客户端核心，应先确认公开范围能满足要求，不能拿SDK仓库的可读性代替核心开放性。学习入口：[ClaudeCode工作流与扩展边界](../wiki/topics/ClaudeCode工作流与扩展边界.md)，配合[claude-code.py](../examples/agents/claude-code.py)的 `response_window`、`hook_reply`、`sdk_tool_route`验证接口契约；这些函数不复现未公开产品内部循环。

## 编排任务：图状态与对话状态的取舍

### LangGraph：显式控制状态归并与恢复点

LangGraph适合流程中存在明确依赖、并行结果归并、人工检查和恢复需求的任务。`PregelLoop`在超步边界应用写入；`LastValue.update`不接受同一步多个值，显式归并器才定义如何合并。检查点、pending writes和Store分别表达执行快照、部分任务写入与跨线程应用数据；把它们都叫“记忆”会掩盖生命周期差异。[apply_writes](https://github.com/langchain-ai/langgraph/blob/4c52e129eb1ab69a3da58b799f67929f77d81149/libs/langgraph/langgraph/pregel/_algo.py#L233)；[LastValue.update](https://github.com/langchain-ai/langgraph/blob/4c52e129eb1ab69a3da58b799f67929f77d81149/libs/langgraph/langgraph/channels/last_value.py#L56)；[Persistence官方说明](https://docs.langchain.com/oss/python/langgraph/persistence)。

恢复代价必须读到节点内部：`interrupt`用恢复输入继续时，从节点开头重新运行，并按调用次序匹配答案。中断前的外部动作可能再次发生，checkpoint不能自动包住文件或数据库副作用；InMemorySaver也不提供跨进程持久化。选型时应分别评估状态Schema、归并器、持久化后端和业务幂等，而非只确认框架有resume。[interrupt重跑语义](https://github.com/langchain-ai/langgraph/blob/4c52e129eb1ab69a3da58b799f67929f77d81149/libs/langgraph/langgraph/types.py#L903)；[InMemorySaver](https://github.com/langchain-ai/langgraph/blob/4c52e129eb1ab69a3da58b799f67929f77d81149/libs/checkpoint/langgraph/checkpoint/memory/__init__.py#L430)。

学习入口：[LangGraph状态图与持久化](../wiki/topics/LangGraph状态图与持久化.md)，用[langgraph.py](../examples/harness/langgraph.py)中的 `merge_superstep`、`checkpoint_writes`、`replay_interrupt_node`检查写冲突、任务身份和中断重放；真实断电恢复与存储一致性还需集成实验。

### AutoGen：研究对话团队的游标、终止和存档

本文限定AgentChat的RoundRobin路径：`select_speaker`推进参与者游标；管理器收到增量消息后应用状态化终止条件；团队存档覆盖参与者与管理器。轮询规则决定谁发言，不能直接代表更好的推理分工。AND条件可以跨消息批次锁存各子条件，重复提交全历史会改变计数语义。[RoundRobinGroupChatManager](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_round_robin_group_chat.py#L58)；[管理器处理增量消息](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat_manager.py#L135)；[终止条件组合](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/python/packages/autogen-agentchat/src/autogen_agentchat/base/_termination.py#L15)。

它适合学习已有对话团队工程、分析停止规则和研究旧系统恢复。新项目选型需先读维护状态：该固定README顶部明确归档且微软不再维护，后文仍留有maintenance措辞；归档API快照标志又是false。本文保留这些不同来源的事实，不能因API标志为false宣称上游继续提供支持。README指向Microsoft Agent Framework，本库没有据此验证迁移实现或兼容性。[AutoGen固定版本维护公告](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/README.md#L1)。

学习入口：[AutoGen对话团队与终止](../wiki/topics/AutoGen对话团队与终止.md)，[autogen.py](../examples/harness/autogen.py)的 `select_round_robin`、`termination_step`、`snapshot_team`用于手算游标、增量停止和一致快照。运行中逐个采状态不自动形成同一时刻快照，重新run也不一定从全空历史开始。[团队save_state/load_state](https://github.com/microsoft/autogen/blob/004749e6b7102c8fd317b9b1499ce5807223c278/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py#L748)。

## 怎样把导读变成选型实验

先写任务契约，再选两种可比实现。环境、模型、提示和预算不同会共同影响结果；若不能使用同一模型，应明确这是系统组合比较，不能把差异都归给框架。下表是可执行的实验设计，不是已经完成的结果。

| 任务与候选方向 | 先做的低成本检查 | 进入真实实验后必须冻结与记录 |
| --- | --- | --- |
| 手机重复任务：Mobile-Agent-v2与AppAgent | 相同界面的观测身份、动作描述、过期知识和回退记录 | 应用/设备版本、截图/XML一致性、是否使用探索文档、步数与重试、独立终态；探索成本单独计入 |
| 桌面截图动作：UI-TARS与自己现有的Operator流程 | 模型输出到点击坐标的逐层换算、未知动作与call_user边界 | 模型版本、显示缩放、截图尺寸、执行器版本、定位错误与业务失败分层统计 |
| 仓库补丁：SWE-agent、Aider、OpenHands等 | 同一基线下的文件观察、歧义替换、失败反馈、事件归属 | 问题集、仓库commit、测试环境、补丁身份、工具权限、总token/调用/时间预算、人工干预 |
| 客户端嵌入：Codex CLI与Claude SDK | 输入、流事件、响应边界、取消和工具扩展契约 | 区分能改客户端源码和只能扩展SDK；记录进程状态、输出截断与最终业务验收，模型条件单列 |
| 可恢复工作流：LangGraph与既有AutoGen团队 | 同一节点或发言中断后保留了哪些状态、哪些动作会重放 | 持久化后端、节点/角色版本、失败注入点、外部幂等键、恢复后终态；AutoGen维护限制单列 |

评价至少分三层：协议与教学性质、真实接口集成、固定任务集效果。补丁任务连接[Agent任务基准与执行评估](../wiki/topics/Agent任务基准与执行评估.md)，界面任务连接[多模态与界面感知评测](../wiki/topics/多模态与界面感知评测.md)，工具与失败预算连接[稳健性与工具安全评测](../wiki/topics/稳健性与工具安全评测.md)。多模态评测还包括视觉理解、任务答案解析和分层错误，不等同于GUI坐标命中率。

报告应同时保留首次成功、固定重试预算后的成功、超时/未知、人工介入、成本和回归失败。若只是运行本库纯函数，应写“教学契约检查”，不能写成SWE-bench复现、设备任务通过或托管产品性能。本文及关联示例均未执行上述真实模型或设备对照。

## 关注度与维护状态快照

下面数据转录自2026-10-24归档的GitHub仓库API记录，表示该日快照。star表示账号关注动作，fork表示仓库分叉计数，二者都不是活跃用户、部署量、使用率或质量测量。OpenHands一行统计Canvas所在仓库，不是SDK；Claude Code一行统计产品仓库，不是SDK。该次采集没有AppAgent记录，因此保留缺失值。

| 官方仓库 | star | fork | API archived快照 |
| --- | ---: | ---: | --- |
| [X-PLUG/MobileAgent](https://github.com/X-PLUG/MobileAgent) | 9324 | 935 | false |
| [TencentQQGYLab/AppAgent](https://github.com/TencentQQGYLab/AppAgent) | 未采集 | 未采集 | 未采集 |
| [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop) | 39372 | 3995 | false |
| [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | 91701 | 12166 | false |
| [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) | 20629 | 2263 | false |
| [Aider-AI/aider](https://github.com/Aider-AI/aider) | 49731 | 5102 | false |
| [openai/codex](https://github.com/openai/codex) | 130739 | 20619 | false |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 153220 | 26655 | false |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 43808 | 7521 | false |
| [microsoft/autogen](https://github.com/microsoft/autogen) | 61545 | 9312 | false |

表内保留采集日期与原数值，当前仓库页面可能已经变化；历史快照不因当前计数变化而被静默覆盖。源码与文档身份可从[来源清单](../sources/manifest/sources.json)及[来源索引](../sources/来源索引.md)回查。维护状态优先保留具体公告的措辞与时间，不用星数增长推测维护承诺；API许可证检测字段也不能代替实际许可文件，例如AutoGen必须区分文档与代码许可。

本导读保留三个明确缺口：没有十方案同任务实测，没有全部依赖/权重/服务条款核验，没有未公开客户端或托管产品内核证据。后续若补充这些材料，应按[持续更新指南](持续更新指南.md)登记实际读取或运行范围，再更新受影响段落。
