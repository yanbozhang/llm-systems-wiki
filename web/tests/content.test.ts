/** 契约：实现契约、网站开发说明；仓库清单只读，合成文件仅写临时目录。 */
import test from 'node:test';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, join, posix } from 'node:path';
import { fileURLToPath } from 'node:url';
import { modules, topics, units, paths, guides, routes, frontiers, sourceCards, readDocument, topicDescription, buildSearchIndex, type Topic, type Unit } from '../src/lib/content';
import { resolveLink, type SearchItem } from '../src/lib/navigation';
import { GET } from '../src/pages/search-index.json.js';

const repo=fileURLToPath(new URL('../../',import.meta.url));
const manifestPaths=['knowledge/modules.json','knowledge/topics.json','knowledge/units.json'];
const rawModules=JSON.parse(readFileSync(resolve(repo,manifestPaths[0]),'utf8')) as {id:string;title:string;page:string}[];
const rawTopics=JSON.parse(readFileSync(resolve(repo,manifestPaths[1]),'utf8')) as Topic[];
const rawUnits=JSON.parse(readFileSync(resolve(repo,manifestPaths[2]),'utf8')) as Unit[];
function withDocument(source: string, assertion: (path:string)=>void): void {
  const directory=mkdtempSync(join(tmpdir(),'llmwiki-content-'));
  try { const path=join(directory,'document.md'); writeFileSync(path,source,'utf8'); assertion(path); }
  finally { rmSync(directory,{recursive:true,force:true}); }
}

test("清单：七模块保留权威数据且生成稳定路由", async () => {
  assert.equal(modules.length,7); assert.deepEqual(modules.map(m=>m.id),rawModules.map(m=>m.id)); for (const expected of rawModules) { const actual=modules.find(m=>m.id===expected.id)!; assert.ok(actual); assert.equal(actual.title,expected.title); assert.equal(actual.page,expected.page); assert.equal(routes[expected.page],'/modules/'+expected.id+'/'); }
});

test("清单：45主题保留示例学习目标和全部源字段", async () => {
  assert.equal(topics.length,45); assert.deepEqual(topics,rawTopics); for(const topic of rawTopics){ assert.ok(topic.example); assert.ok(existsSync(resolve(repo,topic.example))); assert.ok(topic.learning_objectives.length>0); assert.equal(routes[topic.page],'/read/'+topic.id+'/'); }
});

test("清单：135知识点完整并能沿父主题路由访问", async () => {
  assert.equal(units.length,135); assert.deepEqual(units,rawUnits); assert.equal(new Set(units.map(u=>u.id)).size,135); for(const unit of units){ const topic=rawTopics.find(t=>t.id===unit.topic); assert.ok(topic); assert.ok(topic.unit_ids.includes(unit.id)); assert.equal(routes[topic.page],'/read/'+topic.id+'/'); }
});

test("学习路径：覆盖全部六份真实路径文档且路由唯一", async () => {
  const pages=readdirSync(resolve(repo,'wiki/paths')).filter(name=>name.endsWith('.md')).map(name=>'wiki/paths/'+name).sort(); assert.equal(paths.length,6); assert.deepEqual(paths.map(p=>p.page).sort(),pages); assert.equal(new Set(paths.map(p=>p.id)).size,6); assert.equal(new Set(paths.map(p=>p.url)).size,6); for(const path of paths){ assert.match(path.url,/^\/paths\/[^/]+\/$/); assert.equal(routes[path.page],path.url); assert.ok(readDocument(path.page).length>0); }
});

test("指南：每个已声明指南均有真实正文和独立路由", async () => {
  assert.ok(guides.length>0); assert.equal(new Set(guides.map(g=>g.page)).size,guides.length); for(const guide of guides){ assert.ok(existsSync(resolve(repo,guide.page))); assert.match(guide.url,/^\/guides\/[^/]+\/$/); assert.equal(routes[guide.page],guide.url); assert.ok(readDocument(guide.page).length>0); }
});

test("资源：真实assets文件全部显式登记且未知资源不伪登记", async () => {
  const names=readdirSync(resolve(repo,'assets'),{withFileTypes:true}).filter(entry=>entry.isFile()).map(entry=>entry.name); assert.ok(names.length>0); for(const name of names){ assert.ok(Object.hasOwn(routes,'assets/'+name)); assert.equal(routes['assets/'+name],'/'+name); } assert.equal(Object.hasOwn(routes,'assets/not-a-real-fixture.svg'),false);
});

