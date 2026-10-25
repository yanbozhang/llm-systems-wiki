# Codex 进程执行与输出回收

来源ID：`v1-harnesscase-cx-exec-process`

[打开原始来源](<https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/codex-rs/core/src/exec.rs#L982>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [CodexCLI架构与执行](../../../wiki/topics/CodexCLI架构与执行.md)

## 阅读与版本

- 实际登记的读取范围：ExecExpiration 150–200；ExecCapturePolicy 274–291；process\_exec\_tool\_call 302–336；consume\_output 982–1191；read\_output 1194–1247
- 原生版本：`970111f6cb62cc02fe36a82ea7d71b37a2889c97`
- 原登记指纹：`text-sha256:83f72b788b041e2865ebd5b10ce6878b4a471ea4082116c821d87ef39b710888`
- 定位：ExecExpiration 150–200；ExecCapturePolicy 274–291；process\_exec\_tool\_call 302–336；consume\_output 982–1191；read\_output 1194–1247

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
