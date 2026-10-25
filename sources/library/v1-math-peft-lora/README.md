# PEFT LoRA 层实现

来源ID：`v1-math-peft-lora`

[打开原始来源](<https://github.com/huggingface/peft/blob/7d6315ae910bf62b6044a7ca917bccf5881f5e43/src/peft/tuners/lora/layer.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [监督微调与LoRA](../../../wiki/topics/监督微调与LoRA.md)

## 阅读与版本

- 实际登记的读取范围：第219–283、359–372、1046–1109、1138–1209行；参数、缩放、初始化、merge、get\_delta\_weight与forward
- 原生版本：`7d6315ae910bf62b6044a7ca917bccf5881f5e43`
- 原登记指纹：`text-sha256:7f0952efd6df729e060055566cef17a3fff6876a3b4dc4a4502b8d9e31349ffa`
- 定位：LoraLayer\.update\_layer; reset\_lora\_parameters; Linear\.merge; Linear\.get\_delta\_weight; Linear\.forward

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
