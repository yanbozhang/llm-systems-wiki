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
  // 所有结构图按进入视口顺序渲染；同一时刻只执行一张。
  let queue=Promise.resolve();
  let renderer:Promise<typeof import('mermaid')>|undefined;
  const diagrams=[...article.querySelectorAll<HTMLElement>('[data-diagram]')];
  async function draw(pre:HTMLElement,index:number){
    const source=pre.textContent||'';
    const frame=document.createElement('div');frame.className='diagram-frame';
    const label=document.createElement('div');label.className='diagram-label';label.textContent=document.documentElement.lang==='en'?'IMPLEMENTATION DIAGRAM':'实现结构图';
    const canvas=document.createElement('div');canvas.className='diagram-canvas';
    const waiting=document.createElement('p');waiting.className='diagram-loading';waiting.textContent=document.documentElement.lang==='en'?'Drawing the structure…':'正在绘制结构图…';canvas.append(waiting);
    const details=document.createElement('details');details.className='diagram-source';
    const summary=document.createElement('summary');summary.textContent=document.documentElement.lang==='en'?'View diagram source':'查看图示源码';
    const code=document.createElement('pre');code.textContent=source;details.append(summary,code);frame.append(label,canvas,details);pre.replaceWith(frame);
    try{
      renderer??=import('mermaid');const {default:mermaid}=await renderer;
      mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',fontFamily:'Inter, PingFang SC, Noto Sans CJK SC, sans-serif',flowchart:{htmlLabels:true,useMaxWidth:true}});
      const {svg}=await mermaid.render(`knowledge-diagram-${index}`,source);
      canvas.innerHTML=svg;
    }catch{
      canvas.replaceChildren();const note=document.createElement('p');note.className='diagram-error';note.textContent=document.documentElement.lang==='en'?'The diagram could not load. Its source is available below.':'结构图暂未加载，展开下方源码即可查看完整关系。';canvas.append(note);details.open=true;
    }
  }
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){observer.unobserve(entry.target);const pre=entry.target as HTMLElement;queue=queue.then(()=>draw(pre,diagrams.indexOf(pre)));}});},{rootMargin:'500px'});
    diagrams.forEach(pre=>observer.observe(pre));
  }else{diagrams.forEach((pre,i)=>{queue=queue.then(()=>draw(pre,i));});}
}
