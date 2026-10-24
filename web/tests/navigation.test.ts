/** 契约：web/实现契约.md；API 边界补充见本轮验收点。 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { sitePath, resolveLink, normalize, searchTopics, readBookmarks, toggleBookmark, saveBookmarks, type SearchItem } from '../src/lib/navigation';

const routes: Record<string, string> = {
  'wiki/topics/注意力.md': '/read/attention/',
  'wiki/topics/缓存.md': '/llm-systems-wiki/read/cache/',
  'wiki/modules/推理.md': '/modules/inference/',
  'paths/入门.md': '/paths/start/',
  'docs/指南.md': '/guides/guide/',
};
function item(id: string, overrides: Partial<SearchItem> = {}): SearchItem {
  return { id, title: '主题', module: 'network', moduleTitle: '模型网络', moduleEnglish: 'Network',
    unitTitles: [], objectives: [], text: '', url: '/llm-systems-wiki/read/' + id + '/',
    description: '', ...overrides };
}
function ids(items: SearchItem[]): string[] { return items.map(value => value.id); }
function assertInert(value: string): void {
  assert.ok(value === '' || value.startsWith('#'), '危险或越界地址必须成为不可导航占位，实际：' + value);
}
function memoryStorage() {
  const values = new Map<string, string>();
  return { values, getItem(key: string) { return values.get(key) ?? null; },
    setItem(key: string, value: string) { values.set(key, value); } };
}

test("sitePath：空路径只添加一次前缀", () => {
  assert.equal(sitePath(""), "/llm-systems-wiki/");
});

test("sitePath：根路径只添加一次前缀", () => {
  assert.equal(sitePath("/"), "/llm-systems-wiki/");
});

test("sitePath：无前导斜线只添加一次前缀", () => {
  assert.equal(sitePath("read/cache/"), "/llm-systems-wiki/read/cache/");
});

test("sitePath：普通站内路由只添加一次前缀", () => {
  assert.equal(sitePath("/read/cache/"), "/llm-systems-wiki/read/cache/");
});

test("sitePath：已含前缀只添加一次前缀", () => {
  assert.equal(sitePath("/llm-systems-wiki/read/cache/"), "/llm-systems-wiki/read/cache/");
});

test("sitePath：前缀根只添加一次前缀", () => {
  assert.equal(sitePath("/llm-systems-wiki"), "/llm-systems-wiki");
});

test("sitePath：前缀根附锚点只添加一次前缀", () => {
  assert.equal(sitePath("/llm-systems-wiki#目录"), "/llm-systems-wiki#目录");
});

test("sitePath：前缀根附查询只添加一次前缀", () => {
  assert.equal(sitePath("/llm-systems-wiki?q=cache"), "/llm-systems-wiki?q=cache");
});

test("sitePath：相似但不同前缀只添加一次前缀", () => {
  assert.equal(sitePath("/llm-systems-wiki-tools/"), "/llm-systems-wiki/llm-systems-wiki-tools/");
});

test("sitePath：默认参数产生可打开的站点根路径", () => {
  assert.equal(sitePath(), '/llm-systems-wiki/');
});

test("resolveLink：当前目录Unicode", () => {
  assert.equal(resolveLink("./注意力.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/read/attention/");
});

test("resolveLink：百分号编码Unicode", () => {
  assert.equal(resolveLink("./%E6%B3%A8%E6%84%8F%E5%8A%9B.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/read/attention/");
});

test("resolveLink：父目录模块", () => {
  assert.equal(resolveLink("../modules/推理.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/modules/inference/");
});

test("resolveLink：学习路径", () => {
  assert.equal(resolveLink("../../paths/入门.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/paths/start/");
});

test("resolveLink：核心指南", () => {
  assert.equal(resolveLink("../../docs/指南.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/guides/guide/");
});

test("resolveLink：根目录相对路径", () => {
  assert.equal(resolveLink("/wiki/topics/注意力.md", "docs/指南.md", routes), "/llm-systems-wiki/read/attention/");
});

test("resolveLink：点路径归一", () => {
  assert.equal(resolveLink("./临时/../注意力.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/read/attention/");
});

test("resolveLink：已带站点前缀的映射", () => {
  assert.equal(resolveLink("./缓存.md", "wiki/topics/起点.md", routes), "/llm-systems-wiki/read/cache/");
});

test("resolveLink：查询与锚点后缀", () => {
  assert.equal(resolveLink("./注意力.md?view=full#多头注意力", "wiki/topics/起点.md", routes), "/llm-systems-wiki/read/attention/?view=full#多头注意力");
});

test("resolveLink：普通源码", () => {
  assert.equal(resolveLink("../../examples/cache.py#L12", "wiki/topics/起点.md", routes), "https://github.com/yanbozhang/llm-systems-wiki/blob/main/examples/cache.py#L12");
});

test("resolveLink：未知Markdown", () => {
  assert.equal(resolveLink("../../docs/draft.md", "wiki/topics/起点.md", routes), "https://github.com/yanbozhang/llm-systems-wiki/blob/main/docs/draft.md");
});

test("resolveLink：未知资源文件", () => {
  assert.equal(resolveLink("../../assets/diagram.svg", "wiki/topics/起点.md", routes), "https://github.com/yanbozhang/llm-systems-wiki/blob/main/assets/diagram.svg");
});

test("resolveLink：未知文件名与Object原型同名", () => {
  assert.equal(resolveLink("./constructor", "README.md", routes), "https://github.com/yanbozhang/llm-systems-wiki/blob/main/constructor");
});

test("resolveLink：未知Unicode和空格文件使用GitHub编码路径", () => {
  assert.equal(resolveLink('../../notes/学习 memo.md', 'wiki/topics/起点.md', routes), 'https://github.com/yanbozhang/llm-systems-wiki/blob/main/notes/%E5%AD%A6%E4%B9%A0%20memo.md');
});

test("resolveLink：保留#", () => {
  assert.equal(resolveLink("#", 'wiki/topics/起点.md', routes), "#");
});

test("resolveLink：保留#注意力", () => {
  assert.equal(resolveLink(" #注意力 ", 'wiki/topics/起点.md', routes), "#注意力");
});

test("resolveLink：保留https://example.org/paper?q=Cache#part", () => {
  assert.equal(resolveLink("https://example.org/paper?q=Cache#part", 'wiki/topics/起点.md', routes), "https://example.org/paper?q=Cache#part");
});

test("resolveLink：保留http://example.org/paper", () => {
  assert.equal(resolveLink("http://example.org/paper", 'wiki/topics/起点.md', routes), "http://example.org/paper");
});

test("resolveLink：保留mailto:reader@example.org", () => {
  assert.equal(resolveLink("mailto:reader@example.org", 'wiki/topics/起点.md', routes), "mailto:reader@example.org");
});

test("resolveLink：保留HTTPS://example.org/UPPER", () => {
  assert.equal(resolveLink("HTTPS://example.org/UPPER", 'wiki/topics/起点.md', routes), "HTTPS://example.org/UPPER");
});

test("resolveLink：JavaScript scheme返回不可导航占位", () => {
  assertInert(resolveLink("javascript:alert(1)", "README.md", routes));
});

test("resolveLink：混合大小写scheme返回不可导航占位", () => {
  assertInert(resolveLink(" JaVaScRiPt:alert(1) ", "README.md", routes));
});

test("resolveLink：Data HTML scheme返回不可导航占位", () => {
  assertInert(resolveLink("data:text/html,<script>alert(1)</script>", "README.md", routes));
});

test("resolveLink：VBScript scheme返回不可导航占位", () => {
  assertInert(resolveLink("vbscript:msgbox(1)", "README.md", routes));
});

test("resolveLink：控制字符混入scheme返回不可导航占位", () => {
  assertInert(resolveLink("java\tscript:alert(1)", "README.md", routes));
});

test("resolveLink：编码控制字符返回不可导航占位", () => {
  assertInert(resolveLink("docs/%00guide.md", "README.md", routes));
});

test("resolveLink：仓库根以上父目录返回不可导航占位", () => {
  assertInert(resolveLink("../outside.md", "README.md", routes));
});

test("resolveLink：深层路径越界返回不可导航占位", () => {
  assertInert(resolveLink("../../../outside.md", "wiki/topics/起点.md", routes));
});

test("resolveLink：编码父目录越界返回不可导航占位", () => {
  assertInert(resolveLink("%2e%2e/outside.md", "README.md", routes));
});

test("resolveLink：反斜线路径返回不可导航占位", () => {
  assertInert(resolveLink("..\\outside.md", "README.md", routes));
});

test("resolveLink：无效百分号编码返回不可导航占位", () => {
  assertInert(resolveLink("%E0%A4%A", "README.md", routes));
});

test("resolveLink：合法根边界仍可转换源码", () => {
  assert.equal(resolveLink('../../README.md', 'wiki/topics/起点.md', routes), 'https://github.com/yanbozhang/llm-systems-wiki/blob/main/README.md');
});

test("normalize：兼容字符大小写和首尾空白", () => {
  assert.equal(normalize(' \u3000ＡＴＴＥＮＴＩＯＮ KＶ \n'), 'attention kv');
});

test("normalize：中文保留且空白输入归空", () => {
  assert.equal(normalize('  注意力  '), '注意力'); assert.equal(normalize(' \t\n\u3000'), '');
});

test("searchTopics：空查询保持七模块源顺序", () => {
  const items = ['network', 'training', 'inference', 'harness', 'knowledge', 'agents', 'benchmark'].map((module, i) => item('topic-' + i, { module })); assert.deepEqual(searchTopics(items, ''), items);
});

test("searchTopics：空白查询和模块过滤组合", () => {
  const items = [item('a', {module:'training'}), item('b', {module:'inference'}), item('c', {module:'training'})]; assert.deepEqual(ids(searchTopics(items, ' \t\u3000', 'training')), ['a','c']);
});

test("searchTopics：未知模块和空数据均无结果", () => {
  assert.deepEqual(searchTopics([item('a')], '', 'unknown'), []); assert.deepEqual(searchTopics([], 'cache'), []);
});

test("searchTopics：未知关键词无结果", () => {
  assert.deepEqual(searchTopics([item('a', {title:'注意力',text:'缓存机制'})], 'not-present'), []);
});

test("searchTopics：数据和查询两侧NFKC大小写归一", () => {
  const items = [item('a', {title:'ＡＴＴＥＮＴＩＯＮ 注意力'}), item('b', {text:'attention'})]; assert.deepEqual(ids(searchTopics(items, 'ＡｔＴｅＮｔＩｏＮ')), ['a','b']);
});

test("searchTopics：每个词AND且可跨字段命中", () => {
  const items = [item('a',{title:'Attention',text:'缓存'}),item('b',{title:'Attention'}),item('c',{text:'缓存'})]; assert.deepEqual(ids(searchTopics(items, ' attention\t缓存 ')), ['a']);
});

test("searchTopics：模块和关键词同时限制结果", () => {
  const items = [item('a',{module:'inference',title:'KV cache'}),item('b',{module:'training',title:'KV cache'}),item('c',{module:'inference',title:'Prefill'})]; assert.deepEqual(ids(searchTopics(items, 'cache', 'inference')), ['a']);
});

test("searchTopics：覆盖主题标题", () => {
  assert.deepEqual(ids(searchTopics([item('a', {"title":"梯度累积"}), item('b')], "梯度")), ['a']);
});

test("searchTopics：覆盖知识点标题", () => {
  assert.deepEqual(ids(searchTopics([item('a', {"unitTitles":["分页缓存"]}), item('b')], "分页")), ['a']);
});

test("searchTopics：覆盖中文模块名", () => {
  assert.deepEqual(ids(searchTopics([item('a', {"moduleTitle":"推理加速"}), item('b')], "加速")), ['a']);
});

test("searchTopics：覆盖英文模块名", () => {
  assert.deepEqual(ids(searchTopics([item('a', {"moduleEnglish":"Inference"}), item('b')], "ＩＮＦＥＲＥＮＣＥ")), ['a']);
});

test("searchTopics：覆盖学习目标", () => {
  assert.deepEqual(ids(searchTopics([item('a', {"objectives":["理解重排算法"]}), item('b')], "重排")), ['a']);
});

test("searchTopics：覆盖正文", () => {
  assert.deepEqual(ids(searchTopics([item('a', {"text":"稀疏激活计算"}), item('b')], "稀疏")), ['a']);
});

test("searchTopics：标题知识点目标正文按相关性依次排序", () => {
  const items = [item('body',{text:'cache'}),item('objective',{objectives:['cache']}),item('unit',{unitTitles:['cache']}),item('heading',{title:'cache'})]; assert.deepEqual(ids(searchTopics(items, 'cache')), ['heading','unit','objective','body']);
});

test("searchTopics：同分保持非字母源顺序", () => {
  const items = [item('z',{title:'cache'}),item('a',{title:'cache'}),item('m',{title:'cache'})]; assert.deepEqual(ids(searchTopics(items, 'cache')), ['z','a','m']);
});

test("searchTopics：结果保留链接字段且不修改输入", () => {
  const items = [item('body',{text:'cache'}),item('heading',{title:'cache',url:'/llm-systems-wiki/read/heading/',description:'原描述'})]; const before = structuredClone(items); const result = searchTopics(items, 'cache'); assert.deepEqual(items,before); assert.deepEqual(result[0], before[1]); assert.equal(result[0].url, '/llm-systems-wiki/read/heading/');
});

test("readBookmarks：缺失键回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>null}), []);
});

test("readBookmarks：空内容回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>""}), []);
});

test("readBookmarks：损坏JSON回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"{bad"}), []);
});

test("readBookmarks：JSON null回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"null"}), []);
});

test("readBookmarks：对象回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"{\"a\":true}"}), []);
});

test("readBookmarks：字符串回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"\"cache\""}), []);
});

test("readBookmarks：数字回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"12"}), []);
});

test("readBookmarks：布尔回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"true"}), []);
});

test("readBookmarks：空数组回退空收藏", () => {
  assert.deepEqual(readBookmarks({getItem:()=>"[]"}), []);
});

test("readBookmarks：未提供存储时可继续阅读", () => {
  assert.deepEqual(readBookmarks(undefined), []);
});

test("readBookmarks：存储拒绝读取时回退空", () => {
  assert.deepEqual(readBookmarks({getItem(){ throw new Error('storage disabled'); }}), []);
});

test("readBookmarks：重复收藏保留首次顺序", () => {
  assert.deepEqual(readBookmarks({getItem:()=> '["cache","rag","cache"]'}), ['cache','rag']);
});

test("readBookmarks：无效数组成员不成为收藏ID", () => {
  assert.deepEqual(readBookmarks({getItem:()=> '["cache",null,5,"",{},"rag"]'}), ['cache','rag']);
});

test("toggleBookmark：添加后再次点击移除", () => {
  const original = ['rag']; const added = toggleBookmark(original, 'cache'); assert.deepEqual(added,['rag','cache']); assert.deepEqual(toggleBookmark(added,'cache'),['rag']); assert.deepEqual(original,['rag']);
});

test("toggleBookmark：重复点击旧收藏全部移除", () => {
  assert.deepEqual(toggleBookmark(['cache','rag','cache'],'cache'), ['rag']);
});

test("toggleBookmark：添加时全局去重", () => {
  assert.deepEqual(toggleBookmark(['rag','rag'],'cache'), ['rag','cache']);
});

test("toggleBookmark：移除时其余收藏也去重", () => {
  assert.deepEqual(toggleBookmark(['rag','rag','cache'],'cache'), ['rag']);
});

test("saveBookmarks：保存回读与清空跨调用一致", () => {
  const storage = memoryStorage(); assert.equal(saveBookmarks(storage,['cache','rag']),true); assert.deepEqual(readBookmarks(storage),['cache','rag']); assert.equal(saveBookmarks(storage,[]),true); assert.deepEqual(readBookmarks(storage),[]); assert.equal(storage.values.size,1);
});

test("saveBookmarks：缺少存储返回false", () => {
  assert.equal(saveBookmarks(undefined,['cache']),false);
});

test("saveBookmarks：写入失败返回false且保留已有状态", () => {
  const values = ['cache']; let calls = 0; const storage = {getItem:()=> '["rag"]',setItem(){calls++;throw new Error('quota exceeded');}}; assert.equal(saveBookmarks(storage,values),false); assert.equal(calls,1); assert.deepEqual(readBookmarks(storage),['rag']); assert.deepEqual(values,['cache']);
});

test("resolveLink：已登记assets按明确路由转站内", () => {
  const registered = { 'assets/diagram.svg': '/diagram.svg' }; assert.equal(resolveLink('../../assets/diagram.svg#结构', 'wiki/topics/当前.md', registered), '/llm-systems-wiki/diagram.svg#结构');
});

test("resolveLink：继承的字符串属性也不视为已登记路由", () => {
  const inherited = Object.create({ 'docs/inherited.md': '/guides/inherited/' }) as Record<string,string>; assert.equal(resolveLink('docs/inherited.md', 'README.md', inherited), 'https://github.com/yanbozhang/llm-systems-wiki/blob/main/docs/inherited.md');
});

test("resolveLink：自身非字符串值不产生异常或无效路由", () => {
  const malformed = { 'docs/bad.md': 42 } as unknown as Record<string,string>; assert.equal(resolveLink('docs/bad.md', 'README.md', malformed), 'https://github.com/yanbozhang/llm-systems-wiki/blob/main/docs/bad.md');
});
