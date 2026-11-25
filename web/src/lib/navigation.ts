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

export function parseSearchIndex(value: unknown): SearchItem[] {
  if (!Array.isArray(value)) throw new Error('Invalid search index');
  const ids = new Set<string>();
  for (const item of value) {
    if (!item || typeof item !== 'object'
        || !['id', 'title', 'module', 'moduleTitle', 'moduleEnglish', 'text', 'url', 'description']
          .every(key => typeof item[key] === 'string')
        || !['unitTitles', 'objectives'].every(key =>
          Array.isArray(item[key]) && item[key].every((entry: unknown) => typeof entry === 'string'))
        || !/^[a-z0-9][a-z0-9._-]*$/.test(item.id) || ids.has(item.id)
        || item.url !== sitePath(`/read/${item.id}/`)) {
      throw new Error('Invalid search index');
    }
    ids.add(item.id);
  }
  return value as SearchItem[];
}

export function createTopicSearch(items: SearchItem[]) {
  const indexed = items.map((item, index) => {
    const title = normalize(`${item.title} ${item.id}`);
    const units = normalize(item.unitTitles.join(' '));
    const objectives = normalize(item.objectives.join(' '));
    const body = normalize(`${title} ${units} ${objectives} ${item.text} ${item.moduleTitle} ${item.moduleEnglish}`);
    return { item, index, title, units, objectives, body };
  });
  return (query: string, module = 'all'): SearchItem[] => {
    const terms = normalize(query).split(/\s+/).filter(Boolean);
    return indexed.filter(row => (module === 'all' || row.item.module === module)
      && terms.every(term => row.body.includes(term)))
      .map(row => ({...row, score: terms.reduce((sum, term) => sum
        + (row.title.includes(term) ? 8 : row.units.includes(term) ? 4 : row.objectives.includes(term) ? 2 : 1), 0)}))
      .sort((left, right) => right.score - left.score || left.index - right.index)
      .map(row => row.item);
  };
}

export function searchTopics(items: SearchItem[], query: string, module = 'all'): SearchItem[] {
  return createTopicSearch(items)(query, module);
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
