/** 事件级单测：真实业务模块 + happy-dom；第三方图形渲染与浏览器默认动作单独验收。 */
import test, { type TestContext } from 'node:test';
import assert from 'node:assert/strict';
import { setImmediate as immediate } from 'node:timers/promises';
import { Window } from 'happy-dom';
import { bindCatalog } from '../src/client/catalog';
import type { SearchItem } from '../src/lib/navigation';

const make=(id:string,title:string,module:string,extra:Partial<SearchItem>={}):SearchItem=>({
  id,title,module,moduleTitle:module==='inference'?'推理':'训练',moduleEnglish:module==='inference'?'Inference':'Training',
  unitTitles:[],objectives:[],text:'',url:'/llm-systems-wiki/read/'+id+'/',description:'主题说明',...extra
});
const rows:SearchItem[]=[
  make('a','Attention 原理','training',{text:'cache'}),
  make('b','KV Cache 缓存','inference',{text:'needle 正文词'}),
  make('c','KV 训练','training',{objectives:['理解 cache']}),
  make('d','KV 调度','inference',{unitTitles:['cache 分页']})
];
interface Options {
  initialModule?:string;
  modules?:('site'|'reader')[];
  fetch?:()=>Promise<Response>;
  storage?:'denied'|{getItem:(key:string)=>string|null;setItem:(key:string,value:string)=>void};
  language?:string;
  htmlLanguage?:string;
  clipboard?:(text:string)=>Promise<void>;
}
function response(data:unknown,status=200):Response {
  return {ok:status>=200&&status<300,status,json:async()=>data} as Response;
}
function deferred<T>() {
  let resolve!:(value:T|PromiseLike<T>)=>void;
  let reject!:(reason:unknown)=>void;
  const promise=new Promise<T>((ok,fail)=>{resolve=ok;reject=fail;});
  return {promise,resolve,reject};
}
const flush=async()=>{await immediate();};
function q<T extends HTMLElement=HTMLElement>(selector:string):T {
  const node=document.querySelector<T>(selector);assert.ok(node,'测试夹具缺少 '+selector);return node;
}
function click(selector:string){q<HTMLButtonElement>(selector).click();}
function input(selector:string,value:string){const node=q<HTMLInputElement>(selector);node.value=value;node.dispatchEvent(new Event('input',{bubbles:true}));}
function visibleCards(){return [...document.querySelectorAll<HTMLElement>('[data-topic-card]')].filter(e=>!e.hidden).map(e=>e.dataset.id);}
function visibleSources(){return [...document.querySelectorAll<HTMLElement>('[data-source-row]')].filter(e=>!e.hidden).map(e=>e.dataset.sourceRow);}
let moduleSequence=0;
function markup(initial='all'){
  return '<button data-open-search>搜索</button><button data-language-toggle>EN</button><button data-theme-toggle>主题</button>'
    +'<button data-open-menu aria-expanded="false">菜单</button><button data-close-menu>关闭菜单</button><nav class="sidebar"><a href="#原理">文章</a></nav>'
    +'<span id="label" data-zh="全部主题" data-en="All topics">全部主题</span>'
    +'<dialog id="search-dialog"><input id="global-search" data-placeholder-zh="搜索主题、公式、工具…" data-placeholder-en="Search topics, equations, tools…"><button data-close-search>Esc</button><div id="search-results"></div></dialog>'
    +'<section data-catalog data-initial-module="'+initial+'"><input data-catalog-search data-placeholder-zh="搜索主题、知识点或技术关键词…" data-placeholder-en="Search topics, ideas, or technical keywords…">'
    +'<button data-module-filter="all" aria-pressed="true">全部</button><button data-module-filter="inference" aria-pressed="false">推理</button><button data-module-filter="training" aria-pressed="false">训练</button>'
    +'<button data-saved-filter aria-pressed="false">收藏</button><button data-view="grid" aria-pressed="true">卡片</button><button data-view="list" aria-pressed="false">列表</button>'
    +'<strong data-result-count>4</strong><div data-topic-grid>'
    +rows.map(row=>'<article data-topic-card data-id="'+row.id+'" data-module="'+row.module+'"><h2>'+row.title+'</h2><button data-bookmark="'+row.id+'" aria-pressed="false">收藏</button></article>').join('')
    +'</div><div data-catalog-empty hidden><button data-reset-catalog>重置</button></div></section>'
    +'<input data-source-search data-placeholder-zh="搜索来源名称、类型或读取范围…" data-placeholder-en="Filter sources by title or scope…"><strong data-source-count>3</strong>'
    +'<a data-source-row="both">LangGraph Runtime Library</a><a data-source-row="one">LangGraph paper</a><a data-source-row="other">Transformer library</a><div data-source-empty hidden>没有来源</div>'
    +'<div class="language-note">This article is written in Chinese. The original equations, source links, and code remain unchanged.</div>'
    +'<article class="markdown"><h2 id="原理">中文正文原理</h2><h3 id="实验">中文正文实验</h3><div class="code-block"><pre><code>const answer = 42;\n</code></pre><button class="copy-code">复制</button></div></article>'
    +'<aside class="article-toc"><a id="toc-first" class="toc-link" href="#%E5%8E%9F%E7%90%86">原理</a><a id="toc-second" class="toc-link" href="#实验">实验</a></aside><div id="toast"></div>';
}
function mount(t:TestContext,options:Options={}) {
  const win=new Window({url:'https://example.org/llm-systems-wiki/',settings:{disableJavaScriptEvaluation:true,disableJavaScriptFileLoading:true,disableCSSFileLoading:true}});
  win.document.body.innerHTML=markup(options.initialModule);
  win.document.documentElement.lang=options.htmlLanguage||'zh-CN';
  win.document.documentElement.dataset.theme='light';
  if(options.language)win.localStorage.setItem('llmwiki:language',options.language);
  if(options.storage==='denied')Object.defineProperty(win,'localStorage',{configurable:true,get(){throw new Error('storage denied');}});
  else if(options.storage)Object.defineProperty(win,'localStorage',{configurable:true,value:options.storage});
  Object.defineProperty(win.navigator,'clipboard',{configurable:true,value:{writeText:options.clipboard|| (async()=>{})}});
  const observers:FakeObserver[]=[];
  class FakeObserver {
    targets=new Set<Element>();
    constructor(private callback:IntersectionObserverCallback){observers.push(this);}
    observe(target:Element){this.targets.add(target);}
    unobserve(target:Element){this.targets.delete(target);}
    disconnect(){this.targets.clear();}
    takeRecords(){return [];}
    fire(target:Element){this.callback([{target,isIntersecting:true} as IntersectionObserverEntry],this as unknown as IntersectionObserver);}
  }
  Object.defineProperty(win,'IntersectionObserver',{configurable:true,value:FakeObserver});
  const saved=new Map<string,PropertyDescriptor|undefined>();
  const replace=(key:string,value:unknown)=>{saved.set(key,Object.getOwnPropertyDescriptor(globalThis,key));Object.defineProperty(globalThis,key,{configurable:true,writable:true,value});};
  replace('window',win);
  for(const key of ['document','navigator','HTMLElement','HTMLInputElement','HTMLDialogElement','HTMLButtonElement','Element','Node','Event','CustomEvent','KeyboardEvent','MouseEvent']){
    replace(key,(win as unknown as Record<string,unknown>)[key]);
  }
  replace('IntersectionObserver',FakeObserver);
  const requests:string[]=[];
  replace('fetch',async(url:unknown)=>{requests.push(String(url));return options.fetch?options.fetch():response(rows);});
  t.after(async()=>{
    t.mock.timers.reset();
    await win.happyDOM.abort();
    win.close();
    for(const [key,descriptor] of saved){if(descriptor)Object.defineProperty(globalThis,key,descriptor);else Reflect.deleteProperty(globalThis,key);}
  });
  return {win,requests,observers};
}
async function boot(t:TestContext,options:Options={}) {
  const env=mount(t,options);
  for(const name of options.modules||['site']){
    await import(new URL('../src/client/'+name+'.ts?unit_case='+ ++moduleSequence,import.meta.url).href);
  }
  t.mock.timers.enable({apis:['setTimeout']});
  return env;
}

