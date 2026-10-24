import {readBookmarks,saveBookmarks,toggleBookmark,searchTopics,sitePath,type SearchItem} from '../lib/navigation';
import {bindCatalog} from './catalog';
const $=<T extends HTMLElement>(selector:string)=>document.querySelector<T>(selector);
let language:'zh'|'en'='zh';
function storage():Storage|undefined{try{return window.localStorage;}catch{return undefined;}}
try{if(storage()?.getItem('llmwiki:language')==='en')language='en';}catch{}
function applyLanguage(){
  document.documentElement.lang=language==='zh'?'zh-CN':'en';
  document.querySelectorAll<HTMLElement>('[data-zh][data-en]').forEach(el=>{el.textContent=(language==='zh'?el.dataset.zh:el.dataset.en)!.replace(/\\n/g,'\n');});
  document.querySelectorAll<HTMLInputElement>('[data-placeholder-zh]').forEach(el=>{el.placeholder=(language==='zh'?el.dataset.placeholderZh:el.dataset.placeholderEn)!;});
  const button=$('[data-language-toggle]');if(button)button.textContent=language==='zh'?'EN':'中文';
  document.dispatchEvent(new Event('language-change'));
}
applyLanguage();
$('[data-language-toggle]')?.addEventListener('click',()=>{language=language==='zh'?'en':'zh';try{storage()?.setItem('llmwiki:language',language);}catch{}applyLanguage();});
$('[data-theme-toggle]')?.addEventListener('click',()=>{
  const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';
  document.documentElement.dataset.theme=theme;try{storage()?.setItem('llmwiki:theme',theme);}catch{}
});
function menu(open:boolean){document.body.classList.toggle('mobile-nav-open',open);$('[data-open-menu]')?.setAttribute('aria-expanded',String(open));}
$('[data-open-menu]')?.addEventListener('click',()=>menu(!document.body.classList.contains('mobile-nav-open')));
$('[data-close-menu]')?.addEventListener('click',()=>menu(false));
document.querySelectorAll('.sidebar a').forEach(a=>a.addEventListener('click',()=>menu(false)));
let toastTimer:ReturnType<typeof setTimeout>;
export function toast(text:string){const el=$('#toast');if(!el)return;clearTimeout(toastTimer);el.textContent=text;el.classList.add('visible');toastTimer=setTimeout(()=>el.classList.remove('visible'),2400);}
let bookmarks=readBookmarks(storage());
function syncBookmarks(){document.querySelectorAll<HTMLElement>('[data-bookmark]').forEach(button=>{const saved=bookmarks.includes(button.dataset.bookmark!);button.setAttribute('aria-pressed',String(saved));button.title=saved?(language==='zh'?'取消收藏':'Remove saved topic'):(language==='zh'?'收藏文章':'Save topic');});}
syncBookmarks();
document.querySelectorAll<HTMLElement>('[data-bookmark]').forEach(button=>button.addEventListener('click',()=>{
  const id=button.dataset.bookmark!;bookmarks=toggleBookmark(bookmarks,id);const persisted=saveBookmarks(storage(),bookmarks);
  syncBookmarks();document.dispatchEvent(new Event('bookmarks-change'));
  const saved=bookmarks.includes(id);
  toast(language==='zh'?(saved?(persisted?'已加入收藏':'已收藏，本次浏览有效'):'已取消收藏'):(saved?'Saved for later':'Removed from saved topics'));
}));
document.addEventListener('language-change',syncBookmarks);
let indexPromise:Promise<SearchItem[]>|undefined;
function loadIndex(){
  return indexPromise??=(fetch(sitePath('/search-index.json')).then(r=>{if(!r.ok)throw new Error('Search unavailable');return r.json();}).then((value:unknown)=>{if(!Array.isArray(value))throw new Error('Invalid search index');return value as SearchItem[];}).catch(error=>{indexPromise=undefined;throw error;}));
}
bindCatalog(loadIndex,()=>bookmarks);
const dialog=$<HTMLDialogElement>('#search-dialog');
const search=$<HTMLInputElement>('#global-search');
const results=$('#search-results');
let searchRevision=0;
function message(text:string){if(!results)return;results.replaceChildren();const p=document.createElement('p');p.className='search-result-empty';p.textContent=text;results.append(p);}
async function displaySearch(){
  if(!search||!results)return;const revision=++searchRevision;
  try{
    const rows=searchTopics(await loadIndex(),search.value).slice(0,18);
    if(revision!==searchRevision)return;
    results.replaceChildren();
    if(!rows.length){message(language==='zh'?'没有找到相关主题，试试其他关键词。':'No topics found. Try a different keyword.');return;}
    rows.forEach(row=>{const link=document.createElement('a');link.className='search-result';link.href=row.url;const title=document.createElement('strong');title.textContent=row.title;const detail=document.createElement('small');detail.textContent=`${language==='zh'?row.moduleTitle:row.moduleEnglish} · ${row.description}`;link.append(title,detail);results.append(link);});
  }catch{if(revision===searchRevision)message(language==='zh'?'搜索暂时不可用，可以继续浏览全部主题。':'Search is unavailable. You can still browse all topics.');}
}
function openSearch(){if(!dialog||!search)return;if(!dialog.open)dialog.showModal();message(language==='zh'?'正在打开知识索引…':'Opening the knowledge index…');search.focus();void displaySearch();}
document.querySelectorAll('[data-open-search]').forEach(button=>button.addEventListener('click',openSearch));
$('[data-close-search]')?.addEventListener('click',()=>dialog?.close());
dialog?.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}});
search?.addEventListener('input',()=>{void displaySearch();});
document.addEventListener('keydown',event=>{
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();openSearch();}
  if(event.key==='Escape')menu(false);
});
const sourceSearch=$<HTMLInputElement>('[data-source-search]');
sourceSearch?.addEventListener('input',()=>{
  const terms=sourceSearch.value.normalize('NFKC').toLowerCase().trim().split(/\s+/).filter(Boolean);let count=0;
  document.querySelectorAll<HTMLElement>('[data-source-row]').forEach(row=>{const text=(row.textContent||'').normalize('NFKC').toLowerCase();row.hidden=!terms.every(t=>text.includes(t));if(!row.hidden)count++;});
  const total=$('[data-source-count]');if(total)total.textContent=String(count);
  const empty=$('[data-source-empty]');if(empty)empty.hidden=count!==0;
});
