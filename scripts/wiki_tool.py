"""知识库结构检查、学习轮换与订阅候选发现。仅使用标准库。"""
from __future__ import annotations
import argparse
import copy
import hashlib
import ipaddress
import json
import re
import string
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

# 仅用于旧版最小知识包的结构校验；正式轮换只使用版本化模块清单。
MODULES = ('network', 'training', 'inference', 'harness', 'knowledge', 'agents', 'benchmark')


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


def load_modules(root):
    rows = read_json(Path(root) / 'knowledge/modules.json')
    if not isinstance(rows, list) or len(rows) != 7:
        raise ValueError('模块清单必须包含七个模块')
    ids, days = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('模块必须是对象')
        key, day = row.get('id'), row.get('weekday')
        if not isinstance(key, str) or not key.strip() or key in ids:
            raise ValueError('模块 ID 缺失或重复')
        if type(day) is not int or day not in range(7) or day in days:
            raise ValueError('模块 weekday 必须唯一且位于 0 至 6')
        if not all(isinstance(row.get(field), str) and row[field].strip() for field in ('title', 'page')):
            raise ValueError('模块名称与页面不能为空')
        ids.add(key)
        days.add(day)
    if 'benchmark' not in ids:
        raise ValueError('模块清单缺少 benchmark')
    if any(row['id'] == 'benchmark' and row['weekday'] != 6 for row in rows):
        raise ValueError('benchmark 必须安排在周日')
    return sorted(rows, key=lambda row: row['weekday'])


def markdown_prose(body):
    """提取用于结构和链接检查的正文，忽略代码块与HTML注释。"""
    lines, fence, comment = [], None, False
    for line in body.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence)
                    and not line[marker.end():].strip()):
                fence = None
            continue
        if not comment and marker:
            fence = marker[1]
            continue
        if not comment and line.startswith(('    ', '\t')):
            continue
        # 代码内的注释符不改变正文状态；注释内的围栏也不打开代码块。
        visible, offset = [], 0
        while offset < len(line):
            if comment:
                end = line.find('-->', offset)
                if end < 0:
                    break
                comment, offset = False, end + 3
            else:
                start = line.find('<!--', offset)
                if start < 0:
                    visible.append(line[offset:])
                    break
                visible.append(line[offset:start])
                comment, offset = True, start + 4
        lines.append(''.join(visible))
    return '\n'.join(lines)


