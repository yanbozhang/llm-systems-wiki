export const BASE = '/llm-systems-wiki';
export const REPOSITORY = 'https://github.com/yanbozhang/llm-systems-wiki';

/** 路由仅在入口补一次项目子路径。 */
export function sitePath(path = ''): string {
  const clean = `/${path.replace(/^\/+/, '')}`;
  if (clean === BASE || ['/', '?', '#'].some(boundary => clean.startsWith(`${BASE}${boundary}`))) return clean;
  return `${BASE}${clean}`;
}

/** 将受管Markdown相对引用转成站内路由，其他受管文件回到GitHub。 */
export function resolveLink(href: string, sourceFile: string, routes: Record<string, string>): string {
  const value = href.trim();
  if (!value || value.startsWith('#')) return value || '#';
  if (/^(https?:|mailto:)/i.test(value)) return value;
  if (value.startsWith('//')) return `https:${value}`;
  if (/^[a-z][a-z\d+.-]*:/i.test(value) || /[\x00-\x1f]/.test(value)) return '#';
  const split = value.search(/[?#]/);
  const rawPath = split < 0 ? value : value.slice(0, split);
  const suffix = split < 0 ? '' : value.slice(split);
  let decoded: string;
  try { decoded = decodeURIComponent(rawPath); } catch { return '#'; }
  if (decoded.includes('\\') || /[\x00-\x1f]/.test(decoded)) return '#';
  const parts = rawPath.startsWith('/') ? [] : sourceFile.split('/').slice(0, -1);
  for (const part of decoded.split('/')) {
    if (!part || part === '.') continue;
    if (part === '..') { if (!parts.length) return '#'; parts.pop(); }
    else parts.push(part);
  }
  const file = parts.join('/');
  if (Object.hasOwn(routes, file) && typeof routes[file] === 'string') return `${sitePath(routes[file])}${suffix}`;
  return `${REPOSITORY}/blob/main/${file.split('/').map(encodeURIComponent).join('/')}${suffix}`;
}

export interface SearchItem {
  id: string; title: string; module: string; moduleTitle: string; moduleEnglish: string;
  unitTitles: string[]; objectives: string[]; text: string; url: string; description: string;
}
export const normalize = (value: string) => value.normalize('NFKC').toLocaleLowerCase().trim();

export function searchTopics(items: SearchItem[], query: string, module = 'all'): SearchItem[] {
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  return items.map((item, index) => {
    const title = normalize(`${item.title} ${item.id}`);
    const units = normalize(item.unitTitles.join(' '));
    const objectives = normalize(item.objectives.join(' '));
    const body = normalize(`${title} ${units} ${objectives} ${item.text} ${item.moduleTitle} ${item.moduleEnglish}`);
    const matches = (module === 'all' || item.module === module) && terms.every(t => body.includes(t));
    const score = terms.reduce((sum, t) => sum + (title.includes(t) ? 8 : units.includes(t) ? 4 : objectives.includes(t) ? 2 : 1), 0);
    return { item, index, score, matches };
  }).filter(row => row.matches).sort((a, b) => b.score - a.score || a.index - b.index).map(row => row.item);
}

export function readBookmarks(storage: Pick<Storage, 'getItem'> | undefined): string[] {
  try {
    const value: unknown = JSON.parse(storage?.getItem('llmwiki:bookmarks') || '[]');
    return Array.isArray(value) ? [...new Set(value.filter((id): id is string => typeof id === 'string' && !!id))] : [];
  } catch { return []; }
}
export function toggleBookmark(ids: string[], id: string): string[] {
  return ids.includes(id) ? [...new Set(ids.filter(value => value !== id))] : [...new Set([...ids, id])];
}
export function saveBookmarks(storage: Pick<Storage, 'setItem'> | undefined, ids: string[]): boolean {
  try { if (!storage) return false; storage.setItem('llmwiki:bookmarks', JSON.stringify(ids)); return true; }
  catch { return false; }
}
