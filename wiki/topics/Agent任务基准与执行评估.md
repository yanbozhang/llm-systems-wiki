---
id: benchmark-agents
module: benchmark
status: published
page_version: 1
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-benchmark-agents-v1]
---
# Agent任务基准与执行评估

Agent基准比较的不仅是模型，还包括Harness、工具、环境、恢复策略和资源预算。基准名称相同也可能包含不同任务子集或评估器版本。

## 学习目标

- 选择Agent任务基准。
- 冻结环境与预算。
- 解释执行式评分。

## 前置知识

先阅读[评测协议与可复现性](评测协议与可复现性.md)；[业务Agent任务闭环](业务Agent任务闭环.md)，并能区分样本、任务、协议、指标和结论。缺少统计基础时先完成[共同基础](../../docs/共同基础.md)中的概率与实验自测。

## 基本机制

SWE-bench以仓库问题与补丁为任务入口；OSWorld面向真实计算机环境；WebArena系列面向Web任务；BFCL从函数调用扩展到多轮及Agent相关能力。每个基准都需明确动作空间、初始化、可见信息、终态判据和允许重试。

依据：[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)。这里整理方法定义与作者说明，不把项目自述的效果作为本库实测结论。

## 推导或示例

同一个修复任务中，系统A允许读取测试输出并修改三次，系统B只提交一次补丁。若只比较最终解决率，会把反馈预算差异算入模型能力。应同时报告首轮结果、预算内最终结果、调用和运行成本。

环境初始化失败应单独报告，但是否计入总体任务成功率必须事先规定。不能事后只排除表现不佳的环境或任务。

以上数值和场景用于教学，不是任何模型或平台的实测成绩。

## 适用条件与限制

离线基准不覆盖所有业务约束；执行式评分也可能漏掉副作用。BFCL不同版本覆盖范围有变化，必须注明所用版本。

## 常见误区

不同Agent系统用了不同工具或更长预算时，不能把差异全部归因于底层模型。

## 实践任务

为一个代码任务和一个界面任务分别填协议，列出模型、工具、环境和评估器版本；设计重复操作、环境故障及评估器误判的检查用例，并固定重试预算。

使用[评测协议模板](../../templates/评测协议模板.md)和[实验记录模板](../../templates/实验记录模板.md)保存设计；本页状态为“已设计”，未执行大模型基准。

## 掌握标准

能分清模型与系统贡献；能重建任务初始状态；保留全过程与终态证据；报告工具预算、失败和副作用。

复核时应展示协议、计算过程或失败样例。不能只提交一个分数而没有可查证的输入、版本与判据。

## 自测与复盘

在本主题中找出一个会改变分数却不代表模型能力改变的因素；设计一组对照以隔离它。再说明当前结论尚不能证明什么。

<details>
<summary>复盘要点</summary>

检查提示、数据版本、解析器、采样预算、工具权限、环境与聚合规则。对照应固定其余变量；说明样本范围、随机性、未测条件及可能的评估器误差。

</details>

## 来源与继续学习

[SWE-bench 项目说明](https://github.com/SWE-bench/SWE-bench/blob/main/README.md)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)；[Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)；[WebArena 基准](https://webarena.dev/)。来源读取范围见[来源索引](../../sources/来源索引.md)，学习顺序见[Benchmark学习路径](../paths/Benchmark学习路径.md)。

返回[Benchmark模块](../modules/Benchmark.md)，或查看[能力地图](../../docs/能力地图.md)。
