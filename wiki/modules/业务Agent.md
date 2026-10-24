# 业务Agent

本模块目前包含4个知识单元。先选择希望获得的能力，再按前置关系进入主题；主题提供具体示例与实践设计，未完成实验不会标记为已验证。

## 核心知识单元

| 主题 | 学习目标 |
|---|---|
| [业务Agent任务闭环](../topics/业务Agent任务闭环.md) | 把用户目标转换成终态契约；区分过程和结果；设计恢复与补偿 |
| [GUI定位与执行](../topics/GUI定位与执行.md) | 统一截图与坐标空间；区分定位和执行；设计视觉状态验证 |
| [AI代码开发与反馈](../topics/AI代码开发与反馈.md) | 按契约形成补丁；区分测试缺口与修复；记录可复查证据 |
| [Agent评测与失败归因](../topics/Agent评测与失败归因.md) | 建立分层评测；按轨迹归因；衔接Benchmark模块 |

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

跨应用真实任务、长期任务恢复、多Agent协作及失败归因案例。本版补齐学习框架与核心主题，不宣称覆盖本领域全部知识。后续按[研究队列](../../docs/研究队列.md)和证据质量推进。

返回[知识地图](../../docs/大模型持续学习知识库.md)。