test("搜索：点击打开聚焦并可由关闭按钮关闭", async (t) => {
  const env=await boot(t); click('[data-open-search]'); await flush(); assert.equal(q<HTMLDialogElement>('#search-dialog').open,true); assert.equal(document.activeElement,q('#global-search')); assert.equal(env.requests[0],'/llm-systems-wiki/search-index.json'); click('[data-close-search]'); assert.equal(q<HTMLDialogElement>('#search-dialog').open,false);
});

test("搜索：CtrlK快捷键打开并阻止默认行为", async (t) => {
  await boot(t); const event=new KeyboardEvent('keydown',{key:'K',ctrlKey:true,bubbles:true,cancelable:true}); document.dispatchEvent(event); await flush(); assert.equal(event.defaultPrevented,true); assert.equal(q<HTMLDialogElement>('#search-dialog').open,true); assert.equal(document.activeElement,q('#global-search'));
});

test("搜索：CmdK快捷键打开并阻止默认行为", async (t) => {
  await boot(t); const event=new KeyboardEvent('keydown',{key:'K',metaKey:true,bubbles:true,cancelable:true}); document.dispatchEvent(event); await flush(); assert.equal(event.defaultPrevented,true); assert.equal(q<HTMLDialogElement>('#search-dialog').open,true); assert.equal(document.activeElement,q('#global-search'));
});

