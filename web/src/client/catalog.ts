import {searchTopics, type SearchItem} from '../lib/navigation';
export function bindCatalog(load:()=>Promise<SearchItem[]>, bookmarks:()=>string[]) {
  const catalog=document.querySelector<HTMLElement>('[data-catalog]');
  if(!catalog)return;
  const input=catalog.querySelector<HTMLInputElement>('[data-catalog-search]')!;
  const cards=[...catalog.querySelectorAll<HTMLElement>('[data-topic-card]')];
  const grid=catalog.querySelector<HTMLElement>('[data-topic-grid]')!;
  let module=catalog.dataset.initialModule||'all',savedOnly=false,request=0;
  const render=async()=>{
    const current=++request;
    try{
      const result=searchTopics(await load(),input.value,module).filter(t=>!savedOnly||bookmarks().includes(t.id));
      if(current!==request)return;
      const ids=new Set(result.map(t=>t.id));
      cards.forEach(card=>{card.hidden=!ids.has(card.dataset.id!);});
      // 在筛选结果内保留搜索相关性顺序。
      const order=new Map(result.map((t,i)=>[t.id,i]));
      cards.forEach(card=>{card.style.order=String(order.get(card.dataset.id!)??999);});
      catalog.querySelector('[data-result-count]')!.textContent=String(result.length);
      catalog.querySelector<HTMLElement>('[data-catalog-empty]')!.hidden=result.length!==0;
    }catch{
      if(current!==request)return;
      // 索引不可达时仍保留服务端生成的内容和基本标题筛选。
      const query=input.value.trim().toLowerCase();let count=0;
      cards.forEach(card=>{card.hidden=!((module==='all'||card.dataset.module===module)&&(!savedOnly||bookmarks().includes(card.dataset.id!))&&(card.textContent||'').toLowerCase().includes(query));if(!card.hidden)count++;});
      catalog.querySelector('[data-result-count]')!.textContent=String(count);
      catalog.querySelector<HTMLElement>('[data-catalog-empty]')!.hidden=count!==0;
    }
  };
  input.addEventListener('input',()=>{void render();});
  catalog.querySelectorAll<HTMLButtonElement>('[data-module-filter]').forEach(button=>button.addEventListener('click',()=>{
    module=button.dataset.moduleFilter!;
    catalog.querySelectorAll<HTMLButtonElement>('[data-module-filter]').forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    void render();
  }));
  const saved=catalog.querySelector<HTMLButtonElement>('[data-saved-filter]')!;
  saved.addEventListener('click',()=>{savedOnly=!savedOnly;saved.setAttribute('aria-pressed',String(savedOnly));void render();});
  catalog.querySelectorAll<HTMLButtonElement>('[data-view]').forEach(button=>button.addEventListener('click',()=>{
    grid.classList.toggle('list-view',button.dataset.view==='list');
    catalog.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  }));
  catalog.querySelector('[data-reset-catalog]')?.addEventListener('click',()=>{
    input.value='';savedOnly=false;saved.setAttribute('aria-pressed','false');module=catalog.dataset.initialModule||'all';
    catalog.querySelectorAll<HTMLElement>('[data-module-filter]').forEach(b=>{const active=b.dataset.moduleFilter===module;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    void render();input.focus();
  });
  document.addEventListener('bookmarks-change',()=>{void render();});
}