def curriculum_errors(root, topics, sources, modules):
    errors = []
    module_ids = {row['id'] for row in modules}
    levels = {'understand', 'derive', 'build', 'evaluate'}
    def inside_file(value, directory=root):
        if not isinstance(value, str) or not value.strip():
            return False
        path = (root / value).resolve()
        return path.is_relative_to(directory) and path.is_file()
    for module in modules:
        if not inside_file(module['page']):
            errors.append(f'{module["id"]}: 模块页面不存在或越界')
    for key, topic in topics.items():
        goals = topic.get('learning_objectives')
        if not isinstance(goals, list) or not goals or not all(isinstance(x, str) and x.strip() for x in goals):
            errors.append(f'{key}: 缺少学习目标')
        if topic.get('depth') not in {'overview', 'explained', 'worked', 'reproduced'}:
            errors.append(f'{key}: 非法内容成熟度')
        if topic.get('practice_status') not in {'designed', 'executed'}:
            errors.append(f'{key}: 非法实践状态')
        if topic.get('depth') == 'reproduced' or topic.get('practice_status') == 'executed':
            if not inside_file(topic.get('experiment_record')):
                errors.append(f'{key}: 缺少复现实验记录')
        if not inside_file(topic.get('page'), root / 'wiki'):
            continue
        body = markdown_prose((root / topic['page']).read_text(encoding='utf-8'))
        parts = re.split(r'^##\s+(.+)$', body, flags=re.M)
        sections = list(zip(parts[1::2], parts[2::2]))
        for heading in ('学习目标', '前置知识', '基本机制', '推导或示例', '适用条件', '实践任务', '掌握标准'):
            content = next((content for title, content in sections if title.strip().startswith(heading)), '')
            content = re.sub(r'<[^>]*>', '', content)
            content = re.sub(r'\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b|待补充|待完善|待填写|占位符', '', content, flags=re.I)
            if len(re.sub(r'[\W_]+', '', content)) < 20:
                errors.append(f'{key}: {heading}章节缺失或为空')
    registered = {(root / t['page']).resolve() for t in topics.values()
                  if inside_file(t.get('page'), root / 'wiki')}
    for path in (root / 'wiki/topics').rglob('*.md'):
        if path.resolve() not in registered:
            errors.append(f'{path.name}: 主题文件未登记')
    for filename, kind in [('knowledge/capabilities.json', 'capability'), ('sources/learning-resources.json', 'resource')]:
        try:
            rows = read_json(root / filename)
            if not isinstance(rows, list):
                raise ValueError('必须是数组')
        except (OSError, ValueError) as exc:
            errors.append(f'{filename}: {exc}')
            continue
        ids, coverage = set(), set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'].strip():
                errors.append(f'{filename}: ID 无效')
                continue
            if row['id'] in ids:
                errors.append(f'{filename}: ID 重复 {row["id"]}')
            ids.add(row['id'])
            if kind == 'capability':
                mod, level = row.get('module'), row.get('level')
                if mod not in module_ids or level not in levels:
                    errors.append(f'{row["id"]}: 能力模块或级别无效')
                    continue
                coverage.add((mod, level))
                linked = row.get('topic_ids')
                if (not isinstance(linked, list) or not linked
                        or not all(isinstance(x, str) and x in topics for x in linked)
                        or not any(topics[x]['module'] == mod for x in linked)):
                    errors.append(f'{row["id"]}: 能力主题引用无效')
                for field in ('outcome', 'deliverable'):
                    if not isinstance(row.get(field), str) or not row[field].strip():
                        errors.append(f'{row["id"]}: {field} 不能为空')
            else:
                linked = row.get('module_ids')
                if not isinstance(linked, list) or not linked or not all(isinstance(x, str) and x in module_ids for x in linked):
                    errors.append(f'{row["id"]}: 学习资源模块无效')
                url = row.get('url', '')
                if not isinstance(url, str) or urlsplit(url).scheme != 'https' or not urlsplit(url).hostname:
                    errors.append(f'{row["id"]}: 学习资源 URL 无效')
                if row.get('source_id') not in sources:
                    errors.append(f'{row["id"]}: 学习资源来源未知')
                for field in ('title', 'kind', 'reading_scope', 'access', 'reviewed_at'):
                    if not isinstance(row.get(field), str) or not row[field].strip():
                        errors.append(f'{row["id"]}: {field} 不能为空')
        if kind == 'capability':
            for mod in sorted(module_ids):
                for level in sorted(levels):
                    if (mod, level) not in coverage:
                        errors.append(f'{mod}: 缺少 {level} 能力目标')
    return errors


