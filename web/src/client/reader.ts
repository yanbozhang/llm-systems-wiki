import { mountDiagrams } from './diagrams';

const article=document.querySelector<HTMLElement>('.markdown');
if(article){
  document.querySelectorAll<HTMLButtonElement>('.copy-code').forEach(button=>button.addEventListener('click',async()=>{
    const code=button.closest('.code-block')?.querySelector('code')?.textContent||'';
    try{await navigator.clipboard.writeText(code);button.textContent=document.documentElement.lang==='en'?'Copied':'已复制';setTimeout(()=>button.textContent=document.documentElement.lang==='en'?'Copy':'复制',1800);}
    catch{button.textContent=document.documentElement.lang==='en'?'Select to copy':'请选中复制';}
  }));
  const translateCopy=()=>document.querySelectorAll<HTMLButtonElement>('.copy-code').forEach(button=>button.textContent=document.documentElement.lang==='en'?'Copy':'复制');
  document.addEventListener('language-change',translateCopy);translateCopy();
  const headings=[...article.querySelectorAll<HTMLElement>('h2[id],h3[id]')];
  const links=[...document.querySelectorAll<HTMLAnchorElement>('.article-toc .toc-link')];
  const setActive=(id:string)=>links.forEach(link=>link.classList.toggle('active',decodeURIComponent(link.hash.slice(1))===id));
  if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{entries.filter(e=>e.isIntersecting).forEach(e=>setActive(e.target.id));},{rootMargin:'-85px 0px -65% 0px'});headings.forEach(h=>observer.observe(h));}
  mountDiagrams(article);
}
