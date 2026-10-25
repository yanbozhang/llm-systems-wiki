# vllm/v1/core/sched/scheduler.py

来源ID：`v1-systems-scheduler`

[打开原始来源](<https://github.com/vllm-project/vllm/blob/7a64fb8fc9239cb65e0df9313fa759594dfb206a/vllm/v1/core/sched/scheduler.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [缓存分页与连续批处理](../../../wiki/topics/缓存分页与连续批处理.md)
- [Prefill与Decode](../../../wiki/topics/Prefill与Decode.md)

## 阅读与版本

- 实际登记的读取范围：schedule 677–705、785–834、875–955；\_preempt\_request 1744–1780
- 原生版本：`7a64fb8fc9239cb65e0df9313fa759594dfb206a`
- 原登记指纹：`text-sha256:2aab08cb511d5905c280697fcc47fffa60804759d6fba22496779892c290b41b`
- 定位：Scheduler\.schedule；Scheduler\.\_preempt\_request

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
