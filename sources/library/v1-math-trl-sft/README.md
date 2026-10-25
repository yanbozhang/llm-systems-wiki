# TRL SFTTrainer 与文本collator

来源ID：`v1-math-trl-sft`

[打开原始来源](<https://github.com/huggingface/trl/blob/1117c3b9c1632ee9814c30f6c9fc884b792a54e5/trl/trainer/sft_trainer.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [监督微调与LoRA](../../../wiki/topics/监督微调与LoRA.md)

## 阅读与版本

- 实际登记的读取范围：第170–229、1362–1482、1546–1565行；模板分词、mask交集生成labels、padding与跳过准备保护
- 原生版本：`1117c3b9c1632ee9814c30f6c9fc884b792a54e5`
- 原登记指纹：`text-sha256:ab992191b84cdc47e14c0b6baf4e6be724240da4b4d98f26341cdaba072e8e92`
- 定位：SFTTrainer\.\_prepare\_dataset\.build\_labels; DataCollatorForLanguageModeling\.torch\_call

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
