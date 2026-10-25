# Transformers RoPE 参数实现

来源ID：`v1-math-rope-utils`

[打开原始来源](<https://github.com/huggingface/transformers/blob/50e35cc0ca18ec19b80653690de553e6decf74f5/src/transformers/modeling_rope_utils.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [位置编码与RoPE](../../../wiki/topics/位置编码与RoPE.md)

## 阅读与版本

- 实际登记的读取范围：第133–190行的线性缩放函数，包括频率计算与factor处理
- 原生版本：`50e35cc0ca18ec19b80653690de553e6decf74f5`
- 原登记指纹：`text-sha256:8b08f3f372207816eae420e7d33b982e44858dc9e4be7728d95f606b07c23fd0`
- 定位：\_compute\_linear\_scaling\_rope\_parameters

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
