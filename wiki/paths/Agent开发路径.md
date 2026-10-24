# Agent开发路径

从任务契约组织工具、上下文、状态与恢复，并能分层阅读十个已有实现专题。

## 前置与证据边界

具备基本Python字典与状态机知识；先从业务目标及可信终态证据开始，不按角色数量选择系统。 基础入口见[共同基础](../../docs/共同基础.md)，能力身份见[能力地图](../../docs/能力地图.md)。

已完成的是已有主题与标准库教学示例的编纂。本路径把它们组织为学习行动和可提交产物；端到端项目、真实模型、GPU服务或真机实验尚未执行。阅读、手算、示例验证与真实实验需分别记录；教学代码运行结果以对应版本的CI为准。

## 四层学习行动

| 层级与能力ID | 代表知识点及示例函数 | 学习行动与提交 | 验收判据 |
| --- | --- | --- | --- |
| 理解<br>`harness-understand`、`agents-build` | [task-loop-terminal-contract](../topics/业务Agent任务闭环.md) → [terminal_contract()](../../examples/agents/task-loop.py#L4)<br>[tools-skills-validate-query](../topics/工具协议与MCP及Skill.md) → [validate_query()](../../examples/harness/tools-skills.py#L4)<br>[tools-skills-classify-response](../topics/工具协议与MCP及Skill.md) → [classify_response()](../../examples/harness/tools-skills.py#L17) | 给模拟资料整理任务写True/False/None终态契约，列出模型、工具、协议和宿主责任。 | 动作下发、工具回执和业务成功分开；结果未知先回读；Schema不替代权限或语义校验。 |
| 推导<br>`harness-derive` | [agent-loop-admit-budget](../topics/Harness任务循环.md) → [admit_budget()](../../examples/harness/agent-loop.py#L25)<br>[context-select-context](../topics/上下文选择与压缩.md) → [select_context()](../../examples/harness/context.py#L4)<br>[context-trim-complete-turns](../topics/上下文选择与压缩.md) → [trim_complete_turns()](../../examples/harness/context.py#L29) | 手算执行前预算预留与上下文选择，裁剪完整调用回合；提交预算和消息配对表。 | 必要项不可被低价值裁剪；调用与结果保持闭包；重试与回读都计预算。 |
| 实践<br>`harness-build` | [langgraph-checkpoint-writes](../topics/LangGraph状态图与持久化.md) → [checkpoint_writes()](../../examples/harness/langgraph.py#L29)<br>[langgraph-replay-interrupt-node](../topics/LangGraph状态图与持久化.md) → [replay_interrupt_node()](../../examples/harness/langgraph.py#L45)<br>[autogen-snapshot-team](../topics/AutoGen对话团队与终止.md) → [snapshot_team()](../../examples/harness/autogen.py#L40) | 分别设计图式恢复与团队恢复，用同一任务目标比较所需状态，不把两套API合并。 | 图恢复保留检查点作用域与答案顺序；团队恢复保留管理器和参与者；外部副作用另行回查和幂等。 |
| 评估<br>`harness-evaluate`、`agents-evaluate` | [context-audit-checkpoint](../topics/上下文选择与压缩.md) → [audit_checkpoint()](../../examples/harness/context.py#L61)<br>[memory-eligible-memories](../topics/Agent记忆与保鲜.md) → [eligible_memories()](../../examples/harness/memory.py#L5)<br>[agent-evaluation-first-divergence](../topics/Agent评测与失败归因.md) → [first_divergence()](../../examples/agents/agent-evaluation.py#L21)<br>[agent-evaluation-success-summary](../topics/Agent评测与失败归因.md) → [success_summary()](../../examples/agents/agent-evaluation.py#L4) | 加入旧记忆、遗漏约束、重复触发及结果未知，提交完整轨迹、首轮/重试分母和最早偏差候选。 | 过期或异域记忆先失去资格；最早偏差不直接等于因果根因；不能只发布最终较高成功率。 |

## 专题分支与实现边界

通用闭环之后按下表选择实现案例。每个案例的固定提交、读取范围与许可边界由对应主题维护；此路径不扩展外部调查，也不把不同项目或不同代方案拼成一个不存在的系统。

| 方案与实现范围 | 已有知识点及函数 | 学习行动与验收 |
| --- | --- | --- |
| [LangGraph状态图与持久化](../topics/LangGraph状态图与持久化.md)<br>固定提交4c52e129：状态图、超步、检查点与interrupt；内存Saver不等于生产持久化。 | [langgraph-merge-superstep](../topics/LangGraph状态图与持久化.md) → [merge_superstep()](../../examples/harness/langgraph.py#L5)<br>[langgraph-checkpoint-writes](../topics/LangGraph状态图与持久化.md) → [checkpoint_writes()](../../examples/harness/langgraph.py#L29)<br>[langgraph-replay-interrupt-node](../topics/LangGraph状态图与持久化.md) → [replay_interrupt_node()](../../examples/harness/langgraph.py#L45) | 比较sum/last多写，两个thread作用域与节点重跑；提交恢复身份表。<br>验收：并行状态归并、pending writes和外部副作用分别说明，不能把恢复理解成原调用栈续跑。 |
| [AutoGen对话团队与终止](../topics/AutoGen对话团队与终止.md)<br>固定提交004749e6：AgentChat轮询、状态化终止与团队快照；所读README顶部有归档公告。 | [autogen-select-round-robin](../topics/AutoGen对话团队与终止.md) → [select_round_robin()](../../examples/harness/autogen.py#L5)<br>[autogen-termination-step](../topics/AutoGen对话团队与终止.md) → [termination_step()](../../examples/harness/autogen.py#L16)<br>[autogen-snapshot-team](../topics/AutoGen对话团队与终止.md) → [snapshot_team()](../../examples/harness/autogen.py#L40) | 让writer/critic轮询，分批满足AND/OR条件，再核对团队快照。<br>验收：终止文本校验来源；停止不等于业务成功；存档覆盖管理器和参与者，不推断当前维护承诺。 |
| [CodexCLI架构与执行](../topics/CodexCLI架构与执行.md)<br>固定提交970111f6：Rust CLI/exec、App Server客户端与core工具层；不是历史同名模型。 | [codex-cli-launch-plan](../topics/CodexCLI架构与执行.md) → [launch_plan()](../../examples/agents/codex-cli.py#L4)<br>[codex-cli-route-call](../topics/CodexCLI架构与执行.md) → [route_call()](../../examples/agents/codex-cli.py#L18)<br>[codex-cli-capture-output](../topics/CodexCLI架构与执行.md) → [capture_output()](../../examples/agents/codex-cli.py#L46) | 比较入口分派、工具准入与输出保留上限，提交责任和状态矩阵。<br>验收：区分输出截断与进程结束；未核验产品文档不能用仓库跳转链接替代。 |
| [ClaudeCode工作流与扩展边界](../topics/ClaudeCode工作流与扩展边界.md)<br>公开SDK提交0e89b298及已登记产品说明；SDK公开不代表客户端核心完全开源。 | [claude-code-response-window](../topics/ClaudeCode工作流与扩展边界.md) → [response_window()](../../examples/agents/claude-code.py#L4)<br>[claude-code-hook-reply](../topics/ClaudeCode工作流与扩展边界.md) → [hook_reply()](../../examples/agents/claude-code.py#L18)<br>[claude-code-sdk-tool-route](../topics/ClaudeCode工作流与扩展边界.md) → [sdk_tool_route()](../../examples/agents/claude-code.py#L34) | 演示result到达、hook控制回复和进程内工具路由。<br>验收：控制回复success与工具deny可并存；产品描述、SDK实现、未公开核心及各自许可分开。 |
| [MobileAgent多智能体协作](../topics/MobileAgent多智能体协作.md)<br>X-PLUG/MobileAgent的Mobile-Agent-v2；固定提交11cea575，不混入v3/E/PC等目录。 | [mobile-agent-perception](../topics/MobileAgent多智能体协作.md) → [perception_index()](../../examples/agents/mobile-agent.py#L5)<br>[mobile-agent-planning-memory](../topics/MobileAgent多智能体协作.md) → [planning_projection()](../../examples/agents/mobile-agent.py#L36)<br>[mobile-agent-reflection](../topics/MobileAgent多智能体协作.md) → [reflection_transition()](../../examples/agents/mobile-agent.py#L52) | 按框中心建立感知索引，分别推进规划事实与A/B/C反思状态。<br>验收：v2接受历史、回退后再观测与无效动作分别记录；几何框是给定输入，不是实机识别结果。 |
| [AppAgent探索与技能学习](../topics/AppAgent探索与技能学习.md)<br>TencentQQGYLab/AppAgent；固定提交2c190042，探索文档和当前UID检索路径。 | [app-agent-element-identity](../topics/AppAgent探索与技能学习.md) → [element_identity()](../../examples/agents/app-agent.py#L5)<br>[app-agent-document-learning](../topics/AppAgent探索与技能学习.md) → [learn_action_document()](../../examples/agents/app-agent.py#L25)<br>[app-agent-deployment](../topics/AppAgent探索与技能学习.md) → [deployment_context()](../../examples/agents/app-agent.py#L45) | 改变元素属性观察UID，更新动作文档槽位，再按当前界面选择文档与点位。<br>验收：外部知识积累不是微调；UID跨版本不保证稳定，部署FINISH仍需独立终态。 |
| [UITARS感知与动作执行](../topics/UITARS感知与动作执行.md)<br>UI-TARS-desktop提交3ac2cb8d：LocalComputer→SDK→NutJS，以V1_0分支为主。 | [ui-tars-action-protocol](../topics/UITARS感知与动作执行.md) → [parse_action()](../../examples/agents/ui-tars.py#L8)<br>[ui-tars-coordinate-path](../topics/UITARS感知与动作执行.md) → [grounding_coordinates()](../../examples/agents/ui-tars.py#L41)<br>[ui-tars-loop-state](../topics/UITARS感知与动作执行.md) → [agent_loop_transition()](../../examples/agents/ui-tars.py#L61) | 严格解析动作，区分归一化、屏幕点和显示缩放，再推演轮数预算。<br>验收：模型、SDK、桌面宿主、执行器各自负责的字段明确；V1_5另列，不拼坐标规则。 |
| [OpenHands事件流与运行时](../topics/OpenHands事件流与运行时.md)<br>Canvas提交fee10e3d、software-agent-sdk提交acd96e6f；托管Cloud另属产品部署层。 | [openhands-branch](../topics/OpenHands事件流与运行时.md) → [conversation_path()](../../examples/agents/openhands.py#L5)<br>[openhands-projection](../topics/OpenHands事件流与运行时.md) → [project_action_batches()](../../examples/agents/openhands.py#L25)<br>[openhands-observation](../topics/OpenHands事件流与运行时.md) → [observation_links()](../../examples/agents/openhands.py#L50) | 给定父链回放活动分支，合并同响应动作，核对三项观察身份。<br>验收：事件日志、模型消息与文件状态不混同；观察配对不是业务成功，也不自动保证工具重放幂等。 |
| [SWEAgent与智能体计算机接口](../topics/SWEAgent与智能体计算机接口.md)<br>提交3ea751c0的默认工具配置与ACI研究；维护者推荐后继项目的事实不等于已分析其代码。 | [swe-agent-observation](../topics/SWEAgent与智能体计算机接口.md) → [file_window()](../../examples/agents/swe-agent.py#L5)<br>[swe-agent-edit-contract](../topics/SWEAgent与智能体计算机接口.md) → [unique_edit()](../../examples/agents/swe-agent.py#L18)<br>[swe-agent-trajectory](../topics/SWEAgent与智能体计算机接口.md) → [retry_trace()](../../examples/agents/swe-agent.py#L33) | 展示一基窗口，构造唯一编辑与失败重询，提交完整step轨迹。<br>验收：当前配置和论文接口区别明确；编辑失败保留原文，done和测试通过分开。 |
| [Aider仓库地图与编辑协议](../topics/Aider仓库地图与编辑协议.md)<br>提交5dc9490b：RepoMap、SEARCH/REPLACE与文件级Git边界。 | [aider-repomap](../topics/Aider仓库地图与编辑协议.md) → [repo_map()](../../examples/agents/aider.py#L6)<br>[aider-edit-format](../topics/Aider仓库地图与编辑协议.md) → [search_replace()](../../examples/agents/aider.py#L49)<br>[aider-git-boundary](../topics/Aider仓库地图与编辑协议.md) → [commit_plan()](../../examples/agents/aider.py#L84) | 手算图排序预算，比较匹配反馈，生成用户改动与Agent编辑的提交计划。<br>验收：地图匹配与补丁应用不证明代码正确；commit_plan不执行真实提交，现有用户改动边界须保留。 |

表中十个专题分属不同层：LangGraph/AutoGen提供编排机制，Codex/Claude Code提供客户端与SDK边界，GUI三方案与OpenHands/SWE-agent/Aider分别提供具体感知或编辑反馈案例。先复用同一个任务契约，再分别比较接口；不得凭角色数、仓库存在或代码许可推断完整产品能力。

## 结业产物与复核

提交一个只读资料整理任务的合成闭环：冻结输入→选择上下文→生成动作意图→给定工具反馈→权威回读→终态判定→错误复盘。计划更新进入候选记录，不把教学状态变化当作已经修改外部应用。

复核者应能从能力ID、unit_id、主题版本、示例路径/函数、输入和预期重建推演。至少保留一个失败或未知样例，并说明源码已覆盖与教学省略的部分；任何实测结果都需另附原始记录，不能用预期值填写。

使用[学习记录模板](../../templates/学习记录模板.md)、[实验记录模板](../../templates/实验记录模板.md)和[评测协议模板](../../templates/评测协议模板.md)组织产物。可将本路径接入[三个跨模块实践项目](../../docs/跨模块实践项目.md)；真实剩余实验见[研究队列](../../docs/研究队列.md)。

下一步：[GUI智能体实践路径](GUI智能体实践路径.md)、[AI编程智能体实践路径](AI编程智能体实践路径.md)、[Benchmark学习路径](Benchmark学习路径.md)。
