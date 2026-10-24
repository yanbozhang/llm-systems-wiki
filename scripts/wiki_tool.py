"""知识库结构检查、学习轮换与订阅候选发现。仅使用标准库。"""
from __future__ import annotations
import argparse
import copy
import hashlib
import ipaddress
import json
import re
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

MODULES = ('network', 'training', 'inference', 'harness', 'knowledge', 'agents')
TOPICS = (
 ('transformer', 'attention-heads', 'position', 'ffn-norm'),
 ('pretraining', 'sft', 'preference', 'policy-optimization'),
 ('prefill-decode', 'kv-cache', 'cache-scheduling', 'inference-frameworks'),
 ('agent-loop', 'context', 'memory', 'tools-skills'),
 ('rag', 'ingestion', 'hybrid-search', 'graph-wiki'),
 ('task-loop', 'gui-agent', 'coding-agent', 'agent-evaluation'),
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    """同目录原子替换；失败保留原文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         delete=False) as out:
            temp = Path(out.name)
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write('\n')
        temp.replace(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def check(root):
    root = Path(root).resolve()
    errors = []
    collections = {}
    for name, path in [('topics', 'knowledge/topics.json'), ('claims', 'knowledge/claims.json'),
                       ('relations', 'knowledge/relations.json'), ('sources', 'sources/manifest/sources.json')]:
        rows = read_json(root / path)
        if not isinstance(rows, list):
            errors.append(f'{name}: 必须是数组')
            rows = []
        table = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'].strip():
                errors.append(f'{name}: 缺少有效 ID')
                continue
            if row['id'] in table:
                errors.append(f'{name}: 重复 ID {row["id"]}')
            table[row['id']] = row
        collections[name] = table
    topics, sources = collections['topics'], collections['sources']
    paths = set()
    for topic in topics.values():
        page = topic.get('page', '')
        if not isinstance(page, str) or not page.strip():
            errors.append(f'{topic["id"]}: 页面路径必须是非空字符串')
            continue
        path = (root / page).resolve()
        if topic.get('module') not in MODULES:
            errors.append(f'{topic["id"]}: 非法模块')
        if not path.is_relative_to(root) or not path.is_file():
            errors.append(f'{topic["id"]}: 页面不存在或越界')
        if path in paths:
            errors.append(f'{topic["id"]}: 页面重复')
        paths.add(path)
    for claim in collections['claims'].values():
        if claim.get('topic') not in topics:
            errors.append(f'{claim["id"]}: 未知主题')
        evidence = claim.get('evidence', [])
        if not evidence:
            errors.append(f'{claim["id"]}: 缺少证据')
        for ref in evidence:
            src = sources.get(ref.get('source_id'))
            if (not src or not isinstance(src.get('version'), str)
                    or not src['version'].strip()
                    or ref.get('source_version') != src.get('version')):
                errors.append(f'{claim["id"]}: 来源版本无效')
            elif src.get('status') == 'withdrawn' and claim.get('status') != 'withdrawn':
                errors.append(f'{claim["id"]}: 使用已撤回来源')
    graph = {key: [] for key in topics}
    allowed = {'prerequisite', 'related', 'compares', 'implements', 'extends'}
    for rel in collections['relations'].values():
        a, b = rel.get('from'), rel.get('to')
        if a not in topics or b not in topics or rel.get('type') not in allowed:
            errors.append(f'{rel["id"]}: 关系端点或类型无效')
        elif rel['type'] == 'prerequisite':
            graph[a].append(b)
    active, visited = set(), set()
    def visit(node):
        if node in active:
            errors.append(f'{node}: 先修关系有环')
            return
        if node in visited:
            return
        active.add(node)
        for nxt in graph[node]:
            visit(nxt)
        active.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)
    for path in root.rglob('*.md'):
        if any(p in {'.git', '.venv', 'flux', 'site'} for p in path.relative_to(root).parts):
            continue
        lines, fence = [], None
        for line in path.read_text(encoding='utf-8').splitlines():
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
            if fence:
                if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                    fence = None
                continue
            if marker:
                fence = marker[1]
                continue
            if line.startswith(('    ', '\t')):
                continue
            lines.append(line)
        body = '\n'.join(lines)
        for target in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)]+)\)', body):
            target = target.strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            dest = (path.parent / unquote(parsed.path)).resolve()
            if not dest.is_relative_to(root) or not dest.exists():
                errors.append(f'{path.relative_to(root)}: 断链或越界 {target}')
    return errors


def plan(day):
    if isinstance(day, str) and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('日期必须使用 YYYY-MM-DD')
    day = date.fromisoformat(day) if isinstance(day, str) else day
    weekday = day.weekday()
    if weekday == 6:
        return {'date': day.isoformat(), 'module': 'review', 'topic': None, 'reason': '每周跨模块复盘与证据检查'}
    week = (day - date(2026, 10, 19)).days // 7
    return {'date': day.isoformat(), 'module': MODULES[weekday],
            'topic': TOPICS[weekday][week % 4], 'reason': '六模块轮换与四周主题覆盖'}


def parse_feed(xml, feed_id):
    root = ET.fromstring(xml)
    if root.tag == '{http://www.w3.org/2005/Atom}feed':
        ns = '{http://www.w3.org/2005/Atom}'
        entries = root.findall(ns + 'entry')
    elif root.tag == 'rss':
        ns = ''
        entries = root.findall('./channel/item')
    else:
        raise ValueError('不支持的订阅格式')
    items = {}
    for entry in entries:
        link = ''
        if ns:
            for el in entry.findall(ns + 'link'):
                if el.get('rel', 'alternate') == 'alternate':
                    link = el.get('href', '').strip()
                    break
        else:
            link = (entry.findtext('link') or '').strip()
        parsed_link = urlsplit(link)
        if (parsed_link.scheme not in {'http', 'https'} or not parsed_link.hostname
                or parsed_link.username or parsed_link.password):
            continue
        identity = (entry.findtext(ns + 'id') or entry.findtext('guid') or link).strip()
        if not identity:
            continue
        data = {'feed_id': feed_id, 'entry_id': identity,
                'title': (entry.findtext(ns + 'title') or '').strip(), 'url': link,
                'updated': (entry.findtext(ns + 'updated') or entry.findtext('pubDate') or '').strip() or None}
        key = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        items[key] = {'id': key, **data, 'status': 'pending_read', 'reading_scope': 'feed_metadata'}
    return list(items.values())


def fetch_feed(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or parsed.username or parsed.password or not host or host.lower() == 'localhost':
        raise ValueError('订阅地址必须是无凭证的 HTTPS 域名')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('订阅地址不接受 IP 字面量')
    # 禁止跳转到未经登记的目标，维护者应更新源配置。
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={'User-Agent': 'llmwiki-source-monitor/0.1'})
    with opener.open(req, timeout=20) as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError('订阅超过 2 MiB 限额')
    return body


def discover(feeds, state, fetcher=fetch_feed, now=None):
    now = now or datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    updated_state = copy.deepcopy(state)
    seen = set(updated_state.get('seen', []))
    checked = updated_state.setdefault('checked', {})
    candidates, results = [], []
    for index, feed in enumerate(feeds):
        feed_id = (feed.get('id') if isinstance(feed, dict) else None)
        valid_id = isinstance(feed_id, str) and bool(feed_id.strip())
        if not valid_id:
            feed_id = f'invalid-feed-{index}'
        try:
            if not valid_id:
                raise ValueError('来源配置缺少有效 ID')
            items = parse_feed(fetcher(feed['url']), feed_id)
            additions = [item for item in items if item['id'] not in seen]
            candidates.extend(additions)
            seen.update(item['id'] for item in additions)
            checked[feed_id] = now
            results.append({'feed_id': feed_id, 'status': 'ok', 'new_count': len(additions)})
        except Exception as exc:
            results.append({'feed_id': feed_id, 'status': 'error', 'error': str(exc)[:300]})
    updated_state['seen'] = sorted(seen)
    failures = sum(item['status'] == 'error' for item in results)
    status = ('failed' if failures == len(results) else 'partial_failure') if failures else ('changed' if candidates else 'unchanged')
    return {'checked_at': now, 'status': status, 'candidates': candidates, 'feeds': results}, updated_state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'plan', 'discover'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--date', default=None)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            errors = check(args.root)
            print('\n'.join(errors) if errors else '知识库结构检查通过')
            return int(bool(errors))
        if args.command == 'plan':
            print(json.dumps(plan(args.date or datetime.now(ZoneInfo('Asia/Shanghai')).date()), ensure_ascii=False, indent=2))
            return 0
        out = args.output or args.root / 'candidates'
        state_path = out / 'state.json'
        state = read_json(state_path) if state_path.exists() else {'seen': [], 'checked': {}}
        feeds = read_json(args.root / 'sources/manifest/feeds.json')
        report, new_state = discover(feeds, state)
        # 每轮保留不可变日志，先保存线索，后推进检查点。
        run_id = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
        write_json(out / 'runs' / (run_id + '.json'), report)
        write_json(out / 'latest.json', report)
        write_json(state_path, new_state)
        print(json.dumps({'status': report['status'], 'new_count': len(report['candidates'])}, ensure_ascii=False))
        return int(report['status'] in {'failed', 'partial_failure'})
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'维护任务失败：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
