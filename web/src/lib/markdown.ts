import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import rehypeKatex from 'rehype-katex';
import rehypeStringify from 'rehype-stringify';
import { visit } from 'unist-util-visit';
import { toString } from 'hast-util-to-string';
import GithubSlugger from 'github-slugger';
import { createHighlighter } from 'shiki';
import type { Element, Root } from 'hast';
import { resolveLink } from './navigation';

export interface Heading { id: string; text: string; level: number }
const highlighter = createHighlighter({themes:['github-light','github-dark'],langs:['python','bash','json','typescript','javascript','text']});

/** 原始HTML先清洗，之后才加入可信的数学与代码渲染结果。 */
export async function renderMarkdown(markdown: string, file: string, routes: Record<string,string> = {}) {
  const headings: Heading[]=[];
  const slugger = new GithubSlugger();
  const colorizer=await highlighter;
  const schema: typeof defaultSchema = {...defaultSchema, attributes: {...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code || []).filter(rule => typeof rule === 'string' ? rule !== 'className' : rule[0] !== 'className'), ['className', /^language-/, 'math-inline', 'math-display']]
  }};
  function decorate() {
    return (tree: Root) => {
      visit(tree,'element',(node:Element)=>{
        if (/^h[1-6]$/.test(node.tagName)) {
          const text=toString(node), id=slugger.slug(text);
          node.properties.id=id;
          if (node.tagName==='h2'||node.tagName==='h3') headings.push({id,text,level:Number(node.tagName[1])});
        }
        if (node.tagName==='a' && typeof node.properties.href==='string') {
          node.properties.href=resolveLink(node.properties.href,file,routes);
          if (/^https?:/.test(String(node.properties.href))) node.properties.rel=['noopener','noreferrer'];
        }
        if (node.tagName==='img' && typeof node.properties.src==='string') {
          node.properties.src=resolveLink(node.properties.src,file,routes); node.properties.loading='lazy';
        }
        if (node.tagName!=='pre') return;
        const code=node.children[0];
        if (code?.type!=='element'||code.tagName!=='code') return;
        const classes=Array.isArray(code.properties.className)?code.properties.className:[];
        if (classes.includes('math-display') || classes.includes('math-inline')) return;
        const language=String(classes.find(c=>String(c).startsWith('language-'))||'language-text').slice(9);
        const value=toString(code);
        if(language==='mermaid') {
          node.properties.className=['mermaid-source'];
          node.properties['data-diagram']='';
          return;
        }
        const lang=colorizer.getLoadedLanguages().includes(language)?language:'text';
        const html=colorizer.codeToHtml(value,{lang,themes:{light:'github-light',dark:'github-dark'},defaultColor:false});
        // raw节点只来自本地高亮器，原始HTML已在上游清洗。
        Object.assign(node,{type:'raw',value:`<div class="code-block" data-language="${lang}">${html}<button class="copy-code" type="button" aria-label="复制代码" title="复制代码">复制</button></div>`});
      });
    };
  }
  const output=await unified().use(remarkParse).use(remarkGfm).use(remarkMath)
    .use(remarkRehype,{allowDangerousHtml:true}).use(rehypeRaw).use(rehypeSanitize,schema)
    .use(decorate).use(rehypeKatex,{strict:'ignore'})
    .use(rehypeStringify,{allowDangerousHtml:true})
    .process(markdown.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/,'').trim().replace(/^# [^\n]+\n?/,''));
  return {html:String(output),headings};
}