def check(root, curriculum=False):
    root = Path(root).resolve()
    errors = []
    modules = None
    if (root / 'knowledge/modules.json').exists():
        try:
            modules = load_modules(root)
        except (OSError, ValueError, TypeError) as exc:
            errors.append(f'模块配置无效：{exc}')
    module_ids = {row['id'] for row in modules} if modules else set(MODULES)
    for module in modules or []:
        page = (root / module['page']).resolve()
        if not page.is_relative_to(root) or not page.is_file():
            errors.append(f'{module["id"]}: 模块页面不存在或越界')
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
        if topic.get('module') not in module_ids:
            errors.append(f'{topic["id"]}: 非法模块')
        if not path.is_relative_to(root / 'wiki') or not path.is_file():
            errors.append(f'{topic["id"]}: 页面不存在或越界')
        if path in paths:
            errors.append(f'{topic["id"]}: 页面重复')
        paths.add(path)
    for claim in collections['claims'].values():
        if claim.get('topic') not in topics:
            errors.append(f'{claim["id"]}: 未知主题')
        evidence = claim.get('evidence', [])
        if not isinstance(evidence, list):
            errors.append(f'{claim["id"]}: 证据必须是数组')
            continue
        if not evidence:
            errors.append(f'{claim["id"]}: 缺少证据')
        for ref in evidence:
            if not isinstance(ref, dict):
                errors.append(f'{claim["id"]}: 证据项必须是对象')
                continue
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
        if any(p in {'.git', '.venv', 'flux', 'site', 'node_modules', 'dist', '.astro'} for p in path.relative_to(root).parts):
            continue
        body = markdown_prose(path.read_text(encoding='utf-8'))
        for target in markdown_link_targets(body):
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            dest = (path.parent / unquote(parsed.path)).resolve()
            if not dest.is_relative_to(root) or not dest.exists():
                errors.append(f'{path.relative_to(root)}: 断链或越界 {target}')
    if curriculum:
        if not modules:
            errors.append('课程检查需要完整模块清单')
        else:
            errors.extend(curriculum_errors(root, topics, sources, modules))
    return errors


def markdown_link_targets(body):
    """读取普通行内链接目的地，分离标题并保留平衡括号。"""
    ending = re.compile(
        r'''\s*\)|\s+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\((?:\\.|[^()\\])*\))\s*\)''')
    for match in re.finditer(r'(?<!!)\[(?:\\.|[^\]\\\n])+\]\(', body):
        pos = match.end()
        while pos < len(body) and body[pos].isspace():
            pos += 1
        angle = body.startswith('<', pos)
        if angle:
            pos += 1
        target, depth = [], 0
        while pos < len(body):
            char = body[pos]
            if char == '\\' and pos + 1 < len(body) and body[pos + 1] in string.punctuation:
                target.append(body[pos + 1])
                pos += 2
                continue
            if angle:
                if char in '<>\r\n':
                    break
            else:
                if char.isspace() or (char == ')' and depth == 0):
                    break
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
            target.append(char)
            pos += 1
        if angle:
            if pos == len(body) or body[pos] != '>':
                continue
            pos += 1
        elif depth:
            continue
        if ending.match(body, pos):
            yield ''.join(target)


def plan(day, root=None):
    if isinstance(day, str) and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('日期必须使用 YYYY-MM-DD')
    day = date.fromisoformat(day) if isinstance(day, str) else day
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    modules = load_modules(root)
    module = modules[day.weekday()]
    topics = read_json(root / 'knowledge/topics.json')
    if not isinstance(topics, list):
        raise ValueError('主题清单必须是数组')
    options = [t for t in topics if isinstance(t, dict) and t.get('module') == module['id']]
    if not options or not all(isinstance(t.get('id'), str) and t['id'].strip() for t in options):
        raise ValueError(f'{module["id"]}: 缺少可轮换主题')
    week = (day - date(2026, 10, 19)).days // 7
    topic = options[week % len(options)]
    goals = topic.get('learning_objectives') or [topic.get('title', topic['id'])]
    return {'date': day.isoformat(), 'module': module['id'], 'topic': topic['id'],
            'reason': '七模块轮换；模块内按登记顺序持续推进', 'review_due': day.weekday() == 6,
            'learning_objective': goals[0],
            'deliverable': topic.get('deliverable') or '完成本主题的实践任务与自测，记录证据和未解决问题'}


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
    host = (parsed.hostname or '').rstrip('.').lower()
    if (parsed.scheme != 'https' or parsed.username or parsed.password or not host
            or host == 'localhost' or host.endswith('.localhost')):
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
    parser.add_argument('--curriculum', action='store_true', help='检查七模块能力地图与知识单元完整性')
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            errors = check(args.root, curriculum=args.curriculum)
            print('\n'.join(errors) if errors else '知识库结构检查通过')
            return int(bool(errors))
        if args.command == 'plan':
            print(json.dumps(plan(args.date or datetime.now(ZoneInfo('Asia/Shanghai')).date(), args.root), ensure_ascii=False, indent=2))
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
