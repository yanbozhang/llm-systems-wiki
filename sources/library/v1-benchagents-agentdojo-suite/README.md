# AgentDojo 任务执行、效用与安全目标检查

来源ID：`v1-benchagents-agentdojo-suite`

[打开原始来源](<https://github.com/ethz-spylab/agentdojo/blob/089ed468cf3ed0322acc66b0211f26d9d90dbf60/src/agentdojo/task_suite/task_suite.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [稳健性与工具安全评测](../../../wiki/topics/稳健性与工具安全评测.md)

## 阅读与版本

- 实际登记的读取范围：validate\_injections 94–98；环境构建139–146；结果判据281–337；run\_task\_with\_pipeline 339–420；check 422–479；is\_task\_injectable 482–491
- 原生版本：`089ed468cf3ed0322acc66b0211f26d9d90dbf60`
- 原登记指纹：`text-sha256:2e69da06f7e150dd6d238c53a74845b56eebeb224e07f694e1051a6e0c6a2bc1`
- 定位：src/agentdojo/task\_suite/task\_suite\.py::run\_task\_with\_pipeline、\_check\_task\_result、check、is\_task\_injectable

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