test("搜索：索引加载期间连续输入只显示最新查询", async (t) => {
  const pending=deferred<Response>(); const env=await boot(t,{fetch:()=>pending.promise}); click('[data-open-search]'); input('#global-search','Attention'); input('#global-search','needle'); assert.equal(env.requests.length,1); pending.resolve(response(rows)); await flush(); assert.deepEqual([...document.querySelectorAll<HTMLAnchorElement>('.search-result')].map(a=>a.getAttribute('href')),['/llm-systems-wiki/read/b/']); assert.equal(q('.search-result strong').textContent,'KV Cache 缓存');
});

test("搜索：失败后提示仍可浏览且下一次打开可重试", async (t) => {
  let calls=0; await boot(t,{fetch:async()=>++calls===1?response([],503):response(rows)}); click('[data-open-search]'); await flush(); assert.match(q('#search-results').textContent||'',/继续浏览/); click('[data-open-search]'); await flush(); assert.equal(calls,2); assert.ok(document.querySelectorAll('.search-result').length>0); assert.match(q('.markdown').textContent||'',/中文正文/);
});

test("搜索：零结果给出明确提示", async (t) => {
  await boot(t); click('[data-open-search]'); input('#global-search','no-such-term'); await flush(); assert.equal(document.querySelectorAll('.search-result').length,0); assert.match(q('#search-results').textContent||'',/没有找到/);
});

test("目录：关键词模块和收藏三条件共同筛选", async (t) => {
  mount(t); const saved=['b']; bindCatalog(async()=>rows,()=>saved); input('[data-catalog-search]','KV'); await flush(); assert.deepEqual(visibleCards(),['b','c','d']); click('[data-module-filter="inference"]'); await flush(); assert.deepEqual(visibleCards(),['b','d']); click('[data-saved-filter]'); await flush(); assert.deepEqual(visibleCards(),['b']); assert.equal(q('[data-result-count]').textContent,'1'); assert.equal(q('[data-saved-filter]').getAttribute('aria-pressed'),'true');
});

