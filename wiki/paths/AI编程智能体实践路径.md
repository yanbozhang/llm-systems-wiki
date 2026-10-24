# AI编程智能体实践路径

沿仓库上下文、编辑协议、运行反馈和独立验收学习代码Agent，明确客户端与模型的边界。

## 前置与证据边界

先能为一个小函数写出行为契约和反例；只阅读、推演现有教学字符串与事件，不运行生成程序、不执行Git操作。 基础入口见[共同基础](../../docs/共同基础.md)，能力身份见[能力地图](../../docs/能力地图.md)。

已完成的是已有主题与标准库教学示例的编纂。本路径把它们组织为学习行动和可提交产物；端到端项目、真实模型、GPU服务或真机实验尚未执行。阅读、手算、示例验证与真实实验需分别记录；教学代码运行结果以对应版本的CI为准。

## 四层学习行动

| 层级与能力ID | 代表知识点及示例函数 | 学习行动与提交 | 验收判据 |
| --- | --- | --- | --- |
| 理解<br>`agents-understand` | [codex-cli-launch-plan](../topics/CodexCLI架构与执行.md) → [launch_plan()](../../examples/agents/codex-cli.py#L4)<br>[claude-code-response-window](../topics/ClaudeCode工作流与扩展边界.md) → [response_window()](../../examples/agents/claude-code.py#L4)<br>[openhands-branch](../topics/OpenHands事件流与运行时.md) → [conversation_path()](../../examples/agents/openhands.py#L5) | 分别画Codex入口分派、Claude Code公开SDK响应窗口和OpenHands活动事件分支。 | 客户端与基础模型分开；SDK或社区代码不能证明闭源/托管核心；日志追加顺序不必等于活动分支顺序。 |
| 推导<br>`agents-derive`、`harness-derive` | [aider-repomap](../topics/Aider仓库地图与编辑协议.md) → [repo_map()](../../examples/agents/aider.py#L6)<br>[coding-agent-repository-slice](../topics/AI代码开发与反馈.md) → [repository_slice()](../../examples/agents/coding-agent.py#L6)<br>[swe-agent-trajectory](../topics/SWEAgent与智能体计算机接口.md) → [retry_trace()](../../examples/agents/swe-agent.py#L33) | 对给定调用图计算上下文范围与仓库地图预算，并展开一个step内的多次失败尝试。 | 图与边权已给定且可能漏动态调用；格式重询不一定是新的环境step；所有成本保留。 |
| 实践<br>`agents-build` | [coding-agent-guarded-replace](../topics/AI代码开发与反馈.md) → [guarded_replace()](../../examples/agents/coding-agent.py#L23)<br>[swe-agent-edit-contract](../topics/SWEAgent与智能体计算机接口.md) → [unique_edit()](../../examples/agents/swe-agent.py#L18)<br>[aider-edit-format](../topics/Aider仓库地图与编辑协议.md) → [search_replace()](../../examples/agents/aider.py#L49)<br>[codex-cli-route-call](../topics/CodexCLI架构与执行.md) → [route_call()](../../examples/agents/codex-cli.py#L18)<br>[claude-code-sdk-tool-route](../topics/ClaudeCode工作流与扩展边界.md) → [sdk_tool_route()](../../examples/agents/claude-code.py#L34) | 准备基线冲突、非唯一锚点、无变化、未知工具和合法候选五类输入；提交内存补丁和反馈表。 | 失败编辑不改变原文；Aider与SWE-agent匹配政策分别说明；载荷、工具注册和执行准入不等于业务验收。 |
| 评估<br>`agents-evaluate`、`benchmark-build` | [coding-agent-grade-patch](../topics/AI代码开发与反馈.md) → [grade_patch()](../../examples/agents/coding-agent.py#L34)<br>[benchmark-agents-task-acceptance](../topics/Agent任务基准与执行评估.md) → [grade_patch()](../../examples/benchmark/benchmark-agents.py#L4)<br>[codex-cli-capture-output](../topics/CodexCLI架构与执行.md) → [capture_output()](../../examples/agents/codex-cli.py#L46)<br>[claude-code-hook-reply](../topics/ClaudeCode工作流与扩展边界.md) → [hook_reply()](../../examples/agents/claude-code.py#L18)<br>[openhands-observation](../topics/OpenHands事件流与运行时.md) → [observation_links()](../../examples/agents/openhands.py#L50) | 用独立给定结果核对修复和回归，再加入输出截断、hook拒绝和缺观察事件。 | 评分证据绑定同一补丁版本；两种grade_patch采用各自输入契约；进程退出、控制响应success和观察配对均不自动表示任务解决。 |

## 专题分支与实现边界

代码方案分支：OpenHands区分Canvas、software-agent-sdk与托管层；SWE-agent保留其固定默认配置与ACI研究语境，后继项目未在本路径推断；Aider分别核对仓库地图、SEARCH/REPLACE和Git计划，commit_plan只产生教学计划。Codex CLI与Claude Code用于宿主/SDK边界对照，不用同名历史模型的成绩替代客户端评价。

| 方案与实现范围 | 已有知识点及函数 | 学习行动与验收 |
| --- | --- | --- |
| [CodexCLI架构与执行](../topics/CodexCLI架构与执行.md)<br>固定提交970111f6：Rust CLI/exec、App Server客户端与core工具层；不是历史同名模型。 | [codex-cli-launch-plan](../topics/CodexCLI架构与执行.md) → [launch_plan()](../../examples/agents/codex-cli.py#L4)<br>[codex-cli-route-call](../topics/CodexCLI架构与执行.md) → [route_call()](../../examples/agents/codex-cli.py#L18)<br>[codex-cli-capture-output](../topics/CodexCLI架构与执行.md) → [capture_output()](../../examples/agents/codex-cli.py#L46) | 比较入口分派、工具准入与输出保留上限，提交责任和状态矩阵。<br>验收：区分输出截断与进程结束；未核验产品文档不能用仓库跳转链接替代。 |
| [ClaudeCode工作流与扩展边界](../topics/ClaudeCode工作流与扩展边界.md)<br>公开SDK提交0e89b298及已登记产品说明；SDK公开不代表客户端核心完全开源。 | [claude-code-response-window](../topics/ClaudeCode工作流与扩展边界.md) → [response_window()](../../examples/agents/claude-code.py#L4)<br>[claude-code-hook-reply](../topics/ClaudeCode工作流与扩展边界.md) → [hook_reply()](../../examples/agents/claude-code.py#L18)<br>[claude-code-sdk-tool-route](../topics/ClaudeCode工作流与扩展边界.md) → [sdk_tool_route()](../../examples/agents/claude-code.py#L34) | 演示result到达、hook控制回复和进程内工具路由。<br>验收：控制回复success与工具deny可并存；产品描述、SDK实现、未公开核心及各自许可分开。 |
| [OpenHands事件流与运行时](../topics/OpenHands事件流与运行时.md)<br>Canvas提交fee10e3d、software-agent-sdk提交acd96e6f；托管Cloud另属产品部署层。 | [openhands-branch](../topics/OpenHands事件流与运行时.md) → [conversation_path()](../../examples/agents/openhands.py#L5)<br>[openhands-projection](../topics/OpenHands事件流与运行时.md) → [project_action_batches()](../../examples/agents/openhands.py#L25)<br>[openhands-observation](../topics/OpenHands事件流与运行时.md) → [observation_links()](../../examples/agents/openhands.py#L50) | 给定父链回放活动分支，合并同响应动作，核对三项观察身份。<br>验收：事件日志、模型消息与文件状态不混同；观察配对不是业务成功，也不自动保证工具重放幂等。 |
| [SWEAgent与智能体计算机接口](../topics/SWEAgent与智能体计算机接口.md)<br>提交3ea751c0的默认工具配置与ACI研究；维护者推荐后继项目的事实不等于已分析其代码。 | [swe-agent-observation](../topics/SWEAgent与智能体计算机接口.md) → [file_window()](../../examples/agents/swe-agent.py#L5)<br>[swe-agent-edit-contract](../topics/SWEAgent与智能体计算机接口.md) → [unique_edit()](../../examples/agents/swe-agent.py#L18)<br>[swe-agent-trajectory](../topics/SWEAgent与智能体计算机接口.md) → [retry_trace()](../../examples/agents/swe-agent.py#L33) | 展示一基窗口，构造唯一编辑与失败重询，提交完整step轨迹。<br>验收：当前配置和论文接口区别明确；编辑失败保留原文，done和测试通过分开。 |
| [Aider仓库地图与编辑协议](../topics/Aider仓库地图与编辑协议.md)<br>提交5dc9490b：RepoMap、SEARCH/REPLACE与文件级Git边界。 | [aider-repomap](../topics/Aider仓库地图与编辑协议.md) → [repo_map()](../../examples/agents/aider.py#L6)<br>[aider-edit-format](../topics/Aider仓库地图与编辑协议.md) → [search_replace()](../../examples/agents/aider.py#L49)<br>[aider-git-boundary](../topics/Aider仓库地图与编辑协议.md) → [commit_plan()](../../examples/agents/aider.py#L84) | 手算图排序预算，比较匹配反馈，生成用户改动与Agent编辑的提交计划。<br>验收：地图匹配与补丁应用不证明代码正确；commit_plan不执行真实提交，现有用户改动边界须保留。 |

## 结业产物与复核

提交同一虚构修复任务的协议比较：上下文选择、候选补丁、失败反馈、事件关联和独立测试判据。比较能解释的机制，不在没有模型/环境运行数据时给五个产品排正确率名次。

复核者应能从能力ID、unit_id、主题版本、示例路径/函数、输入和预期重建推演。至少保留一个失败或未知样例，并说明源码已覆盖与教学省略的部分；任何实测结果都需另附原始记录，不能用预期值填写。

使用[学习记录模板](../../templates/学习记录模板.md)、[实验记录模板](../../templates/实验记录模板.md)和[评测协议模板](../../templates/评测协议模板.md)组织产物。可将本路径接入[三个跨模块实践项目](../../docs/跨模块实践项目.md)；真实剩余实验见[研究队列](../../docs/研究队列.md)。

下一步：[Agent开发路径](Agent开发路径.md)、[Benchmark学习路径](Benchmark学习路径.md)、[系统工程路径](系统工程路径.md)。
