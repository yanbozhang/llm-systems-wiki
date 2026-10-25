# docs/design/prefix_caching.md

来源ID：`v1-systems-prefix-doc`

[打开原始来源](<https://github.com/vllm-project/vllm/blob/7a64fb8fc9239cb65e0df9313fa759594dfb206a/docs/design/prefix_caching.md>) · [原始登记信息](source.json) · [保存记录](archive.json)

## 这份资料用在哪里

- [缓存分页与连续批处理](../../../wiki/topics/缓存分页与连续批处理.md)
- [KV缓存原理与显存估算](../../../wiki/topics/KV缓存原理与显存估算.md)

## 阅读与版本

- 实际登记的读取范围：Automatic Prefix Caching 1–185行，哈希身份、数据结构与分配步骤
- 原生版本：`7a64fb8fc9239cb65e0df9313fa759594dfb206a`
- 原登记指纹：`text-sha256:67ee4e2b7bc23d40e9b366e4a9053ae4ecd0925ddef51f412ac5c16b9dc83a61`
- 定位：Data Structure；Block Allocation

## 本地资料

已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存。

原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。

第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。

[返回来源资料库](../../README.md)