test("目录：重置清空关键词收藏并恢复页面初始模块", async (t) => {
  mount(t,{initialModule:'inference'}); bindCatalog(async()=>rows,()=>['b']); input('[data-catalog-search]','no-match'); click('[data-module-filter="training"]'); click('[data-saved-filter]'); await flush(); assert.equal(q<HTMLElement>('[data-catalog-empty]').hidden,false); click('[data-reset-catalog]'); await flush(); assert.equal(q<HTMLInputElement>('[data-catalog-search]').value,''); assert.equal(q('[data-saved-filter]').getAttribute('aria-pressed'),'false'); assert.equal(q('[data-module-filter="inference"]').getAttribute('aria-pressed'),'true'); assert.deepEqual(visibleCards(),['b','d']); assert.equal(document.activeElement,q('[data-catalog-search]'));
});

test("目录：列表卡片切换只更新视图状态", async (t) => {
  mount(t); bindCatalog(async()=>rows,()=>[]); click('[data-view="list"]'); assert.ok(q('[data-topic-grid]').classList.contains('list-view')); assert.equal(q('[data-view="list"]').getAttribute('aria-pressed'),'true'); assert.equal(q('[data-view="grid"]').getAttribute('aria-pressed'),'false'); click('[data-view="grid"]'); assert.equal(q('[data-topic-grid]').classList.contains('list-view'),false); assert.equal(q('[data-view="grid"]').getAttribute('aria-pressed'),'true'); assert.equal(visibleCards().length,4);
});

test("目录：收藏变化事件实时更新收藏结果", async (t) => {
  mount(t); let saved=['b']; bindCatalog(async()=>rows,()=>saved); click('[data-saved-filter]'); await flush(); assert.deepEqual(visibleCards(),['b']); saved=['d']; document.dispatchEvent(new Event('bookmarks-change')); await flush(); assert.deepEqual(visibleCards(),['d']); assert.equal(q('[data-result-count]').textContent,'1');
});

test("目录：相关性顺序传递到卡片显示顺序", async (t) => {
  mount(t); bindCatalog(async()=>rows,()=>[]); input('[data-catalog-search]','cache'); await flush(); const cards=[...document.querySelectorAll<HTMLElement>('[data-topic-card]')].filter(c=>!c.hidden).sort((a,b)=>Number(a.style.order)-Number(b.style.order)); assert.deepEqual(cards.map(c=>c.dataset.id),['b','d','c','a']);
});

test("目录：较早成功响应不能覆盖较新的搜索结果", async (t) => {
  mount(t); const older=deferred<SearchItem[]>(),newer=deferred<SearchItem[]>(); let calls=0; bindCatalog(()=>++calls===1?older.promise:newer.promise,()=>[]); input('[data-catalog-search]','old'); input('[data-catalog-search]','needle'); newer.resolve(rows); await flush(); assert.deepEqual(visibleCards(),['b']); older.resolve([rows[0]]); await flush(); assert.deepEqual(visibleCards(),['b']); assert.equal(q('[data-result-count]').textContent,'1');
});

test("目录：较早失败响应不能覆盖较新的成功搜索", async (t) => {
  mount(t); const older=deferred<SearchItem[]>(),newer=deferred<SearchItem[]>(); let calls=0; bindCatalog(()=>++calls===1?older.promise:newer.promise,()=>[]); input('[data-catalog-search]','old'); input('[data-catalog-search]','needle'); newer.resolve(rows); await flush(); assert.deepEqual(visibleCards(),['b']); older.reject(new Error('older request failed')); await flush(); assert.deepEqual(visibleCards(),['b']); assert.equal(q('[data-result-count]').textContent,'1');
});

test("目录：当前加载失败时保留基本标题模块和收藏筛选", async (t) => {
  mount(t); bindCatalog(async()=>{throw new Error('offline');},()=>['b']); input('[data-catalog-search]','kv'); click('[data-module-filter="inference"]'); click('[data-saved-filter]'); await flush(); assert.deepEqual(visibleCards(),['b']); assert.equal(q('[data-result-count]').textContent,'1');
});

