import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { sitePath, type SearchItem } from './navigation';
export const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const read = (path: string) => readFileSync(resolve(ROOT, path), 'utf8');
const json = <T>(path: string) => JSON.parse(read(path)) as T;
export interface Topic { id: string; title: string; module: string; page: string; example: string; learning_objectives: string[]; unit_ids: string[]; last_checked: string; }
export interface Unit { id: string; topic: string; title: string; function: string; source_ids: string[]; }
export interface Module { id: string; title: string; page: string; english: string; subtitle: string; color: string; number: string; }
export interface Document { id: string; title: string; english: string; page: string; url: string; description: string; steps?: string; level?: string; }
export const moduleInfo: Record<string, [string, string, string]> = {
  network: ['Architecture', '理解 token 到智能的计算过程', 'blue'],
  training: ['Training', '从数据与目标，走向模型能力', 'amber'],
  inference: ['Inference', '在内存、延迟与吞吐间做取舍', 'green'],
  harness: ['Agent Harness', '把模型连接成可靠的执行系统', 'violet'],
  knowledge: ['Knowledge & RAG', '让回答有依据，让知识可追溯', 'cyan'],
  agents: ['Applied Agents', '从工具调用走到真实任务闭环', 'orange'],
  benchmark: ['Evaluation', '理解分数背后的协议与边界', 'rose']
};
export const modules: Module[] = json<Omit<Module, 'english' | 'subtitle' | 'color' | 'number'>[]>('knowledge/modules.json').map((m, i) => ({...m, english:moduleInfo[m.id][0], subtitle:moduleInfo[m.id][1], color:moduleInfo[m.id][2], number:String(i+1).padStart(2,'0')}));
export const topics = json<Topic[]>('knowledge/topics.json');
export const units = json<Unit[]>('knowledge/units.json');
export const capabilities = json<{ id: string; module: string; outcome: string; level: string; deliverable: string; unit_ids: string[] }[]>('knowledge/capabilities.json');
export const sources = json<{id:string; title:string; url:string; kind?:string; native_version?:string; reading_scope:string}[]>('sources/manifest/sources.json');
export const paths: Document[] = [
  {id:'foundations',title:'基础入门',english:'The foundations',page:'wiki/paths/基础入门路径.md',description:'从 Transformer 出发，建立大模型的完整认知。',steps:'概念 → 推导 → 实现',level:'从这里开始',url:'/paths/foundations/'},
  {id:'systems',title:'系统工程',english:'Systems engineering',page:'wiki/paths/系统工程路径.md',description:'把缓存、调度和负载连接成可以测量的系统。',steps:'内存 → 调度 → 性能',level:'工程进阶',url:'/paths/systems/'},
  {id:'agents',title:'Agent 开发',english:'Building agents',page:'wiki/paths/Agent开发路径.md',description:'从状态、工具与记忆，构建可靠的任务循环。',steps:'状态 → 工具 → 闭环',level:'应用实践',url:'/paths/agents/'},
  {id:'benchmark',title:'Benchmark',english:'Evaluation practice',page:'wiki/paths/Benchmark学习路径.md',description:'让每个分数，都有可信的协议和解释。',steps:'协议 → 统计 → 归因',level:'评测方法',url:'/paths/benchmark/'},
  {id:'gui',title:'GUI 智能体',english:'GUI agents',page:'wiki/paths/GUI智能体实践路径.md',description:'拆解 Mobile-Agent、AppAgent 与 UI-TARS。',steps:'感知 → 动作 → 验收',level:'专项深入',url:'/paths/gui/'},
  {id:'coding',title:'AI 编程智能体',english:'Coding agents',page:'wiki/paths/AI编程智能体实践路径.md',description:'阅读 Codex、Claude Code 与编程工具的实现。',steps:'上下文 → 编辑 → 反馈',level:'专项深入',url:'/paths/coding/'}
];
export const guides: Document[] = [
  {id:'map',title:'能力地图',english:'Capability map',page:'docs/能力地图.md',description:'28项能力，连接知识点与可提交的实践成果。',url:'/guides/map/'},
  {id:'resources',title:'学习资源',english:'Learning resources',page:'docs/系统学习资源指南.md',description:'课程、论文、官方文档与源码的系统阅读入口。',url:'/guides/resources/'},
  {id:'frameworks',title:'Agent 方案导读',english:'Agent frameworks',page:'docs/Agent开源方案导读.md',description:'十个代表方案的架构、状态、恢复与开放边界。',url:'/guides/frameworks/'},
  {id:'foundations',title:'共同基础',english:'Prerequisites',page:'docs/共同基础.md',description:'数学、编程与工程基础，支持后续每一次推导。',url:'/guides/foundations/'},
  {id:'projects',title:'跨模块实践',english:'Capstone projects',page:'docs/跨模块实践项目.md',description:'将模型、知识、工具与评价连接为完整项目。',url:'/guides/projects/'},
  {id:'index',title:'全部知识点',english:'Knowledge index',page:'docs/知识点索引.md',description:'逐条定位135个公式、实现与结构图。',url:'/guides/index/'}
];
export const routes: Record<string,string> = Object.fromEntries([
  ...topics.map(t=>[t.page,`/read/${t.id}/`]), ...modules.map(m=>[m.page,`/modules/${m.id}/`]),
  ...paths.map(p=>[p.page,p.url]), ...guides.map(p=>[p.page,p.url]),
  ...readdirSync(resolve(ROOT,'assets'),{withFileTypes:true}).filter(entry=>entry.isFile()).map(entry=>[`assets/${entry.name}`,`/${entry.name}`]),
  ['docs/大模型持续学习知识库.md','/'],['README.md','/'],['sources/来源索引.md','/sources/']
]);
export function readDocument(path:string):string {
  return read(path).replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, '').replace(/\r?\n---\r?\n\r?\n\[返回模块\][\s\S]*$/, '').trim();
}
export function topicDescription(topic:Topic):string { return topic.learning_objectives.slice(0,2).join('；'); }
export function buildSearchIndex(): SearchItem[] {
  return topics.map(t=>{
    const mod=modules.find(m=>m.id===t.module)!;
    const body=readDocument(t.page).replace(/```[\s\S]*?```/g,' ').replace(/\$\$[\s\S]*?\$\$/g,' ').replace(/https?:\/\/\S+/g,' ');
    return {id:t.id,title:t.title,module:t.module,moduleTitle:mod.title,moduleEnglish:mod.english,
      unitTitles:units.filter(u=>u.topic===t.id).map(u=>u.title),objectives:t.learning_objectives,
      text:body,url:sitePath(`/read/${t.id}/`),description:topicDescription(t)};
  });
}
