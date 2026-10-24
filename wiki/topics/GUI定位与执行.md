---
id: gui-agent
module: agents
status: published
page_version: 1
last_checked: 2026-10-24
claim_ids: [claim-gui-agent-v1]
---
# GUI定位与执行

GUI Agent 需要把任务意图映射到当前屏幕中的可操作元素。定位正确只是开始，后续还要确认动作实际产生了预期状态。

前置学习：[业务Agent任务闭环](业务Agent任务闭环.md)。所属模块：[业务Agent](../modules/业务Agent.md)。

## 基本机制

常见循环为截图或结构化观察、目标定位、动作下发、等待界面变化、重新观察和终态检查。视觉 grounding 用截图与指令定位元素；DOM 或无障碍树提供另一种观察方式。坐标必须对应同一次截图、分辨率、缩放与滚动位置。

依据：[SeeClick 原论文](https://arxiv.org/html/2401.10935v1)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)。完整来源与章节定位见[来源索引](../../sources/来源索引.md)。

## 方法演进

SeeClick 聚焦视觉 GUI grounding，并以 ScreenSpot 等数据评估；OSWorld 将任务扩展到真实桌面应用与跨应用流程。两者的任务定义和指标不同，不能直接把定位准确率当作端到端成功率。

## 适用条件与限制

页面布局、遮挡、弹窗、异步加载与状态变化会使旧坐标失效。动作工具返回成功只说明事件被发送，业务成功要回读界面或文件状态。

## 常见误区

反复点击同一位置可能把暂时延迟放大为重复提交；使用另一张图上的坐标也无法证明当前目标正确。

## 学习练习

按钮点击后页面没有变化，列出三种不同原因及下一步观察，而不是直接重试。

<details>
<summary>展开答案要点</summary>

可能点击未命中、请求仍在处理、已成功但提示未刷新；检查控件状态、加载指示、目标数据或文件，再决定等待、重定位或安全重试。

</details>

## 证据与后续阅读

本页是原始资料相关章节的编纂与教学推导，未独立复现实验。关键声明标识：`claim-gui-agent-v1`；实验效果、产品功能和教学建议不构成普遍保证。

[SeeClick 原论文](https://arxiv.org/html/2401.10935v1)；[OSWorld 原论文](https://arxiv.org/html/2404.07972v1)。

关联阅读：[Agent评测与失败归因](Agent评测与失败归因.md)。