test("收藏：拒绝访问localStorage时内存收藏仍可筛选", async (t) => {
  await boot(t,{storage:'denied'}); click('[data-bookmark="b"]'); click('[data-saved-filter]'); await flush(); assert.equal(q('[data-bookmark="b"]').getAttribute('aria-pressed'),'true'); assert.deepEqual(visibleCards(),['b']); click('[data-bookmark="b"]'); await flush(); assert.equal(q('[data-bookmark="b"]').getAttribute('aria-pressed'),'false'); assert.deepEqual(visibleCards(),[]); assert.match(q('.markdown').textContent||'',/中文正文/);
});

test("收藏：写入失败仍更新按钮和本次浏览状态", async (t) => {
  let writes=0; await boot(t,{storage:{getItem:()=>null,setItem:()=>{writes++;throw new Error('quota');}}}); click('[data-bookmark="b"]'); await flush(); assert.equal(writes,1); assert.equal(q('[data-bookmark="b"]').getAttribute('aria-pressed'),'true'); assert.match(q('#toast').textContent||'',/本次浏览有效/);
});

test("主题：存储不可用仍能连续切换明暗状态", async (t) => {
  await boot(t,{storage:'denied'}); click('[data-theme-toggle]'); assert.equal(document.documentElement.dataset.theme,'dark'); click('[data-theme-toggle]'); assert.equal(document.documentElement.dataset.theme,'light'); assert.match(q('.markdown').textContent||'',/中文正文/);
});

test("语言：双向切换文案placeholder且保留中文正文提示", async (t) => {
  await boot(t,{storage:'denied'}); const original=q('.markdown').textContent; click('[data-language-toggle]'); assert.equal(document.documentElement.lang,'en'); assert.equal(q('[data-language-toggle]').textContent,'中文'); assert.equal(q('#label').textContent,'All topics'); assert.equal(q<HTMLInputElement>('#global-search').placeholder,'Search topics, equations, tools…'); assert.equal(q<HTMLInputElement>('[data-catalog-search]').placeholder,'Search topics, ideas, or technical keywords…'); assert.equal(q('.markdown').textContent,original); assert.match(q('.language-note').textContent||'',/written in Chinese/); click('[data-language-toggle]'); assert.equal(document.documentElement.lang,'zh-CN'); assert.equal(q('#label').textContent,'全部主题'); assert.equal(q<HTMLInputElement>('#global-search').placeholder,'搜索主题、公式、工具…');
});

test("语言：已有English偏好在首次初始化生效", async (t) => {
  await boot(t,{language:'en'}); assert.equal(document.documentElement.lang,'en'); assert.equal(q<HTMLInputElement>('[data-source-search]').placeholder,'Filter sources by title or scope…'); click('[data-open-search]'); input('#global-search','KV Cache'); await flush(); assert.match(q('.search-result small').textContent||'',/Inference/);
});

test("来源：NFKC大小写和多词AND同时生效", async (t) => {
  await boot(t); input('[data-source-search]','LIBRARY ｌａｎｇｇｒａｐｈ'); assert.deepEqual(visibleSources(),['both']); assert.equal(q('[data-source-count]').textContent,'1'); assert.equal(q<HTMLElement>('[data-source-empty]').hidden,true);
});

test("来源：零结果和清空恢复计数", async (t) => {
  await boot(t); input('[data-source-search]','no-match'); assert.deepEqual(visibleSources(),[]); assert.equal(q('[data-source-count]').textContent,'0'); assert.equal(q<HTMLElement>('[data-source-empty]').hidden,false); input('[data-source-search]',' \t '); assert.equal(visibleSources().length,3); assert.equal(q('[data-source-count]').textContent,'3'); assert.equal(q<HTMLElement>('[data-source-empty]').hidden,true);
});

test("复制：异步成功后反馈并最终恢复按钮文字", async (t) => {
  const copied:string[]=[]; const pending=deferred<void>(); await boot(t,{modules:['reader'],clipboard:async text=>{copied.push(text);await pending.promise;}}); click('.copy-code'); assert.deepEqual(copied,['const answer = 42;\n']); assert.equal(q('.copy-code').textContent,'复制'); pending.resolve(); await flush(); assert.equal(q('.copy-code').textContent,'已复制'); t.mock.timers.runAll(); assert.equal(q('.copy-code').textContent,'复制');
});

