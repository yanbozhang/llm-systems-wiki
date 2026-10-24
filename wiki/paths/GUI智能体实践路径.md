# GUI智能体实践路径

用合成截图几何与状态记录，区分感知、规划、动作解析、执行回执与业务终态。

## 前置与证据边界

先完成Agent开发路径的任务契约、预算与回读；本路径不申请设备、不连接ADB、不控制鼠标键盘。 基础入口见[共同基础](../../docs/共同基础.md)，能力身份见[能力地图](../../docs/能力地图.md)。

已完成的是已有主题与标准库教学示例的编纂。本路径把它们组织为学习行动和可提交产物；端到端项目、真实模型、GPU服务或真机实验尚未执行。阅读、手算、示例验证与真实实验需分别记录；教学代码运行结果以对应版本的CI为准。

## 四层学习行动

| 层级与能力ID | 代表知识点及示例函数 | 学习行动与提交 | 验收判据 |
| --- | --- | --- | --- |
| 理解<br>`agents-understand`、`harness-understand` | [gui-agent-observation-gate](../topics/GUI定位与执行.md) → [observation_gate()](../../examples/agents/gui-agent.py#L25)<br>[ui-tars-action-protocol](../topics/UITARS感知与动作执行.md) → [parse_action()](../../examples/agents/ui-tars.py#L8)<br>[app-agent-element-identity](../topics/AppAgent探索与技能学习.md) → [element_identity()](../../examples/agents/app-agent.py#L5) | 为同一虚构界面分别记录截图身份、元素UID和动作文本，画模型/SDK/宿主/驱动边界。 | 过期或布局变化的观测不可直接复用；元素UID是结构启发式；解析成功不能当作动作已执行。 |
| 推导<br>`agents-derive` | [gui-agent-map-point](../topics/GUI定位与执行.md) → [map_point()](../../examples/agents/gui-agent.py#L5)<br>[mobile-agent-perception](../topics/MobileAgent多智能体协作.md) → [perception_index()](../../examples/agents/mobile-agent.py#L5)<br>[ui-tars-coordinate-path](../topics/UITARS感知与动作执行.md) → [grounding_coordinates()](../../examples/agents/ui-tars.py#L41) | 给裁剪、留白、文本框和显示缩放参数手算三套坐标路径，分别提交中间值。 | 区分展示点、截图像素、归一化框和执行器坐标；V1_0/V1_5分母不可混用；不声称检测到真实控件。 |
| 实践<br>`agents-derive`、`agents-build` | [mobile-agent-planning-memory](../topics/MobileAgent多智能体协作.md) → [planning_projection()](../../examples/agents/mobile-agent.py#L36)<br>[mobile-agent-reflection](../topics/MobileAgent多智能体协作.md) → [reflection_transition()](../../examples/agents/mobile-agent.py#L52)<br>[app-agent-document-learning](../topics/AppAgent探索与技能学习.md) → [learn_action_document()](../../examples/agents/app-agent.py#L25)<br>[app-agent-deployment](../topics/AppAgent探索与技能学习.md) → [deployment_context()](../../examples/agents/app-agent.py#L45) | 在独立状态表中演示v2规划/反思和AppAgent探索文档/部署选择，并设计恢复后重新观测。 | 进度、页面事实与操作历史分开；探索文档不等于权重更新；不得把两项目的状态和动作拼接使用。 |
| 评估<br>`agents-evaluate`、`benchmark-evaluate` | [gui-agent-verify-gui-action](../topics/GUI定位与执行.md) → [verify_gui_action()](../../examples/agents/gui-agent.py#L43)<br>[ui-tars-loop-state](../topics/UITARS感知与动作执行.md) → [agent_loop_transition()](../../examples/agents/ui-tars.py#L61)<br>[benchmark-agents-final-state](../topics/Agent任务基准与执行评估.md) → [state_acceptance()](../../examples/benchmark/benchmark-agents.py#L29)<br>[benchmark-robustness-utility-security-denominators](../topics/稳健性与工具安全评测.md) → [security_metrics()](../../examples/benchmark/benchmark-robustness.py#L4) | 设计定位正确但后置条件未知、驱动失败和部分条件满足三个反例；提交正常效用与受检副作用表。 | 坐标命中、下发成功、SDK停止和业务完成分别判定；条件满足2/3仍可整题失败；不以ASR补数代替安全效用。 |

## 专题分支与实现边界

方案边界：MobileAgent只采用已读Mobile-Agent-v2子目录；AppAgent采用TencentQQGYLab/AppAgent的元素文档路径；UI-TARS采用LocalComputer→SDK→NutJS的本地链，以V1_0为主。它们的模型、动作集合与坐标规则分别记录，不使用一个通用示例冒充三套真实执行。

| 方案与实现范围 | 已有知识点及函数 | 学习行动与验收 |
| --- | --- | --- |
| [MobileAgent多智能体协作](../topics/MobileAgent多智能体协作.md)<br>X-PLUG/MobileAgent的Mobile-Agent-v2；固定提交11cea575，不混入v3/E/PC等目录。 | [mobile-agent-perception](../topics/MobileAgent多智能体协作.md) → [perception_index()](../../examples/agents/mobile-agent.py#L5)<br>[mobile-agent-planning-memory](../topics/MobileAgent多智能体协作.md) → [planning_projection()](../../examples/agents/mobile-agent.py#L36)<br>[mobile-agent-reflection](../topics/MobileAgent多智能体协作.md) → [reflection_transition()](../../examples/agents/mobile-agent.py#L52) | 按框中心建立感知索引，分别推进规划事实与A/B/C反思状态。<br>验收：v2接受历史、回退后再观测与无效动作分别记录；几何框是给定输入，不是实机识别结果。 |
| [AppAgent探索与技能学习](../topics/AppAgent探索与技能学习.md)<br>TencentQQGYLab/AppAgent；固定提交2c190042，探索文档和当前UID检索路径。 | [app-agent-element-identity](../topics/AppAgent探索与技能学习.md) → [element_identity()](../../examples/agents/app-agent.py#L5)<br>[app-agent-document-learning](../topics/AppAgent探索与技能学习.md) → [learn_action_document()](../../examples/agents/app-agent.py#L25)<br>[app-agent-deployment](../topics/AppAgent探索与技能学习.md) → [deployment_context()](../../examples/agents/app-agent.py#L45) | 改变元素属性观察UID，更新动作文档槽位，再按当前界面选择文档与点位。<br>验收：外部知识积累不是微调；UID跨版本不保证稳定，部署FINISH仍需独立终态。 |
| [UITARS感知与动作执行](../topics/UITARS感知与动作执行.md)<br>UI-TARS-desktop提交3ac2cb8d：LocalComputer→SDK→NutJS，以V1_0分支为主。 | [ui-tars-action-protocol](../topics/UITARS感知与动作执行.md) → [parse_action()](../../examples/agents/ui-tars.py#L8)<br>[ui-tars-coordinate-path](../topics/UITARS感知与动作执行.md) → [grounding_coordinates()](../../examples/agents/ui-tars.py#L41)<br>[ui-tars-loop-state](../topics/UITARS感知与动作执行.md) → [agent_loop_transition()](../../examples/agents/ui-tars.py#L61) | 严格解析动作，区分归一化、屏幕点和显示缩放，再推演轮数预算。<br>验收：模型、SDK、桌面宿主、执行器各自负责的字段明确；V1_5另列，不拼坐标规则。 |

## 结业产物与复核

交付三套独立方案对照包，每套包含版本边界、几何输入、状态转移、动作意图、预期回读与终态判据；另外列出真实设备实验还缺的应用版本、截图、权限、驱动和独立验收证据。

复核者应能从能力ID、unit_id、主题版本、示例路径/函数、输入和预期重建推演。至少保留一个失败或未知样例，并说明源码已覆盖与教学省略的部分；任何实测结果都需另附原始记录，不能用预期值填写。

使用[学习记录模板](../../templates/学习记录模板.md)、[实验记录模板](../../templates/实验记录模板.md)和[评测协议模板](../../templates/评测协议模板.md)组织产物。可将本路径接入[三个跨模块实践项目](../../docs/跨模块实践项目.md)；真实剩余实验见[研究队列](../../docs/研究队列.md)。

下一步：[Agent开发路径](Agent开发路径.md)、[Benchmark学习路径](Benchmark学习路径.md)。
