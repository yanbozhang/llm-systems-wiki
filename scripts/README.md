# 维护工具

普通读者不必运行这些工具，直接读[主题](../wiki/README.md)即可。

| 工具 | 作用 |
|---|---|
| wiki_tool.py | 检查知识清单、生成学习计划、收集订阅候选 |
| learning_check.py | 检查知识点的公式、代码、结构图和来源绑定 |
| source_library.py | 为每条来源生成目录，下载本地原文并验证归档记录 |

在仓库根目录运行：

```bash
python scripts/wiki_tool.py check --curriculum
python scripts/learning_check.py
python scripts/source_library.py index
python scripts/source_library.py capture --workers 2
python scripts/source_library.py check
```

来源抓取需要访问公开网络；其余检查可以离线执行。`source_library.py check --local`另外核验本机原文件，适用于下载后检查，不适用于未下载缓存的新克隆。保存原文与阅读、核验、复现实验是不同步骤。
