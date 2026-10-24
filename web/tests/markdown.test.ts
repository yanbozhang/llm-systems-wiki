/** 来源：web/实现契约.md§阅读/数据和路由；不执行浏览器脚本。 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { unified } from 'unified';
import rehypeRaw from 'rehype-raw';
import { visit } from 'unist-util-visit';
import { toString as text } from 'hast-util-to-string';
import type { Element, Root } from 'hast';
import { renderMarkdown } from '../src/lib/markdown';

async function render(markdown: string, routes: Record<string,string> = {}) {
  const result = await renderMarkdown(markdown, 'wiki/topics/当前.md', routes);
  const tree = await unified().use(rehypeRaw).run({
    type: 'root', children: [{ type: 'raw', value: result.html }]
  } as Root) as Root;
  return { ...result, tree };
}
function nodes(tree: Root | Element, tag?: string): Element[] {
  const result: Element[] = [];
  visit(tree, 'element', (node: Element) => {
    if (!tag || node.tagName === tag) result.push(node);
  });
  return result;
}
function byClass(tree: Root | Element, name: string): Element[] {
  return nodes(tree).filter(node => Array.isArray(node.properties.className) && node.properties.className.includes(name));
}
function fence(language: string, source: string): string {
  return '\x60\x60\x60' + language + '\n' + source + '\n\x60\x60\x60';
}
function assertSafe(tree: Root): void {
  for (const node of nodes(tree)) {
    assert.ok(!['script','iframe','object','embed','style'].includes(node.tagName), '输出包含可执行元素：' + node.tagName);
    for (const [name, value] of Object.entries(node.properties)) {
      assert.ok(!/^on/i.test(name), '输出包含事件处理属性：' + name);
      if (['href','src','xLinkHref','formAction','action'].includes(name) && typeof value === 'string') {
        const protocol = new URL(value, 'https://example.org/').protocol;
        assert.ok(['https:','http:','mailto:'].includes(protocol), '输出包含危险URL：' + value);
      }
    }
  }
}

test("正文：空输入返回空内容和空目录", async () => {
  const result=await render(''); assert.equal(result.html,''); assert.deepEqual(result.headings,[]);
});

test("正文：frontmatter和重复一级标题隐藏", async () => {
  const result=await render('---\ntitle: 内部元信息标记\nstatus: draft\n---\n# 页面已有标题\n\n正文保留\n\n## 机制\n内容'); assert.doesNotMatch(result.html,/内部元信息标记|status: draft|页面已有标题/); assert.equal(nodes(result.tree,'h1').length,0); assert.match(text(result.tree),/正文保留/); assert.deepEqual(result.headings.map(h=>h.text),['机制']);
});

test("正文：CRLF元信息隐藏且正文保留", async () => {
  const result=await render('---\r\ntitle: CRLF元信息\r\n---\r\n# 标题\r\n\r\n段落'); assert.doesNotMatch(result.html,/CRLF元信息/); assert.equal(text(result.tree).trim(),'段落');
});

test("正文：仅有frontmatter且末尾无换行时不泄漏元信息", async () => {
  const result=await render('---\ntitle: 仅元信息\n---'); assert.doesNotMatch(result.html,/仅元信息|title:/); assert.equal(text(result.tree).trim(),'');
});

test("正文：GFM表格保留表头和单元格", async () => {
  const result=await render('| 模型 | 参数 |\n| --- | ---: |\n| 小模型 | 7B |\n| 大模型 | 70B |'); assert.equal(nodes(result.tree,'table').length,1); assert.deepEqual(nodes(result.tree,'th').map(text),['模型','参数']); assert.deepEqual(nodes(result.tree,'td').map(text),['小模型','7B','大模型','70B']);
});

test("目录：二三级标题保持正文顺序与层级", async () => {
  const result=await render('# 文章\n\n## 机制\n内容\n\n### 推导\n证明\n\n## 实验\n记录'); assert.deepEqual(result.headings.map(({text,level})=>({text,level})),[{text:'机制',level:2},{text:'推导',level:3},{text:'实验',level:2}]); const headings=nodes(result.tree).filter(e=>e.tagName==='h2'||e.tagName==='h3'); assert.deepEqual(headings.map(e=>e.properties.id),result.headings.map(h=>h.id));
});

test("目录：相同标题及预占后缀生成全局唯一ID", async () => {
  const result=await render('## Attention\n\n### Attention\n\n## Attention-1\n\n## Attention'); const ids=result.headings.map(h=>h.id); assert.equal(ids.length,4); assert.equal(new Set(ids).size,4); assert.deepEqual(nodes(result.tree).filter(e=>/^h[23]$/.test(e.tagName)).map(e=>e.properties.id),ids);
});

test("目录：富文本标题提取文字且锚点指向真实标题", async () => {
  const result=await render('## **KV** 与 `QK`\n\n## Attention\n\n[跳转](#attention)'); assert.equal(result.headings[0].text,'KV 与 QK'); const href=nodes(result.tree,'a')[0].properties.href; assert.equal(href,'#attention'); assert.ok(result.headings.some(h=>'#'+h.id===href));
});

test("目录：不同文档之间不共享slug编号", async () => {
  const first=await render('## Cache\n\n## Cache'); const second=await render('## Cache'); assert.equal(second.headings[0].id,first.headings[0].id); assert.equal(second.headings.length,1);
});

test("代码：Python语法高亮且原代码完整", async () => {
  const code='def square(x):\n    return x ** 2'; const result=await render(fence('python',code)); const pre=nodes(result.tree,'pre')[0]; assert.ok(pre); assert.equal(text(pre).trimEnd(),code); const styled=nodes(pre,'span').filter(e=>typeof e.properties.style==='string'); assert.ok(styled.length>=2,'关键词与普通代码应形成着色token'); assert.ok(new Set(styled.map(e=>e.properties.style)).size>=2,'不同token应有区分性的高亮');
});

test("代码：未知语言仍保留文本并转义HTML", async () => {
  const code='<img src=x onerror=alert(1)>'; const result=await render(fence('unknown-language',code)); assert.equal(text(nodes(result.tree,'pre')[0]).trimEnd(),code); assert.equal(nodes(result.tree,'img').length,0); assertSafe(result.tree);
});

test("代码：行内危险HTML只能显示为文本", async () => {
  const snippet='<script>alert(1)</script>'; const result=await render('`'+snippet+'`'); assert.equal(text(nodes(result.tree,'code')[0]),snippet); assertSafe(result.tree);
});

test("代码：HTML代码块不会变成可执行DOM", async () => {
  const code='<script>alert(1)</script>\n<img src=x onerror="alert(2)">'; const result=await render(fence('html',code)); assert.equal(text(nodes(result.tree,'pre')[0]).trimEnd(),code); assert.equal(nodes(result.tree,'img').length,0); assertSafe(result.tree);
});

test("数学：行内表达式渲染KaTeX及幂运算MathML", async () => {
  const result=await render('损失为 $x^2$。'); assert.ok(byClass(result.tree,'katex').length>=1); assert.ok(nodes(result.tree,'math').length>=1); assert.ok(nodes(result.tree,'msup').length>=1); assert.equal(byClass(result.tree,'katex-display').length,0); assert.match(text(result.tree),/损失为/);
});

test("数学：独立公式渲染KaTeX展示块而非代码高亮", async () => {
  const result=await render('$$\n\\frac{1}{2} + x^2\n$$'); assert.equal(byClass(result.tree,'katex-display').length,1,'展示数学容器丢失，实际HTML：'+result.html); assert.ok(nodes(result.tree,'mfrac').length>=1); assert.equal(nodes(result.tree,'pre').length,0); assert.equal(byClass(result.tree,'code-block').length,0);
});

test("数学：表格和普通段落中同时支持行内公式", async () => {
  const result=await render('设 $x=1$。\n\n| 符号 | 公式 |\n| --- | --- |\n| y | $x^2$ |'); assert.equal(nodes(result.tree,'table').length,1); assert.equal(nodes(result.tree,'math').length,2);
});

test("数学：公式里的危险href不能绕过清洗", async () => {
  const result=await render('$\\href{javascript:alert(1)}{x}$'); assertSafe(result.tree); assert.ok(byClass(result.tree,'katex').length>=1);
});

test("Mermaid：保留独立渲染标记和原始图源码", async () => {
  const diagram='graph TD\n  A["输入"] --> B["输出"]'; const result=await render(fence('mermaid',diagram)); const pre=nodes(result.tree,'pre')[0]; assert.ok(pre); assert.equal(text(pre).trimEnd(),diagram); assert.ok(byClass(pre,'language-mermaid').length>0 || byClass(pre,'mermaid-source').length>0 || pre.properties.dataDiagram!==undefined); assert.equal(byClass(result.tree,'shiki').length,0);
});

test("Mermaid：源码中的HTML结束标签保持为文本", async () => {
  const diagram='graph TD\n A["</pre><script>alert(1)</script>"] --> B'; const result=await render(fence('mermaid',diagram)); assert.equal(text(nodes(result.tree,'pre')[0]).trimEnd(),diagram); assertSafe(result.tree);
});

test("链接：相对Unicode文章路径保留锚点并站内转换", async () => {
  const result=await render('[注意力](./注意力.md#原理)',{'wiki/topics/注意力.md':'/read/attention/'}); assert.equal(new URL(String(nodes(result.tree,'a')[0].properties.href),'https://example.org/').href,new URL('/llm-systems-wiki/read/attention/#原理','https://example.org/').href);
});

test("链接：普通仓库文件使用GitHub源码路径", async () => {
  const result=await render('[源码](../../examples/cache.py#L5)'); assert.equal(nodes(result.tree,'a')[0].properties.href,'https://github.com/yanbozhang/llm-systems-wiki/blob/main/examples/cache.py#L5');
});

test("链接：外部网址邮件及文章锚点保持", async () => {
  const result=await render('[论文](https://example.org/paper) [邮件](mailto:reader@example.org) [章节](#缓存)'); assert.deepEqual(nodes(result.tree,'a').map(e=>new URL(String(e.properties.href),'https://example.org/').href),['https://example.org/paper','mailto:reader@example.org','#缓存'].map(href=>new URL(href,'https://example.org/').href));
});

test("链接：图片相对路径也经过安全路径转换", async () => {
  const result=await render('![流程](../../docs/diagram.png)'); const img=nodes(result.tree,'img')[0]; assert.equal(img.properties.src,'https://github.com/yanbozhang/llm-systems-wiki/blob/main/docs/diagram.png'); assert.equal(img.properties.alt,'流程');
});

test("清洗：原始script iframe object和事件属性不保留", async () => {
  const source='<script>alert(1)</script>\n<iframe src="https://example.org"></iframe>\n<object data="data:text/html,evil"></object>\n<img src="https://example.org/x.png" onerror="alert(2)">\n<p onclick="alert(3)">安全文本</p>'; const result=await render(source); assertSafe(result.tree); assert.match(text(result.tree),/安全文本/);
});

test("清洗：原始及Markdown可执行URL不进入输出链接", async () => {
  const source='<a href="javascript:alert(1)">原始</a>\n<a href="jav&#x61;script:alert(2)">实体编码</a>\n<a href="data:text/html,evil">data</a>\n\n[Markdown](javascript:alert%281%29)\n\n![图片](data:image/svg+xml;base64,PHN2Zz4=)'; const result=await render(source); assertSafe(result.tree); assert.match(text(result.tree),/原始/);
});

test("清洗：借用高亮器class的原始HTML仍受清洗", async () => {
  const source='<div class="code-block"><pre class="shiki github-light github-dark"><code class="language-html"><script>alert(1)</script><img src=x onerror="alert(2)"><a href="javascript:alert(3)">原文</a></code></pre></div>'; const result=await render(source); assertSafe(result.tree); assert.doesNotMatch(result.html,/onerror\s*=/i); assert.match(text(result.tree),/原文/);
});

test("清洗：借用数学class不能生成可执行链接", async () => {
  const source='<code class="language-math math-inline">\\href{javascript:alert(1)}{点击}</code><p onmouseover="alert(2)">正文</p>'; const result=await render(source); assertSafe(result.tree); assert.match(text(result.tree),/正文/);
});

test("清洗：转义文本与安全强调均保留", async () => {
  const result=await render('&lt;script&gt;示例&lt;/script&gt;\n\n**重点** 与普通段落'); assertSafe(result.tree); assert.match(text(result.tree),/<script>示例<\/script>/); assert.equal(text(nodes(result.tree,'strong')[0]),'重点');
});
