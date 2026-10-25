# NVIDIA/Megatron-LM：megatron/core/transformer/moe/moe_layer.py

来源ID：`2026-code-network-megatron`

[打开原始来源](<https://github.com/NVIDIA/Megatron-LM/blob/2052769557dcf7045c4091d1996f0bc59afeb80e/megatron/core/transformer/moe/moe_layer.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [MHA与MQA及GQA](../../../wiki/topics/MHA与MQA及GQA.md)
- [前馈网络与归一化](../../../wiki/topics/前馈网络与归一化.md)
- [位置编码与RoPE](../../../wiki/topics/位置编码与RoPE.md)
- [Transformer与自回归生成](../../../wiki/topics/Transformer与自回归生成.md)

## 阅读与版本

- 实际登记的读取范围：MoELayer初始化、router与dispatch组件，241行起；静态阅读，未运行完整框架
- 原生版本：`2052769557dcf7045c4091d1996f0bc59afeb80e`
- 原登记指纹：`text-sha256:95dc78afe985a752a9de32984e219fe5b718acc46ae7ea6ca5ca922e966a1896`
- 定位：MoELayer初始化、router与dispatch组件，241行起

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