test("复制：失败给出手动复制反馈且不影响正文", async (t) => {
  await boot(t,{modules:['reader'],clipboard:async()=>{throw new Error('denied');},htmlLanguage:'en'}); click('.copy-code'); await flush(); assert.equal(q('.copy-code').textContent,'Select to copy'); assert.match(q('.markdown').textContent||'',/中文正文/);
});

test("复制：语言变化事件更新操作文字", async (t) => {
  await boot(t,{modules:['site','reader']}); assert.equal(q('.copy-code').textContent,'复制'); click('[data-language-toggle]'); assert.equal(q('.copy-code').textContent,'Copy'); click('[data-language-toggle]'); assert.equal(q('.copy-code').textContent,'复制');
});

test("目录高亮：观察器只激活对应中文锚点", async (t) => {
  const env=await boot(t,{modules:['reader']}); const observer=env.observers.find(o=>o.targets.size===2)!; assert.ok(observer); observer.fire(q('#原理')); assert.ok(q('#toc-first').classList.contains('active')); assert.equal(q('#toc-second').classList.contains('active'),false); observer.fire(q('#实验')); assert.equal(q('#toc-first').classList.contains('active'),false); assert.ok(q('#toc-second').classList.contains('active'));
});

test("移动导航：开关Escape侧栏链接均更新展开状态", async (t) => {
  await boot(t); click('[data-open-menu]'); assert.ok(document.body.classList.contains('mobile-nav-open')); assert.equal(q('[data-open-menu]').getAttribute('aria-expanded'),'true'); document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); assert.equal(document.body.classList.contains('mobile-nav-open'),false); click('[data-open-menu]'); click('.sidebar a'); assert.equal(q('[data-open-menu]').getAttribute('aria-expanded'),'false'); click('[data-open-menu]'); click('[data-close-menu]'); assert.equal(document.body.classList.contains('mobile-nav-open'),false);
});
test("全站初始化：没有目录组件仍能读取收藏并搜索", async (t) => {
  mount(t,{storage:{getItem:key=>key==='llmwiki:bookmarks'?'["b"]':null,setItem(){}}}); q('[data-catalog]').remove(); const button=document.createElement('button');button.dataset.bookmark='b';document.body.append(button); await import(new URL('../src/client/site.ts?unit_case='+ ++moduleSequence,import.meta.url).href); t.mock.timers.enable({apis:['setTimeout']}); assert.equal(button.getAttribute('aria-pressed'),'true'); click('[data-open-search]'); input('#global-search','needle'); await flush(); assert.equal(document.querySelectorAll('.search-result').length,1); assert.equal(q<HTMLDialogElement>('#search-dialog').open,true);
});

test("提示：收藏反馈立即显示并在定时任务后消失", async (t) => {
  await boot(t); click('[data-bookmark="b"]'); assert.ok(q('#toast').classList.contains('visible')); assert.ok((q('#toast').textContent||'').length>0); t.mock.timers.runAll(); assert.equal(q('#toast').classList.contains('visible'),false); assert.equal(q('[data-bookmark="b"]').getAttribute('aria-pressed'),'true');
});

test("弹窗：内部点击保留打开状态而外部点击关闭", async (t) => {
  await boot(t); click('[data-open-search]'); await flush(); const dialog=q<HTMLDialogElement>('#search-dialog'); t.mock.method(dialog,'getBoundingClientRect',()=>({x:10,y:10,left:10,top:10,right:110,bottom:110,width:100,height:100,toJSON(){return {};}})); dialog.dispatchEvent(new MouseEvent('click',{clientX:50,clientY:50,bubbles:true})); assert.equal(dialog.open,true); dialog.dispatchEvent(new MouseEvent('click',{clientX:150,clientY:150,bubbles:true})); assert.equal(dialog.open,false);
});
