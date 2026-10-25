# sgl-project/sglang：python/sglang/srt/mem_cache/radix_cache.py

来源ID：`2026-code-inference-sglang`

[打开原始来源](<https://github.com/sgl-project/sglang/blob/d558ac2f3e7a59a876bbce4687fa49334de777fa/python/sglang/srt/mem_cache/radix_cache.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [缓存分页与连续批处理](../../../wiki/topics/缓存分页与连续批处理.md)
- [推理框架与性能实验](../../../wiki/topics/推理框架与性能实验.md)
- [KV缓存原理与显存估算](../../../wiki/topics/KV缓存原理与显存估算.md)
- [Prefill与Decode](../../../wiki/topics/Prefill与Decode.md)

## 阅读与版本

- 实际登记的读取范围：RadixCache\.evict、inc\_lock\_ref、dec\_lock\_ref，552行起；静态阅读，未运行完整框架
- 原生版本：`d558ac2f3e7a59a876bbce4687fa49334de777fa`
- 原登记指纹：`text-sha256:61d55b14e7d229049685ab27a8bf5dcc0b28fb25a134778c99784682011cafcf`
- 定位：RadixCache\.evict、inc\_lock\_ref、dec\_lock\_ref，552行起

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)

## 可随仓库读取的上游快照

[源码或文档快照](snapshot/source.txt) · [上游许可证](snapshot/LICENSE)

本快照保留上游Apache-2.0许可与文件内声明，未将第三方材料改为本库许可。
