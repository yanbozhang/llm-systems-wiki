# FastChat 成对裁判调用、顺序交换与结果加载

来源ID：`v1-benchagents-fastchat-judge`

[打开原始来源](<https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge/common.py>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [模型裁判与人工校准](../../../wiki/topics/模型裁判与人工校准.md)

## 阅读与版本

- 实际登记的读取范围：run\_judge\_single 135–189；run\_judge\_pair 235–310；play\_a\_match\_pair 313–404；normalize\_game\_key\_single 522–534；load\_pairwise\_model\_judgments 546–586
- 原生版本：`587d5cfa1609a43d192cedb8441cac3c17db105d`
- 原登记指纹：`text-sha256:71c3b317322845cb05eb6d9b555b03e5084fa59085d24989ce521fcfa8bdc9a7`
- 定位：fastchat/llm\_judge/common\.py::run\_judge\_pair、play\_a\_match\_pair、load\_pairwise\_model\_judgments

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
