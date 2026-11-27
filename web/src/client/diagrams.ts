import { diagramTheme, fitDiagram, readableFlowchart } from '../lib/diagram-theme';

type Renderer = Pick<typeof import('mermaid')['default'], 'initialize' | 'render'>;
type Loader = () => Promise<Renderer>;
const defaultLoader: Loader = async () => (await import('mermaid')).default;
let sequence = 0;

export function mountDiagrams(article: HTMLElement, loadRenderer: Loader = defaultLoader) {
  let queue = Promise.resolve();
  let renderer: Promise<Renderer> | undefined;
  const pending = new Map<Element, () => Promise<void>>();
  const originals = [...article.querySelectorAll<HTMLElement>('[data-diagram], img')].filter(element => {
    if (element.matches('[data-diagram]')) return !element.closest('details');
    return /\.svg(?:[?#]|$)/i.test(element.getAttribute('src') || '');
  });

  for (const original of originals) {
    const image = original.tagName === 'IMG' ? original as HTMLImageElement : undefined;
    const source = image ? '' : original.textContent || '';
    const title = image?.alt || original.dataset.diagramTitle || '结构图';
    const identity = `knowledge-diagram-${sequence++}`;
    const frame = document.createElement('figure');
    frame.className = 'diagram-frame';
    frame.dataset.diagramState = 'waiting';
    const header = document.createElement('figcaption');
    header.className = 'diagram-label';
    const caption = document.createElement('span');
    caption.className = 'diagram-title';
    caption.id = `${identity}-caption`;
    caption.textContent = title;
    const toolbar = document.createElement('div');
    toolbar.className = 'diagram-toolbar';
    const canvas = document.createElement('div');
    canvas.className = 'diagram-canvas';
    canvas.tabIndex = 0;
    canvas.setAttribute('role', 'region');
    canvas.setAttribute('aria-labelledby', caption.id);
    canvas.setAttribute('aria-busy', 'true');
    const hint = document.createElement('p');
    hint.className = 'diagram-hint';
    const status = document.createElement('output');
    status.className = 'diagram-scale';
    status.setAttribute('aria-live', 'polite');
    const controls = new Map<string, HTMLButtonElement>();
    for (const action of ['out', 'in', 'fit', 'reset', 'expand']) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'diagram-control';
      button.dataset.diagramAction = action;
      button.disabled = true;
      controls.set(action, button);
      toolbar.append(button);
    }
    const download = document.createElement('a');
    download.className = 'diagram-control diagram-download';
    download.hidden = true;
    download.download = `${identity}.svg`;
    toolbar.append(status, download);
    header.append(caption, toolbar);
    frame.append(header, canvas, hint);
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    details.className = 'diagram-source';
    if (!image) {
      const code = document.createElement('pre');
      code.textContent = source;
      details.append(summary, code);
      frame.append(details);
    }
    if (image && original.parentElement?.tagName === 'P' && original.parentElement.childNodes.length === 1) {
      original.parentElement.replaceWith(frame);
    } else {
      original.replaceWith(frame);
    }
    const placeholder = document.createComment('diagram position');
    frame.before(placeholder);
    const dialog = document.createElement('dialog');
    dialog.className = 'diagram-dialog';
    dialog.setAttribute('aria-labelledby', caption.id);
    let drawing: SVGElement | HTMLImageElement | undefined;
    let intrinsicWidth = 800;
    let scale = 1;
    let automatic = true;
    let fullFit = false;
    let expanded = false;
    let error = false;
    let objectUrl: string | undefined;
    const setScale = (next: number, manual = true) => {
      if (!drawing) return;
      scale = Math.max(0.1, Math.min(3, next));
      if (manual) automatic = false;
      drawing.style.width = `${Math.round(intrinsicWidth * scale)}px`;
      drawing.style.maxWidth = 'none';
      status.textContent = `${Math.round(scale * 100)}%`;
      controls.get('out')!.disabled = scale <= 0.1;
      controls.get('in')!.disabled = scale >= 3;
    };
    const fit = () => {
      if (automatic) setScale(fitDiagram(intrinsicWidth, canvas.clientWidth - 32, !fullFit), false);
    };
    const translate = () => {
      const english = document.documentElement.lang === 'en';
      const labels = {
        out: english ? 'Zoom out' : '缩小',
        in: english ? 'Zoom in' : '放大',
        fit: english ? 'Fit' : '适应宽度',
        reset: english ? '100%' : '原始比例',
        expand: expanded ? (english ? 'Close ×' : '关闭 ×') : (english ? 'Expand ↗' : '全屏查看 ↗'),
      };
      controls.forEach((button, action) => {
        const label = labels[action as keyof typeof labels];
        button.textContent = action === 'in' ? '+' : action === 'out' ? '−' : label;
        button.setAttribute('aria-label', label);
        button.title = label;
      });
      controls.get('expand')!.setAttribute('aria-expanded', String(expanded));
      summary.textContent = english ? 'View editable Mermaid source' : '查看可编辑 Mermaid 源码';
      download.textContent = english ? 'SVG ↓' : '下载 SVG ↓';
      hint.textContent = error
        ? (english ? 'The diagram could not load; use the original or source below.' : '图示加载失败，请查看原图或下方源码。')
        : frame.dataset.diagramLayout === 'vertical'
          ? (english ? 'Long flow arranged vertically · Relationships and source are unchanged · Use + / − or expand' : '长流程已纵向排版，节点关系与源码不变 · 支持缩放与全屏')
          : (english ? 'Scroll to inspect · Use + / − or expand · Diagram labels remain in Chinese' : '可横向滚动查看 · 支持缩放与全屏 · 图中文字以原文为准');
      toolbar.setAttribute('aria-label', english ? 'Diagram controls' : '图示操作');
      toolbar.setAttribute('role', 'group');
    };
    const close = () => {
      expanded = false;
      placeholder.after(frame);
      dialog.remove();
      translate();
      fit();
      controls.get('expand')!.focus();
    };
    dialog.addEventListener('close', close);
    controls.get('expand')!.addEventListener('click', () => {
      if (expanded) {
        dialog.close();
        return;
      }
      document.body.append(dialog);
      dialog.append(frame);
      expanded = true;
      translate();
      dialog.showModal();
      fit();
      controls.get('expand')!.focus();
    });
    controls.get('in')!.addEventListener('click', () => setScale(scale + 0.2));
    controls.get('out')!.addEventListener('click', () => setScale(scale - 0.2));
    controls.get('reset')!.addEventListener('click', () => setScale(1));
    controls.get('fit')!.addEventListener('click', () => {
      automatic = true;
      fullFit = true;
      fit();
    });
    const ready = (element: SVGElement | HTMLImageElement, width: number) => {
      drawing = element;
      intrinsicWidth = Number.isFinite(width) && width > 0 ? width : 800;
      element.classList.add('diagram-drawing');
      canvas.replaceChildren(element);
      canvas.setAttribute('aria-busy', 'false');
      frame.dataset.diagramState = 'ready';
      controls.forEach(button => { button.disabled = false; });
      fit();
    };
    const fail = () => {
      error = true;
      frame.dataset.diagramState = 'error';
      canvas.setAttribute('aria-busy', 'false');
      if (!image) {
        canvas.replaceChildren();
        details.open = true;
      }
      translate();
    };
    if (image) {
      const originalLink = document.createElement('a');
      originalLink.href = image.src;
      originalLink.textContent = image.alt || title;
      originalLink.className = 'diagram-original';
      originalLink.target = '_blank';
      originalLink.rel = 'noopener noreferrer';
      frame.append(originalLink);
      image.addEventListener('load', () => ready(image, image.naturalWidth), { once: true });
      image.addEventListener('error', fail, { once: true });
      canvas.append(image);
      download.href = image.src;
      download.hidden = false;
      if (image.complete) {
        if (image.naturalWidth) ready(image, image.naturalWidth);
        else fail();
      }
    } else {
      const waiting = document.createElement('pre');
      waiting.className = 'diagram-placeholder';
      waiting.textContent = source;
      canvas.append(waiting);
      pending.set(frame, async () => {
        try {
          renderer ??= loadRenderer().then(instance => {
            instance.initialize(diagramTheme);
            return instance;
          });
          const instance = await renderer;
          let { svg } = await instance.render(identity, source);
          const container = document.createElement('div');
          container.innerHTML = svg;
          const dimensions = container.querySelector('svg')?.getAttribute('viewBox')?.trim().split(/[\s,]+/).map(Number);
          const adapted = readableFlowchart(source, dimensions?.[2] || 0, dimensions?.[3] || 1);
          if (adapted !== source) {
            ({ svg } = await instance.render(identity, adapted));
            container.innerHTML = svg;
            frame.dataset.diagramLayout = 'vertical';
            translate();
          }
          const element = container.querySelector('svg');
          if (!element) throw new Error('Missing SVG');
          element.setAttribute('role', 'img');
          element.setAttribute('aria-label', title);
          element.style.backgroundColor = '#ffffff';
          const exported = new XMLSerializer().serializeToString(element);
          const width = Number(element.getAttribute('viewBox')?.trim().split(/[\s,]+/)[2]);
          ready(element, width);
          objectUrl = URL.createObjectURL(new Blob([exported], { type: 'image/svg+xml;charset=utf-8' }));
          download.href = objectUrl;
          download.hidden = false;
        } catch {
          renderer = undefined;
          document.getElementById(`d${identity}`)?.remove();
          fail();
        }
      });
    }
    document.addEventListener('language-change', translate);
    window.addEventListener('resize', fit);
    window.addEventListener('pagehide', event => {
      if (!event.persisted && objectUrl) URL.revokeObjectURL(objectUrl);
    }, { once: true });
    translate();
  }

  const schedule = (target: Element) => {
    const draw = pending.get(target);
    if (!draw) return;
    pending.delete(target);
    queue = queue.then(draw);
  };
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          schedule(entry.target);
        }
      }
    }, { rootMargin: '500px' });
    pending.forEach((_, target) => observer.observe(target));
  } else {
    [...pending.keys()].forEach(schedule);
  }
  return { settled: () => queue };
}
