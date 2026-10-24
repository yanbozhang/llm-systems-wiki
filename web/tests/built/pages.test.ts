/** 构建后装配验证：显式运行tests/built/pages.test.ts；不执行浏览器或第三方图形脚本。 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Script } from 'node:vm';
import { createRequire } from 'node:module';
import { setImmediate as yieldEventLoop } from 'node:timers/promises';
import { paths, guides, type Topic, type Unit } from '../../src/lib/content';
const repo=fileURLToPath(new URL('../../../',import.meta.url));
const base='/llm-systems-wiki';
const read=<T>(path:string):T=>JSON.parse(readFileSync(resolve(repo,path),'utf8')) as T;
const rawTopics=read<Topic[]>('knowledge/topics.json');
const rawUnits=read<Unit[]>('knowledge/units.json');
const rawModules=read<{id:string;title:string}[]>('knowledge/modules.json');
const rawCapabilities=read<{module:string;outcome:string}[]>('knowledge/capabilities.json');
const rawSources=read<{id:string;url:string;title:string;reading_scope:string}[]>('sources/manifest/sources.json');
const layout=readFileSync(resolve(repo,'web/src/layouts/SiteLayout.astro'),'utf8');
const themeScript=layout.match(/<script is:inline>([\s\S]*?)<\/script>/)![1];
const { JSDOM }=createRequire(import.meta.url)('jsdom') as {
  JSDOM:new(html:string,options:{url:string})=>{window:{document:Document;close():void}};
};
async function page(name:string,assertions:(document:Document)=>void){
  const dom=new JSDOM(readFileSync(resolve(repo,'web/dist',name),'utf8'),{url:'https://yanbozhang.github.io'+base+'/'});
  try {assertions(dom.window.document);}
  finally {dom.window.close();await yieldEventLoop();}
}
function get<T extends Element=HTMLElement>(parent:Document|Element,selector:string):T {
  const element=parent.querySelector<T>(selector);assert.ok(element,'构建HTML缺少 '+selector);return element;
}
function decodedSource(href:string){
  const url=new URL(href);
  if(url.origin!=='https://github.com')return '';
  return decodeURIComponent(url.pathname).replace(/^\/yanbozhang\/llm-systems-wiki\/blob\/main\//,'');
}
function validateCards(doc:Document){
  for(const card of doc.querySelectorAll<HTMLElement>('[data-topic-card]')){
    const topic=rawTopics.find(t=>t.id===card.dataset.id);assert.ok(topic);
    assert.equal(card.dataset.module,topic.module);
    assert.equal(get<HTMLAnchorElement>(card,'.topic-card-title').getAttribute('href'),base+'/read/'+topic.id+'/');
    assert.equal(get(card,'h3').textContent,topic.title);
    assert.equal(get<HTMLElement>(card,'[data-bookmark]').dataset.bookmark,topic.id);
    assert.ok(card.textContent?.includes(String(topic.unit_ids.length)+' 个知识点'));
  }
}

test("首页：统计模块入口及推荐卡片关联真实清单", async()=>{
  await page('index.html',doc=>{assert.deepEqual([...doc.querySelectorAll('.stats-strip strong')].map(e=>parseInt(e.textContent||'',10)),[7,45,135,6]); const cards=[...doc.querySelectorAll<HTMLAnchorElement>('.module-card')]; assert.equal(cards.length,7); for(const module of rawModules){const card=cards.find(c=>c.getAttribute('href')===base+'/modules/'+module.id+'/')!; assert.ok(card,module.id); assert.ok(card.textContent?.includes(module.title)); const ids=new Set(rawTopics.filter(t=>t.module===module.id).map(t=>t.id)); assert.deepEqual((get(card,'.module-card-foot').textContent||'').match(/\d+/g)?.map(Number),[ids.size,rawUnits.filter(u=>ids.has(u.topic)).length]);} validateCards(doc);});
});

test("知识库：45张主题卡完整映射标题链接收藏与知识点数", async()=>{
  await page('library/index.html',doc=>{const cards=[...doc.querySelectorAll<HTMLElement>('[data-topic-card]')]; assert.equal(cards.length,45); assert.deepEqual(cards.map(c=>c.dataset.id),rawTopics.map(t=>t.id)); validateCards(doc); assert.equal(get(doc,'[data-result-count]').textContent,'45');});
});

test("模块页：七个getStaticPaths输出只装配所属主题与能力", async()=>{
  for(const module of rawModules){await page('modules/'+module.id+'/index.html',doc=>{const expected=rawTopics.filter(t=>t.module===module.id); assert.deepEqual([...doc.querySelectorAll<HTMLElement>('[data-topic-card]')].map(c=>c.dataset.id),expected.map(t=>t.id),module.id); assert.equal(get<HTMLElement>(doc,'[data-catalog]').dataset.initialModule,module.id); assert.equal(doc.querySelectorAll('[data-module-filter]').length,0); assert.equal(get(doc,'[data-result-count]').textContent,String(expected.length)); for(const goal of rawCapabilities.filter(c=>c.module===module.id))assert.ok(get(doc,'.module-goals').textContent?.includes(goal.outcome)); validateCards(doc);});}
});

test("文章页：45个稳定路由绑定正确正文示例与收藏目标", async()=>{
  for(const topic of rawTopics){await page('read/'+topic.id+'/index.html',doc=>{assert.equal(get(doc,'.article-header h1').textContent,topic.title,topic.id); assert.equal(get<HTMLElement>(doc,'.article-save').dataset.bookmark,topic.id); assert.equal(parseInt(get(doc,'.article-unit-count').textContent||'',10),topic.unit_ids.length); const actions=[...doc.querySelectorAll<HTMLAnchorElement>('.article-actions a')]; assert.ok(actions.some(a=>decodedSource(a.href)===topic.page),topic.id+' Markdown来源'); assert.ok(actions.some(a=>decodedSource(a.href)===topic.example),topic.id+' 示例来源'); const body=get(doc,'.markdown').textContent||''; for(const unit of rawUnits.filter(u=>u.topic===topic.id))assert.ok(body.includes(unit.title),topic.id+' '+unit.id); assert.match(get(doc,'.language-note').textContent||'',/written in Chinese/); assert.ok(doc.querySelectorAll('.katex math').length>=topic.unit_ids.length,topic.id+' 数学节点');});}
});

test("文章目录：构建后的章节锚点按正文顺序对应", async()=>{
  for(const topic of rawTopics){await page('read/'+topic.id+'/index.html',doc=>{const headings=[...doc.querySelectorAll<HTMLElement>('.markdown h2[id], .markdown h3[id]')]; const links=[...doc.querySelectorAll<HTMLAnchorElement>('.article-toc .toc-link')]; assert.deepEqual(links.map(a=>decodeURIComponent(a.hash.slice(1))),headings.map(h=>h.id),topic.id); assert.equal(new Set(headings.map(h=>h.id)).size,headings.length,topic.id+' 章节ID');});}
});

test("前后篇：边界与中间文章的链接文字和方向正确", async()=>{
  const selected=[rawTopics[0],rawTopics[1],rawTopics[rawTopics.length-1]]; for(const topic of selected){await page('read/'+topic.id+'/index.html',doc=>{const current=rawTopics.findIndex(t=>t.id===topic.id); const links=[...doc.querySelectorAll<HTMLAnchorElement>('.article-pagination a')]; assert.ok(links.length>=1&&links.length<=2); for(const link of links){const id=link.getAttribute('href')!.split('/').filter(Boolean).at(-1)!; const target=rawTopics.find(t=>t.id===id); assert.ok(target); assert.notEqual(id,topic.id); assert.equal(get(link,'strong').textContent,target.title); const targetIndex=rawTopics.findIndex(t=>t.id===id); assert.ok(link.classList.contains('next')?targetIndex>current:targetIndex<current);}});}
});

test("学习路径：总览六入口与详情页来源一一对应", async()=>{
  await page('paths/index.html',doc=>{assert.deepEqual([...doc.querySelectorAll<HTMLAnchorElement>('.path-card')].map(a=>a.getAttribute('href')).sort(),paths.map(p=>base+p.url).sort());}); for(const path of paths){await page('paths/'+path.id+'/index.html',doc=>{assert.ok(get(doc,'.article-header h1').textContent?.includes(path.title)); assert.ok([...doc.querySelectorAll<HTMLAnchorElement>('.article-actions a')].some(a=>decodedSource(a.href)===path.page)); assert.ok(get(doc,'.markdown').textContent!.length>100);});}
});

test("指南：已登记指南详情绑定各自Markdown", async()=>{
  for(const guide of guides){await page('guides/'+guide.id+'/index.html',doc=>{assert.equal(get(doc,'.article-header h1').textContent,guide.title); assert.ok([...doc.querySelectorAll<HTMLAnchorElement>('.article-actions a')].some(a=>decodedSource(a.href)===guide.page)); assert.ok(get(doc,'.markdown').textContent!.length>100);});}
});

test("来源页：全部条目保持来源链接标题和读取范围", async()=>{
  await page('sources/index.html',doc=>{const entries=[...doc.querySelectorAll<HTMLAnchorElement>('[data-source-row]')]; assert.equal(entries.length,rawSources.length); assert.equal(get(doc,'[data-source-count]').textContent,String(rawSources.length)); for(let i=0;i<entries.length;i++){const entry=entries[i],source=rawSources[i]; assert.equal(entry.href,new URL(source.url).href); assert.equal(get(entry,'h2').textContent,source.title); assert.ok(get(entry,'code').textContent?.startsWith(source.id+' ·')); assert.equal(get(entry,'p').textContent,source.reading_scope);}});
});

test("布局：canonical与主导航站内地址包含一次项目base", async()=>{
  for(const name of ['index.html','library/index.html','read/transformer/index.html']){await page(name,doc=>{const route=name==='index.html'?'/':('/'+name.replace(/index\.html$/,'')); assert.equal(get<HTMLLinkElement>(doc,'link[rel="canonical"]').href,'https://yanbozhang.github.io'+base+route); const links=[...doc.querySelectorAll<HTMLAnchorElement>('.primary-nav a, .module-nav a')]; assert.equal(doc.querySelectorAll('.module-nav a').length,7); for(const link of links){const value=link.getAttribute('href')!; assert.ok(value.startsWith(base+'/')); assert.equal(value.split(base).length-1,1);} assert.ok(doc.querySelector('#search-dialog #global-search')); assert.ok(doc.querySelector('[data-language-toggle]'));});}
});

test("404：提供可打开的站点首页入口", async()=>{
  await page('404.html',doc=>{assert.ok(doc.querySelector('a.button[href="'+base+'/"]')); assert.ok(get(doc,'#main-content').textContent?.includes('404'));});
});

test("首屏主题：已保存的明暗偏好恢复到页面状态", async()=>{
  for(const theme of ['light','dark']){const document={documentElement:{dataset:{theme:theme==='light'?'dark':'light'}}}; new Script(themeScript).runInNewContext({document,localStorage:{getItem:()=>theme}}); assert.equal(document.documentElement.dataset.theme,theme);}
});

test("首屏主题：无效偏好不会进入主题状态", async()=>{
  const document={documentElement:{dataset:{theme:'light'}}}; new Script(themeScript).runInNewContext({document,localStorage:{getItem:()=>'<invalid>'}}); assert.equal(document.documentElement.dataset.theme,'light');
});

test("首屏主题：存储读取失败时保持默认主题可读", async()=>{
  const document={documentElement:{dataset:{theme:'light'}}}; new Script(themeScript).runInNewContext({document,localStorage:{getItem(){throw new Error('blocked');}}}); assert.equal(document.documentElement.dataset.theme,'light');
});
