# TRL DPOTrainer 实现

来源ID：`v1-math-trl-dpo`

[打开原始来源](<https://github.com/huggingface/trl/blob/1117c3b9c1632ee9814c30f6c9fc884b792a54e5/trl/trainer/dpo_trainer.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [偏好学习与DPO](../../../wiki/topics/偏好学习与DPO.md)

## 阅读与版本

- 实际登记的读取范围：第1295–1447、1556–1575行；参考策略、completion mask、logp求和、reverse\_kl、sigmoid及sigmoid\_norm
- 原生版本：`1117c3b9c1632ee9814c30f6c9fc884b792a54e5`
- 原登记指纹：`text-sha256:148ae182814e8983409209bf3898397923cbdb67d4a195f2af3af36f895f9f4f`
- 定位：DPOTrainer\.compute\_ref\_log\_probs; DPOTrainer\.\_compute\_loss

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
