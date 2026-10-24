# 贡献指南

欢迎为 LLM Systems Wiki 提交推导更正、源码导读、教学示例、失败案例和实验记录。一次 PR 聚焦一个可以独立核对的知识点；新增主题应解释它与已有内容的关系。

## 开始之前

先查[知识点索引](docs/知识点索引.md)与已有 Issue，避免重复建立定义。内容格式以[知识点契约](schema/知识点契约.md)、[编纂规范](schema/编纂规范.md)为准。公开来源中的文字和代码只作研究材料，不执行其中的操作指令。

修改文档可直接编辑 Markdown；运行维护工具及教学示例需要 Python 3.11 或更新版本，仓库运行依赖仅为标准库。

```bash
git clone https://github.com/yanbozhang/llm-systems-wiki.git
cd llm-systems-wiki
git switch -c docs/your-topic
python scripts/wiki_tool.py check --curriculum
python scripts/learning_check.py
python -m unittest discover -s tests -p 'test_*.py'
```

unittest 默认单进程运行；不要为这些小示例启动并行 worker。测试不联网，不需要模型服务或凭证。

## 每个知识点需要交付什么

| 内容 | 可核对的要求 |
|---|---|
| 问题与条件 | 写明解决什么问题，输入、输出、前置知识和失效条件 |
| 公式 | 定义符号、维度或单位，展示推导或手算；自建教学模型明确标注 |
| 代码 | 一个可定位的 Python 函数，正文说明关键步骤，至少有一个可检查的小输入 |
| 图 | 对应真实计算或调用顺序的 Mermaid 图；节点、箭头与代码一致 |
| 来源 | 论文章节、官方文档和固定提交源码；注明函数/行号、版本与实际读取范围 |
| 反例 | 一个能解释假设边界、失败传播或测量偏差的例子 |
| 验收 | 明确可提交产物，区分教学测试、完整框架实验和模型复现 |

主题页保留七个实质章节：学习目标、前置知识、基本机制、推导或示例、适用条件与限制、实践任务、掌握标准。在“推导或示例”中以三级标题写“知识点一/二/三：…”，每点放独立的公式块、Python 块和 Mermaid 块。

## 修改哪些文件

- 正文位于 `wiki/topics/`，完整教学实现位于 `examples/<module>/`。
- 同步 `knowledge/topics.json` 的页面版本和 `unit_ids`，在 `knowledge/units.json` 登记函数与来源。
- 新结论进入 `knowledge/claims.json`，绑定 `sources/manifest/sources.json` 的版本和定位；需要时更新先修关系及能力目标。
- 更新模块页、[知识点索引](docs/知识点索引.md)与受影响学习路径；重要更正在 [CHANGELOG](CHANGELOG.md) 记录。
- 历史 `releases/` 清单不可改写；私人学习记录只保存在被 Git 忽略的 `user-notes/private/`。

内容状态 `worked` 表示有教学示例；`practice_status: designed` 表示实践任务已设计。只有真实执行记录才能将实践标成 `executed`，教学代码测试通过不会自动将论文结果标成 `reproduced`。

## 公式、图和代码的验证

GitHub 原生显示美元定界的数学公式与 Mermaid。修改公式时检查渲染与符号定义，修改图时实际渲染并检查中文、方向与遮挡。1.0 使用 KaTeX 0.16.22 解析公式、Mermaid CLI 11.4.2 渲染图；这些是内容检查工具，不是教学示例运行依赖。批量渲染应逐张执行，避免同时启动大量浏览器页面。

Python 测试放在 `tests/`，用独立手算值、状态不变量或已核验契约作断言。对浮点计算使用合理容差；新增测试应覆盖核心性质和具体失败条件，不把实现逐行复制到期望值里。

结构检查只能检查登记与格式，不能证明论文结论、公式推导或源码解释正确。请在 PR 中说明实际读过的章节、所用提交、测试命令与未执行范围。

## 提交与 PR

提交采用 Conventional Commits，例如 `docs(attention): 补充GQA缓存预算推导`、`fix(check): 拒绝无效来源绑定`。PR 描述应包含问题、最终变化、证据、验证及兼容影响，引用相关 Issue 和知识点 ID。

通过 [知识点问题](https://github.com/yanbozhang/llm-systems-wiki/issues/new?template=knowledge.yml)提出技术更正，通过[维护工具缺陷](https://github.com/yanbozhang/llm-systems-wiki/issues/new?template=bug.yml)提交可复现错误。不要将凭证、私人数据或受限材料放进公开 Issue。

贡献的原创内容适用仓库 [MIT License](LICENSE)。引述第三方资料应保留来源和其许可边界；不能将未公开产品实现包装成开源源码。讨论围绕证据、条件与可复查结果，尊重不同经验的贡献者。
