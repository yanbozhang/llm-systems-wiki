import test, { type TestContext } from 'node:test';
import assert from 'node:assert/strict';
import { Window } from 'happy-dom';
import { mountDiagrams } from '../src/client/diagrams';
import { diagramTheme, fitDiagram, readableFlowchart } from '../src/lib/diagram-theme';

function mount(context: TestContext, markup = '<pre data-diagram data-diagram-title="任务闭环">flowchart LR\nA--&gt;B</pre>') {
  const window = new Window({ url: 'https://example.org/llm-systems-wiki/', settings: { enableImageFileLoading: false, disableJavaScriptEvaluation: true } });
  window.document.body.innerHTML = `<article>${markup}</article>`;
  window.document.documentElement.lang = 'zh-CN';
  const descriptors = new Map<string, PropertyDescriptor | undefined>();
  for (const [key, value] of Object.entries({
    window, document: window.document, XMLSerializer: window.XMLSerializer,
  })) {
    descriptors.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { value, configurable: true, writable: true });
  }
  delete (window as unknown as Record<string, unknown>).IntersectionObserver;
  context.after(() => {
    for (const [key, descriptor] of descriptors) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
    window.happyDOM.abort();
  });
  return { window, article: window.document.querySelector('article')! as unknown as HTMLElement };
}

const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 240"><text x="20" y="30">可读标签</text></svg>';

test('图示保持浅色实底与至少 80% 的默认可读字号', () => {
  assert.equal(diagramTheme.securityLevel, 'strict');
  assert.equal(diagramTheme.htmlLabels, false);
  assert.equal(fitDiagram(1200, 350), 0.8);
  assert.equal(fitDiagram(1200, 350, false), 350 / 1200);
  assert.equal(fitDiagram(200, 350), 1);
  assert.equal(fitDiagram(Number.NaN, 350), 1);
});

test('长横向流程只调整全局阅读方向，不改节点关系或原始源码', () => {
  const source = 'flowchart LR\nA["输入"] --> B["输出"]';
  assert.equal(readableFlowchart(source, 1500, 100), 'flowchart TB\nA["输入"] --> B["输出"]');
  assert.equal(readableFlowchart(source, 900, 100), source);
  assert.equal(readableFlowchart(source, 1500, 600), source);
  assert.equal(readableFlowchart('sequenceDiagram\nA->>B: LR', 1500, 100), 'sequenceDiagram\nA->>B: LR');
});

test('真实客户端：顺序绘图、一次初始化、缩放、源码及下载', async context => {
  const { article } = mount(context, '<pre data-diagram data-diagram-title="任务闭环">flowchart LR\nA--&gt;B</pre><pre data-diagram>B--&gt;C</pre>');
  let active = 0;
  let initialized = 0;
  const rendered: string[] = [];
  const mounted = mountDiagrams(article, async () => ({
    initialize: () => { initialized++; },
    render: async (_, source) => {
      assert.equal(active++, 0);
      rendered.push(source);
      await Promise.resolve();
      active--;
      return { svg, diagramType: 'flowchart-v2' };
    },
  }));
  await mounted.settled();
  assert.equal(initialized, 1);
  assert.equal(rendered.length, 2);
  assert.equal(article.querySelectorAll('[data-diagram-state="ready"]').length, 2);
  const drawing = article.querySelector<SVGElement>('.diagram-drawing')!;
  assert.equal(drawing.getAttribute('aria-label'), '任务闭环');
  assert.equal(drawing.style.width, '640px');
  article.querySelector<HTMLButtonElement>('[data-diagram-action="in"]')!.click();
  assert.equal(drawing.style.width, '800px');
  article.querySelector<HTMLButtonElement>('[data-diagram-action="reset"]')!.click();
  assert.equal(article.querySelector('output')!.textContent, '100%');
  assert.equal(article.querySelector('.diagram-source pre')!.textContent, 'flowchart LR\nA-->B');
  assert.match(article.querySelector<HTMLAnchorElement>('.diagram-download')!.href, /^blob:/);
});

test('一个图失败不阻塞后续图，保留可访问源码并清除 busy 状态', async context => {
  const { article } = mount(context, '<pre data-diagram>broken</pre><pre data-diagram>valid</pre>');
  const mounted = mountDiagrams(article, async () => ({
    initialize: () => {},
    render: async (_, source) => {
      if (source === 'broken') throw new Error('Invalid syntax');
      return { svg, diagramType: 'flowchart-v2' };
    },
  }));
  await mounted.settled();
  assert.equal(article.querySelectorAll('[data-diagram-state="error"]').length, 1);
  assert.equal(article.querySelectorAll('[data-diagram-state="ready"]').length, 1);
  assert.equal(article.querySelector<HTMLDetailsElement>('details')!.open, true);
  assert.equal(article.querySelector('.diagram-canvas')!.getAttribute('aria-busy'), 'false');
});

test('静态 SVG 使用相同控件，折叠权威源不会重复渲染', async context => {
  const { article, window } = mount(context, '<p><img src="/llm-systems-wiki/architecture-harness.svg" alt="运行系统"></p><details><summary>权威源</summary><pre data-diagram>flowchart LR\nA--&gt;B</pre></details>');
  let loads = 0;
  mountDiagrams(article, async () => {
    loads++;
    throw new Error('Should not render source-only blocks');
  });
  assert.equal(loads, 0);
  assert.equal(article.querySelectorAll('.diagram-frame').length, 1);
  const image = article.querySelector('img')!;
  Object.defineProperty(image, 'naturalWidth', { value: 1120, configurable: true });
  image.dispatchEvent(new window.Event('load') as unknown as Event);
  assert.equal(article.querySelector('.diagram-frame')!.getAttribute('data-diagram-state'), 'ready');
  assert.equal(article.querySelector('.diagram-title')!.textContent, '运行系统');
  assert.ok(article.querySelector('details [data-diagram]'));
});

test('切换语言更新所有图示操作，不翻译权威图中文字', async context => {
  const { article, window } = mount(context);
  const mounted = mountDiagrams(article, async () => ({
    initialize: () => {},
    render: async () => ({ svg, diagramType: 'flowchart-v2' }),
  }));
  await mounted.settled();
  window.document.documentElement.lang = 'en';
  window.document.dispatchEvent(new window.Event('language-change'));
  assert.equal(article.querySelector('[data-diagram-action="in"]')!.getAttribute('aria-label'), 'Zoom in');
  assert.match(article.querySelector('summary')!.textContent!, /editable Mermaid source/);
  assert.equal(article.querySelector('.diagram-title')!.textContent, '任务闭环');
});
