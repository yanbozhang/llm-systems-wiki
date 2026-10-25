# python/sglang/srt/mem_cache/radix_cache.py

来源ID：`v1-systems-radix`

[打开原始来源](<https://github.com/sgl-project/sglang/blob/3ea7e210d28e26a13590d3244cedfe17f8c3e58c/python/sglang/srt/mem_cache/radix_cache.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [缓存分页与连续批处理](../../../wiki/topics/缓存分页与连续批处理.md)

## 阅读与版本

- 实际登记的读取范围：RadixKey\.match\_at 178–220；TreeNode 250–275；evict/inc\_lock\_ref/dec\_lock\_ref 552–617；\_match\_prefix\_helper/\_split\_node 651–701
- 原生版本：`3ea7e210d28e26a13590d3244cedfe17f8c3e58c`
- 原登记指纹：`text-sha256:eea7015fcf678167ac7296b08c8dc568ccbe42a4bb106da23b33a7c59debec01`
- 定位：RadixKey\.match\_at；RadixCache\.\_split\_node；RadixCache\.evict

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