test("正文：从真实主题剥离元信息并保留文章标题和公式代码", async () => {
  const source=readFileSync(resolve(repo,rawTopics[0].page),'utf8'); const heading=source.match(/^# .+$/m)![0]; const body=readDocument(rawTopics[0].page); assert.ok(body.includes(heading)); assert.ok(body.includes('$$'),'正文公式应保留'); assert.ok(body.includes('```python'),'正文教学代码应保留'); assert.doesNotMatch(body,/^---\r?\n/); assert.doesNotMatch(body,/\[返回模块\]|觉得这篇推导有帮助/);
});

test("正文：LF元信息", async () => {
  withDocument("---\ntitle: 秘密元数据\n---\n# 正文\n\n保留段落", path=>assert.equal(readDocument(path),"# 正文\n\n保留段落"));
});

test("正文：CRLF元信息", async () => {
  withDocument("---\r\ntitle: 秘密元数据\r\n---\r\n# 正文\r\n\r\n保留段落", path=>assert.equal(readDocument(path),"# 正文\r\n\r\n保留段落"));
});

test("正文：EOF元信息", async () => {
  withDocument("---\ntitle: 秘密元数据\n---", path=>assert.equal(readDocument(path),""));
});

test("正文：LF旧推广尾段", async () => {
  withDocument("# 正文\n\n必要知识\n---\n\n[返回模块](../modules/网络.md)\n\n旧推广标记", path=>assert.equal(readDocument(path),"# 正文\n\n必要知识"));
});

test("正文：CRLF旧推广尾段", async () => {
  withDocument("# 正文\r\n\r\n必要知识\r\n---\r\n\r\n[返回模块](../modules/网络.md)\r\n\r\n旧推广标记", path=>assert.equal(readDocument(path),"# 正文\r\n\r\n必要知识"));
});

test("正文：普通分割线与代码样例", async () => {
  withDocument("# 正文\n\n---\n\n必要知识\n\n```python\nprint('不要执行源文')\n```", path=>assert.equal(readDocument(path),"# 正文\n\n---\n\n必要知识\n\n```python\nprint('不要执行源文')\n```"));
});

test("搜索：45条条目按权威主题顺序完整输出", async () => {
  const index=buildSearchIndex(); assert.equal(index.length,45); assert.deepEqual(index.map(row=>row.id),rawTopics.map(t=>t.id)); assert.equal(new Set(index.map(row=>row.id)).size,45);
});

test("搜索：标题模块学习目标和知识点逐条对应源数据", async () => {
  const index=buildSearchIndex(); for(const source of rawTopics){ const row=index.find(r=>r.id===source.id)!; const module=rawModules.find(m=>m.id===source.module)!; assert.equal(row.title,source.title); assert.equal(row.module,source.module); assert.equal(row.moduleTitle,module.title); assert.ok(row.moduleEnglish.length>0); assert.deepEqual(row.objectives,source.learning_objectives); assert.deepEqual(row.unitTitles,rawUnits.filter(u=>u.topic===source.id).map(u=>u.title)); }
});

test("搜索：每个条目包含正文且项目base恰好一次", async () => {
  for(const row of buildSearchIndex()){ const topic=rawTopics.find(t=>t.id===row.id)!; const original=readFileSync(resolve(repo,topic.page),'utf8'); const heading=original.match(/^# (.+)$/m)![1]; assert.ok(row.text.includes(heading)); assert.equal(row.url,'/llm-systems-wiki/read/'+row.id+'/'); assert.equal(row.url.split('/llm-systems-wiki').length-1,1); assert.doesNotMatch(row.text,/\[返回模块\]|觉得这篇推导有帮助/); }
});

test("搜索：索引构建保留原始主题知识点及磁盘清单", async () => {
  const before={topics:structuredClone(topics),units:structuredClone(units),files:manifestPaths.map(p=>readFileSync(resolve(repo,p),'utf8'))}; buildSearchIndex(); assert.deepEqual(topics,before.topics); assert.deepEqual(units,before.units); assert.deepEqual(manifestPaths.map(p=>readFileSync(resolve(repo,p),'utf8')),before.files);
});

test("摘要：主题学习目标作为可见摘要保留", async () => {
  const description=topicDescription({...rawTopics[0],learning_objectives:['理解缓存','验证调度','评估吞吐']}); assert.ok(description.includes('理解缓存')); assert.ok(description.includes('验证调度'));
});

test("摘要：没有学习目标时不生成虚假文字", async () => {
  assert.equal(topicDescription({...rawTopics[0],learning_objectives:[]}), '');
});

test("接口：GET直接返回成功JSON与UTF8内容类型", async () => {
  const response=GET(); assert.equal(response.status,200); assert.match(response.headers.get('content-type')||'',/^application\/json\s*;\s*charset=utf-8$/i); const value=await response.json() as SearchItem[]; assert.equal(value.length,45); assert.deepEqual(value.map(row=>row.id),rawTopics.map(t=>t.id));
});

test("接口：GET载荷保留主题目标知识点和可打开链接", async () => {
  const value=await GET().json() as SearchItem[]; for(const topic of rawTopics){ const row=value.find(r=>r.id===topic.id)!; assert.ok(row); assert.equal(row.title,topic.title); assert.deepEqual(row.objectives,topic.learning_objectives); assert.deepEqual(row.unitTitles,rawUnits.filter(u=>u.topic===topic.id).map(u=>u.title)); assert.equal(row.url,'/llm-systems-wiki/read/'+topic.id+'/'); assert.ok(row.text.length>0); }
});
test("搜索：真实正文长段落进入索引而非仅标题", async () => {
  const source=readFileSync(resolve(repo,rawTopics[0].page),'utf8');
  const tree=unified().use(remarkParse).parse(source);
  const paragraphs=tree.children.filter(node=>node.type==='paragraph');
  const snippets=paragraphs.flatMap(node=>node.children.filter(child=>child.type==='text').map(child=>child.value)).filter(value=>value.length>80).slice(0,2);
  assert.equal(snippets.length,2,'原始文档应提供两段独立正文作为期待值');
  const actual=buildSearchIndex().find(row=>row.id===rawTopics[0].id)!;
  for(const snippet of snippets)assert.ok(actual.text.includes(snippet),'正文片段未进入全文索引：'+snippet.slice(0,40));
});

test("前沿清单：直接保留权威JSON的全部字段", () => {
  const expected=JSON.parse(readFileSync(resolve(repo,'knowledge/frontiers.json'),'utf8'));
  assert.deepEqual(frontiers,expected);
  for(const frontier of frontiers){assert.ok(frontier.id);assert.ok(frontier.title);assert.ok(frontier.summary);assert.ok(frontier.as_of);}
});

test("前沿路由：七模块均有唯一研究入口且不依赖正文预加载", () => {
  assert.equal(frontiers.length,7);
  assert.deepEqual(new Set(frontiers.map(f=>f.module)),new Set(rawModules.map(m=>m.id)));
  assert.equal(new Set(frontiers.map(f=>f.id)).size,frontiers.length);
  assert.equal(new Set(frontiers.map(f=>f.page)).size,frontiers.length);
  for(const frontier of frontiers)assert.equal(routes[frontier.page],'/research/'+frontier.id+'/');
});

test("来源清单：读取资料卡索引并保留身份主题与归档状态", () => {
  const expected=JSON.parse(readFileSync(resolve(repo,'sources/library/index.json'),'utf8'));
  assert.deepEqual(sourceCards,expected);
  assert.equal(new Set(sourceCards.map(card=>card.id)).size,sourceCards.length);
  for(const card of sourceCards)assert.equal(routes[card.path],'/sources/'+card.id+'/');
});

test("来源路由：研究正文的相对资料卡链接转换到一次站点base", () => {
  assert.ok(frontiers.length>0);assert.ok(sourceCards.length>0);
  const origin=frontiers[0].page;
  for(const card of sourceCards){
    const href=posix.relative(posix.dirname(origin),card.path);
    assert.equal(resolveLink(href,origin,routes),'/llm-systems-wiki/sources/'+card.id+'/');
  }
});

test("导览：学习研究与来源入口都有可解析的站内路由", () => {
  const guide=guides.find(g=>g.id==='tour');assert.ok(guide);
  assert.equal(guide.page,'docs/仓库导览.md');assert.equal(routes[guide.page],'/guides/tour/');
  assert.equal(resolveLink('../wiki/paths/基础入门路径.md',guide.page,routes),'/llm-systems-wiki/paths/foundations/');
  assert.equal(resolveLink('../wiki/frontiers/README.md',guide.page,routes),'/llm-systems-wiki/research/');
  assert.equal(resolveLink('../sources/README.md',guide.page,routes),'/llm-systems-wiki/sources/');
});

test("资料库路由：不把本地原文缓存登记为网站页面", () => {
  for(const [source,target] of Object.entries(routes)){
    assert.equal(source.includes('sources/.local/'),false,source);
    assert.equal(target.includes('sources/.local/'),false,target);
  }
});
