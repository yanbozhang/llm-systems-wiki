# 教学代码

这里的45份Python示例对应基础主题中的135个知识点，只依赖Python 3.11及以上版本的标准库。每个函数用于解释一个数学关系、状态转移或边界条件，不需要GPU、模型权重或API Key。

先通过[知识点索引](../docs/知识点索引.md)找到文章，再阅读其输入、符号和适用条件。例如，缓存估算见[inference/kv-cache.py](inference/kv-cache.py)，检查点教学见[harness/langgraph.py](harness/langgraph.py)。

```bash
python examples/inference/kv-cache.py
python examples/harness/langgraph.py
```

目录与七个知识模块同名：network、training、inference、harness、knowledge、agents、benchmark。新论文中的完整实验与上游框架需另行安装和固定版本，不要把本目录的小输入计算当成真实模型跑分。

[阅读基础知识](../wiki/README.md) · [查看来源代码和论文](../sources/README.md)
