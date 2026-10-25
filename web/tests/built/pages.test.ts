/** 构建后装配验证：显式运行tests/built/pages.test.ts；不执行浏览器或第三方图形脚本。 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, join, posix } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Script } from 'node:vm';
import { createRequire } from 'node:module';
import { setImmediate as yieldEventLoop } from 'node:timers/promises';
import { paths, guides, type Topic, type Unit, type Frontier, type SourceCard } from '../../src/lib/content';
const repo=fileURLToPath(new URL('../../../',import.meta.url));
const base='/llm-systems-wiki';
const read=<T>(path:string):T=>JSON.parse(readFileSync(resolve(repo,path),'utf8')) as T;
const rawTopics=read<Topic[]>('knowledge/topics.json');
const rawUnits=read<Unit[]>('knowledge/units.json');
const rawModules=read<{id:string;title:string}[]>('knowledge/modules.json');
const rawCapabilities=read<{module:string;outcome:string}[]>('knowledge/capabilities.json');
const rawSources=read<{id:string;url:string;title:string;reading_scope:string;locator?:string}[]>('sources/manifest/sources.json');
const rawFrontiers=read<Frontier[]>('knowledge/frontiers.json');
const rawSourceCards=read<SourceCard[]>('sources/library/index.json');
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
  await page('sources/index.html',doc=>{const entries=[...doc.querySelectorAll<HTMLAnchorElement>('[data-source-row]')]; assert.equal(entries.length,rawSources.length); assert.equal(get(doc,'[data-source-count]').textContent,String(rawSources.length)); for(let i=0;i<entries.length;i++){const entry=entries[i],source=rawSources[i]; assert.equal(entry.getAttribute('href'),base+'/sources/'+source.id+'/'); assert.equal(entry.dataset.sourceUrl,source.url); assert.equal(get(entry,'h2').textContent,source.title); assert.ok(get(entry,'code').textContent?.startsWith(source.id+' ·')); assert.equal(get(entry,'p').textContent,source.reading_scope);}});
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

test("研究总览：七模块卡片关联正确标题摘要日期及详情路由", async()=>{
  assert.equal(rawFrontiers.length,7);
  await page('research/index.html',doc=>{
    const cards=[...doc.querySelectorAll<HTMLAnchorElement>('[data-research-card]')];
    assert.equal(cards.length,rawFrontiers.length);
    for(const frontier of rawFrontiers){
      const card=cards.find(c=>c.getAttribute('href')===base+'/research/'+frontier.id+'/');assert.ok(card);
      assert.equal(get(card,'h2').textContent,frontier.title);
      assert.ok(card.textContent?.includes(frontier.summary));assert.ok(card.textContent?.includes(frontier.as_of));
      assert.deepEqual((get(card,'.module-card-foot').textContent||'').match(/\d+/g)?.map(Number),[frontier.paper_ids.length,frontier.repository_ids.length]);
    }
  });
});

test("研究详情：正文版本与基础主题来源可追溯", async()=>{
  for(const frontier of rawFrontiers){
    assert.ok(frontier.topic_ids.length>0);assert.ok(frontier.source_ids.length>0);
    const markdown=readFileSync(resolve(repo,frontier.page),'utf8');
    const declaredPaths=new Set([...markdown.matchAll(/\[[^\]]*\]\(([^)\s]+)\)/g)]
      .map(match=>posix.normalize(posix.join(posix.dirname(frontier.page),decodeURIComponent(match[1].split(/[?#]/)[0])))));
    const declaredTopics=rawTopics.filter(topic=>declaredPaths.has(topic.page));
    const declaredSources=rawSourceCards.filter(card=>declaredPaths.has(card.path));
    assert.ok(declaredTopics.length>0);assert.ok(declaredSources.length>0);
    await page('research/'+frontier.id+'/index.html',doc=>{
      assert.equal(get(doc,'.article-header h1').textContent,frontier.title);
      assert.ok(get(doc,'.article-deck').textContent?.includes(frontier.as_of));
      assert.ok([...doc.querySelectorAll<HTMLAnchorElement>('.article-actions a')].some(a=>decodedSource(a.href)===frontier.page));
      const body=get(doc,'.markdown');assert.ok((body.textContent||'').length>100);
      const links=new Set([...body.querySelectorAll<HTMLAnchorElement>('a[href]')].map(a=>a.getAttribute('href')!.split('#')[0]));
      for(const id of frontier.topic_ids)assert.ok(rawTopics.some(t=>t.id===id));
      for(const id of frontier.source_ids)assert.ok(rawSources.some(s=>s.id===id));
      for(const topic of declaredTopics)assert.ok(links.has(base+'/read/'+topic.id+'/'),frontier.id+' 正文基础主题 '+topic.id);
      for(const card of declaredSources)assert.ok(links.has(base+'/sources/'+card.id+'/'),frontier.id+' 正文来源 '+card.id);
    });
  }
});

test("来源详情：每个来源ID有资料卡并首先提供原始地址", async()=>{
  assert.deepEqual(new Set(rawSourceCards.map(c=>c.id)),new Set(rawSources.map(s=>s.id)));
  const failures:string[]=[];
  for(const source of rawSources){
    const card=rawSourceCards.find(c=>c.id===source.id);assert.ok(card);
    try {await page('sources/'+source.id+'/index.html',doc=>{
      assert.equal(get(doc,'.article-header h1').textContent,source.title);
      const body=get(doc,'.markdown');
      assert.equal(get<HTMLAnchorElement>(body,'a[href]').href,new URL(source.url).href);
      assert.ok(body.textContent?.includes(source.id));
      const metadata=[...body.querySelectorAll('li')].map(item=>item.textContent||'');
      const readingScope=metadata.find(text=>text.startsWith('实际登记的读取范围：'))?.slice('实际登记的读取范围：'.length);
      if(readingScope!==source.reading_scope)failures.push(source.id+'：读取范围未按登记保留 '+source.reading_scope);
      if(typeof source.locator==='string'){
        const locator=metadata.find(text=>text.startsWith('定位：'))?.slice('定位：'.length);
        if(locator!==source.locator)failures.push(source.id+'：定位符号未按登记保留 '+source.locator);
      }
      assert.ok([...doc.querySelectorAll<HTMLAnchorElement>('.article-actions a')].some(a=>decodedSource(a.href)===card.path));
      const hrefs=new Set([...body.querySelectorAll<HTMLAnchorElement>('a[href]')].map(a=>a.getAttribute('href')));
      for(const topic of card.topic_ids)assert.ok(hrefs.has(base+'/read/'+topic+'/'),source.id+' 关联主题 '+topic);
    });} catch(error){failures.push(source.id+'：'+String(error));}
  }
  assert.deepEqual(failures,[],'资料卡正文必须保持来源标识及注册读取范围');
});

test("模块研究入口：每个模块跳转到所属前沿详情", async()=>{
  for(const module of rawModules){
    const frontier=rawFrontiers.find(f=>f.module===module.id);assert.ok(frontier);
    await page('modules/'+module.id+'/index.html',doc=>{
      assert.equal(get<HTMLAnchorElement>(doc,'.module-update a').getAttribute('href'),base+'/research/'+frontier.id+'/');
    });
  }
});

test("导览与导航：学习研究来源三个入口在新页面保持可达", async()=>{
  for(const name of ['research/index.html','sources/index.html','guides/tour/index.html']){
    await page(name,doc=>{
      const nav=new Set([...doc.querySelectorAll<HTMLAnchorElement>('.primary-nav a,.secondary-nav a')].map(a=>a.getAttribute('href')));
      for(const route of ['/guides/tour/','/research/','/sources/'])assert.ok(nav.has(base+route),name+' '+route);
      if(name==='guides/tour/index.html'){
        const links=new Set([...doc.querySelectorAll<HTMLAnchorElement>('.markdown a')].map(a=>a.getAttribute('href')));
        for(const route of ['/paths/foundations/','/research/','/sources/'])assert.ok(links.has(base+route),route);
      }
    });
  }
});

test("公开产物：本地缓存对象不被复制或作为资源链接发布", ()=>{
  function files(dir:string):string[]{return readdirSync(dir,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?files(join(dir,entry.name)):[join(dir,entry.name)]);}
  const cachedNames=new Set<string>();
  for(const card of rawSourceCards){
    const archive=read<{captures:{sha256:string}[]}>('sources/library/'+card.id+'/archive.json');
    for(const capture of archive.captures)cachedNames.add(capture.sha256+'.bin');
  }
  for(const file of files(resolve(repo,'web/dist'))){
    assert.equal(file.includes('/.local/'),false,file);
    assert.equal(cachedNames.has(file.split('/').at(-1)!),false,file);
    if(file.endsWith('.html'))assert.doesNotMatch(readFileSync(file,'utf8'),/(?:href|src)=["'][^"']*sources\/\.local\//,file);
  }
});

test("来源状态：列表如实区分已保存记录与未取得记录", async()=>{
  const expected=new Map(rawSourceCards.map(card=>[card.id,card.archive_status]));
  const observed=new Set<string>();
  await page('sources/index.html',doc=>{
    for(const entry of doc.querySelectorAll<HTMLAnchorElement>('[data-source-row]')){
      const id=entry.getAttribute('href')!.split('/').filter(Boolean).at(-1)!;
      const status=expected.get(id);assert.ok(status,id);
      const label=get(entry,'code').textContent||'';
      observed.add(status);
      if(status==='saved')assert.match(label,/已保存|已归档/,id+' 必须明确有保存记录');
      else if(status==='failed'){
        assert.doesNotMatch(label,/已保存|已归档/,id+' 失败不得宣称成功');
        assert.match(label,/不可用|失败|未取得/,id+' 必须说明未取得原文');
      }else{
        assert.doesNotMatch(label,/已保存|已归档/,id+' 未下载不得宣称成功');
        assert.match(label,/资料卡|未下载|未请求/,id+' 应区分索引与原文保存');
      }
    }
  });
  assert.ok(observed.has('saved'));assert.ok(observed.has('failed'));
});
