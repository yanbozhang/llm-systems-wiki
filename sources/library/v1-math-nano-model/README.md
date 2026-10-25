# nanoGPT model.py

来源ID：`v1-math-nano-model`

[打开原始来源](<https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/model.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [前馈网络与归一化](../../../wiki/topics/前馈网络与归一化.md)
- [预训练目标与数据](../../../wiki/topics/预训练目标与数据.md)
- [Transformer与自回归生成](../../../wiki/topics/Transformer与自回归生成.md)

## 阅读与版本

- 实际登记的读取范围：实际读取第20–205、303–330行；LayerNorm、CausalSelfAttention、MLP、Block、GPT\.forward与generate
- 原生版本：`3adf61e154c3fe3fca428ad6bc3818b27a3b8291`
- 原登记指纹：`text-sha256:7c01703240dbec5d554527dc666e35b3df8391d0b117fddc07afcf325a21d11c`
- 定位：CausalSelfAttention\.forward; Block\.forward; GPT\.forward; GPT\.generate

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
