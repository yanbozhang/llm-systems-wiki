#!/usr/bin/env python3
"""Create traceable source folders and an optional, uncommitted local cache."""
import argparse
import hashlib
from http.client import HTTPException
import ipaddress
import json
import re
import socket
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 20 * 1024 * 1024
ID_PATTERN = re.compile(r'[a-z0-9][a-z0-9._-]*\Z')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def inside(root, relative):
    root = Path(root).resolve()
    if Path(relative).is_absolute():
        raise ValueError('记录必须使用相对路径')
    expected = root / relative
    try:
        path = expected.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError('路径无法安全解析') from exc
    if not path.is_relative_to(root) or path != expected:
        raise ValueError('路径必须位于仓库内，且不能通过符号链接或别名跳转')
    return path


def github_file_identity(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None:
        return None
    parts = unquote(parsed.path).strip('/').split('/')
    if parsed.hostname == 'github.com' and len(parts) >= 5 and parts[2] == 'blob':
        owner, repo, revision = parts[0], parts[1], parts[3]
    elif parsed.hostname == 'raw.githubusercontent.com' and len(parts) >= 4:
        owner, repo, revision = parts[:3]
    else:
        return None
    if not owner or not repo or not re.fullmatch(r'[a-f0-9]{40}', revision):
        return None
    return owner.lower(), repo.lower(), revision


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, encoding='utf-8', delete=False) as out:
        temp = Path(out.name)
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')
    temp.replace(path)


def load_sources(root):
    rows = read_json(Path(root) / 'sources/manifest/sources.json')
    if not isinstance(rows, list):
        raise ValueError('来源清单必须是数组')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not ID_PATTERN.fullmatch(row['id']):
            raise ValueError('来源ID无效')
        if row['id'] in seen:
            raise ValueError('来源ID重复')
        if not isinstance(row.get('url'), str) or not isinstance(row.get('title'), str):
            raise ValueError('来源缺少标题或URL')
        seen.add(row['id'])
    return rows


def source_usage(root):
    topics = read_json(Path(root) / 'knowledge/topics.json')
    claims = read_json(Path(root) / 'knowledge/claims.json')
    units = read_json(Path(root) / 'knowledge/units.json')
    by_topic = {t['id']: t for t in topics}
    usage = {}
    for row in units:
        for sid in row.get('source_ids', []):
            usage.setdefault(sid, set()).add(row['topic'])
    for row in claims:
        for ref in row.get('evidence', []):
            if isinstance(ref, dict) and ref.get('source_id'):
                usage.setdefault(ref['source_id'], set()).add(row.get('topic'))
    frontier_path = Path(root) / 'knowledge/frontiers.json'
    if frontier_path.exists():
        for row in read_json(frontier_path):
            for sid in row.get('source_ids', []):
                usage.setdefault(sid, set()).update(row.get('topic_ids', []))
    return {sid: [by_topic[tid] for tid in sorted(tid for tid in tids if tid in by_topic)]
            for sid, tids in usage.items()}


def markdown_literal(text):
    return re.sub(r'([\\`*_{}\[\]()#+\-.!|<>~&])', r'\\\1', str(text))


def materialize(root):
    root = Path(root).resolve()
    sources = load_sources(root)
    usage = source_usage(root)
    # Validate all destinations before creating directories.
    destinations = {s['id']: inside(root, f"sources/library/{s['id']}") for s in sources}
    index = []
    for source in sources:
        sid = source['id']
        folder = destinations[sid]
        folder.mkdir(parents=True, exist_ok=True)
        write_json(inside(root, f'sources/library/{sid}/source.json'), source)
        archive_path = inside(root, f'sources/library/{sid}/archive.json')
        if not archive_path.exists():
            write_json(archive_path, {'source_id': sid, 'status': 'not_requested', 'captures': []})
        archive = read_json(archive_path)
        linked = usage.get(sid, [])
        record = {'id': sid, 'title': source['title'], 'path': f'sources/library/{sid}/README.md',
                  'topic_ids': [t['id'] for t in linked],
                  'module_ids': sorted({t['module'] for t in linked}),
                  'archive_status': archive.get('status', 'not_requested')}
        index.append(record)
        state = {'saved': '已有来源快照的保存记录；取得时间见档案，新克隆需重新下载本地缓存',
                 'failed': '本轮未取得原文，保留原站入口',
                 'not_requested': '尚未下载，仅有来源资料卡'}.get(record['archive_status'], '状态需检查')
        lines = [f"# {source['title']}", '', f"来源ID：`{sid}`", '',
                 f"[打开原始来源](<{source['url']}>) · [原始登记信息](source.json) · [保存记录](archive.json)", '',
                 '## 这份资料用在哪里', '']
        lines += [f"- [{t['title']}](../../../{t['page']})" for t in linked] or ['尚未绑定基础主题；可能是课程入口或待编纂来源。']
        lines += ['', '## 阅读与版本', '',
                  f"- 实际登记的读取范围：{markdown_literal(source.get('reading_scope', '未登记'))}",
                  f"- 原生版本：`{source.get('native_version') or '未登记'}`",
                  f"- 原登记指纹：`{source.get('version', '未登记')}`",
                  f"- 定位：{markdown_literal(source.get('locator', '未登记'))}", '',
                  '## 本地资料', '', state + '。', '',
                  '原文缓存位于Git忽略的`sources/.local/`，具体相对路径与字节SHA-256见保存记录。'
                  '缓存可能是论文正文、源码文件或网站入口，保存记录中的representation会说明范围；保存不表示全文已阅读或结论已复现。', '',
                  '第三方全文默认只在本地留存。原作许可未核实时不随本仓库公开分发；本库MIT许可证不改变原作权利。', '',
                  '[返回来源资料库](../../README.md)', '']
        public = archive.get('public_snapshot')
        if public:
            snapshot = inside(root, f'sources/library/{sid}/snapshot')
            links = []
            for key, label in (('content_file', '源码或文档快照'), ('license_file', '上游许可证'), ('notice_file', '上游NOTICE')):
                if key in public:
                    file = inside(root, public[key])
                    if not file.is_relative_to(snapshot) or not file.is_file():
                        raise ValueError('公开快照必须是该来源snapshot目录内的文件')
                    links.append(f'[{label}]({file.relative_to(folder).as_posix()})')
            lines += ['## 可随仓库读取的上游快照', '', ' · '.join(links), '',
                      f"本快照保留上游{public['spdx_id']}许可与文件内声明，未将第三方材料改为本库许可。", '']
        inside(root, f'sources/library/{sid}/README.md').write_text('\n'.join(lines), encoding='utf-8')
    write_json(inside(root, 'sources/library/index.json'), index)
    return index


def validate_url(url, resolver=socket.getaddrinfo):
    if not isinstance(url, str) or re.search(r'[\x00-\x20\x7f]', url):
        raise ValueError('原文地址无效')
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower().rstrip('.')
    if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None or not host
            or '%' in host or host == 'localhost' or host.endswith('.localhost')
            or parsed.port not in (None, 443)):
        raise ValueError('仅接受无凭证的公网HTTPS地址')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('原文地址不接受IP字面量')
    addresses = resolver(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('原文地址必须解析到公网')
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))


def candidates(url):
    parsed = urlsplit(url)
    clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))
    parts = parsed.path.strip('/').split('/')
    if parsed.hostname == 'github.com' and len(parts) >= 5 and parts[2] == 'blob':
        raw = 'https://raw.githubusercontent.com/' + '/'.join(parts[:2] + parts[3:])
        return [(raw, 'source_file')]
    if parsed.hostname == 'arxiv.org' and len(parts) == 2 and parts[0] in ('html', 'abs', 'pdf'):
        aid = parts[1].removesuffix('.pdf')
        return [(f'https://arxiv.org/html/{aid}', 'paper_full_text'),
                (f'https://arxiv.org/pdf/{aid}', 'paper_full_text'),
                (f'https://arxiv.org/abs/{aid}', 'paper_landing_page')]
    representation = 'source_file' if parsed.hostname == 'raw.githubusercontent.com' else 'web_page'
    return [(clean, representation)]


def fetch_public(url, max_bytes=MAX_BYTES):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    for hop in range(4):
        url = validate_url(url)
        request = urllib.request.Request(url, headers={'User-Agent': 'LLM-Systems-Wiki-source-library/1.0'})
        try:
            response = opener.open(request, timeout=20)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get('Location') and hop < 3:
                url = urljoin(url, exc.headers['Location'])
                exc.close()
                continue
            raise
        with response:
            declared = response.headers.get('Content-Length')
            if declared is not None and (not declared.isdigit() or int(declared) > max_bytes):
                raise ValueError('原文长度声明无效或超过上限')
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError('原文超过20MiB上限')
            if not body:
                raise ValueError('原文为空')
            if declared is not None and len(body) != int(declared):
                raise ValueError('原文传输不完整')
            return {'body': body, 'url': url, 'content_type': response.headers.get('Content-Type', '')}
    raise ValueError('重定向次数超限')


def capture_one(root, source, fetcher=fetch_public):
    root = Path(root).resolve()
    sid = source['id']
    if not isinstance(sid, str) or not ID_PATTERN.fullmatch(sid):
        raise ValueError('来源ID无效')
    archive_path = inside(root, f'sources/library/{sid}/archive.json')
    old = read_json(archive_path) if archive_path.exists() else {'source_id': sid, 'status': 'not_requested', 'captures': []}
    attempted = datetime.now(timezone.utc).isoformat()
    failures = []
    for url, representation in candidates(source['url']):
        try:
            result = fetcher(url)
            body = result['body']
            if not isinstance(body, bytes) or not body or len(body) > MAX_BYTES:
                raise ValueError('原文为空或超过上限')
            digest = hashlib.sha256(body).hexdigest()
            relative = f'sources/.local/objects/{digest}.bin'
            target = inside(root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            if (not target.is_file() or target.stat().st_size != len(body)
                    or hashlib.sha256(target.read_bytes()).hexdigest() != digest):
                with tempfile.NamedTemporaryFile('wb', dir=target.parent, delete=False) as stream:
                    temp = Path(stream.name)
                    stream.write(body)
                temp.replace(target)
            capture = {'sha256': digest, 'bytes': len(body), 'cache_file': relative,
                       'requested_url': url, 'resolved_url': result.get('url', url),
                       'content_type': result.get('content_type', ''), 'representation': representation,
                       'retrieved_at': attempted, 'declared_source_version': source.get('version'),
                       'redistribution': 'local_only_license_not_reviewed'}
            history = old.get('captures', [])
            if not any(item.get('sha256') == digest and item.get('requested_url') == url for item in history):
                history.append(capture)
            old.update(source_id=sid, status='saved', captures=history,
                       last_attempt={'at': attempted, 'status': 'saved'})
            write_json(archive_path, old)
            return {'id': sid, 'status': 'saved', 'bytes': len(body), 'representation': representation}
        except (OSError, HTTPException, ValueError, KeyError, TypeError) as exc:
            reason = f'HTTP {exc.code}' if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
            failures.append({'url': url, 'reason': reason})
    old['status'] = 'saved' if old.get('captures') else 'failed'
    old['last_attempt'] = {'at': attempted, 'status': 'failed', 'errors': failures}
    write_json(archive_path, old)
    return {'id': sid, 'status': 'failed', 'previous_capture_kept': bool(old.get('captures'))}


def capture_all(root, ids=None, workers=3, fetcher=fetch_public):
    if workers not in (1, 2, 3):
        raise ValueError('并发只能为1至3')
    sources = load_sources(root)
    if ids is not None:
        missing = set(ids) - {s['id'] for s in sources}
        if missing:
            raise ValueError('请求的来源ID不存在')
        sources = [s for s in sources if s['id'] in ids]
    materialize(root)
    # URL-sharing sources reuse the response within this bounded batch.
    groups = {}
    for source in sources:
        groups.setdefault(source['url'].split('#', 1)[0], []).append(source)
    def capture_group(group):
        responses = {}
        def shared(url):
            if url not in responses:
                try:
                    responses[url] = fetcher(url)
                except (OSError, HTTPException, ValueError) as exc:
                    responses[url] = exc
            if isinstance(responses[url], Exception):
                raise responses[url]
            return responses[url]
        return [capture_one(root, source, shared) for source in group]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for rows in pool.map(capture_group, groups.values()):
            results.extend(rows)
    materialize(root)
    return results


def check_library(root, local=False):
    root = Path(root).resolve()
    errors = []
    try:
        sources = load_sources(root)
    except (OSError, ValueError, TypeError) as exc:
        return [f'来源清单无效：{type(exc).__name__}']
    source_ids = {s['id'] for s in sources}
    try:
        library = inside(root, 'sources/library')
        if {p.name for p in library.iterdir() if p.is_dir()} != source_ids:
            errors.append('来源目录与清单不是一一对应')
        index = read_json(inside(root, 'sources/library/index.json'))
        if (not isinstance(index, list) or len(index) != len(sources)
                or any(not isinstance(r, dict) for r in index)
                or {r.get('id') for r in index} != source_ids):
            errors.append('来源索引与清单不一致')
        else:
            for record in index:
                if record.get('path') != f"sources/library/{record['id']}/README.md":
                    errors.append(f"{record['id']}: 索引路径无效")
        topics = read_json(root / 'knowledge/topics.json')
        topic_ids = {t['id'] for t in topics}
        units = read_json(root / 'knowledge/units.json')
        claims = read_json(root / 'knowledge/claims.json')
        for unit in units:
            if unit.get('topic') not in topic_ids or any(sid not in source_ids for sid in unit.get('source_ids', [])):
                errors.append('知识点引用不存在的来源或主题')
        for claim in claims:
            if claim.get('topic') not in topic_ids or any(e.get('source_id') not in source_ids for e in claim.get('evidence', [])):
                errors.append('声明引用不存在的来源或主题')
        frontier_path = inside(root, 'knowledge/frontiers.json')
        if frontier_path.exists():
            for frontier in read_json(frontier_path):
                if (any(sid not in source_ids for sid in frontier.get('source_ids', []))
                        or any(tid not in topic_ids for tid in frontier.get('topic_ids', []))):
                    errors.append('研究进展引用不存在的来源或主题')
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        errors.append('来源索引或知识关联无法读取')
    for source in sources:
        sid = source['id']
        try:
            folder = inside(root, f'sources/library/{sid}')
            card = inside(root, f'sources/library/{sid}/README.md')
            metadata = inside(root, f'sources/library/{sid}/source.json')
            if not card.is_file() or read_json(metadata) != source:
                errors.append(f'{sid}: 来源卡片或元数据不一致')
            archive = read_json(inside(root, f'sources/library/{sid}/archive.json'))
            if not isinstance(archive, dict):
                errors.append(f'{sid}: 保存记录必须是对象')
                continue
            public = archive.get('public_snapshot')
            if public is not None:
                if (not isinstance(public, dict) or public.get('spdx_id') not in ('MIT', 'Apache-2.0')
                        or not isinstance(public.get('source_commit'), str)
                        or not re.fullmatch(r'[a-f0-9]{40}', public['source_commit'])
                        or public.get('source_commit') != source.get('native_version')
                        or not isinstance(public.get('upstream_license_url'), str)
                        or urlsplit(public['upstream_license_url']).scheme != 'https'
                        or not urlsplit(public['upstream_license_url']).hostname
                        or github_file_identity(source['url']) is None
                        or github_file_identity(source['url'])[2] != public['source_commit']
                        or github_file_identity(public['upstream_license_url']) != github_file_identity(source['url'])):
                    errors.append(f'{sid}: 公开快照许可或版本信息无效')
                    continue
                snapshot = inside(root, f'sources/library/{sid}/snapshot')
                for key in ('content_file', 'license_file') + (('notice_file',) if 'notice_file' in public else ()):
                    file = inside(root, public[key])
                    if not file.is_relative_to(snapshot) or not file.is_file() or not file.stat().st_size:
                        raise ValueError('公开快照文件缺失或越界')
                content = inside(root, public['content_file'])
                if content.is_file() and hashlib.sha256(content.read_bytes()).hexdigest() != public.get('content_sha256'):
                    errors.append(f'{sid}: 公开快照内容指纹不一致')
            captures = archive.get('captures')
            if (archive.get('source_id') != sid or archive.get('status') not in ('saved', 'failed', 'not_requested')
                    or not isinstance(captures, list) or bool(captures) != (archive.get('status') == 'saved')):
                errors.append(f'{sid}: 保存状态无效')
                continue
            for item in captures:
                if not isinstance(item, dict) or not re.fullmatch(r'[a-f0-9]{64}', item.get('sha256', '')):
                    errors.append(f'{sid}: 保存指纹无效')
                    continue
                fields = ('requested_url', 'resolved_url', 'retrieved_at', 'content_type', 'representation')
                if any(not isinstance(item.get(key), str) for key in fields):
                    errors.append(f'{sid}: 缺少原文取得信息')
                    continue
                if (not item['representation'] or not datetime.fromisoformat(item['retrieved_at']).tzinfo
                        or any(urlsplit(item[key]).scheme != 'https' or not urlsplit(item[key]).hostname
                               or urlsplit(item[key]).username is not None for key in ('requested_url', 'resolved_url'))):
                    errors.append(f'{sid}: 原文取得信息无效')
                    continue
                expected = f"sources/.local/objects/{item['sha256']}.bin"
                if (item.get('cache_file') != expected or type(item.get('bytes')) is not int
                        or not 0 < item['bytes'] <= MAX_BYTES):
                    errors.append(f'{sid}: 缓存路径或大小无效')
                    continue
                cache = inside(root, expected)
                if local and (not cache.is_file() or cache.stat().st_size != item['bytes']
                              or hashlib.sha256(cache.read_bytes()).hexdigest() != item['sha256']):
                    errors.append(f'{sid}: 当前机器缺少原文或指纹不一致')
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            errors.append(f'{sid}: 来源目录无法读取')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description='建立与检查可追溯来源资料库')
    parser.add_argument('action', choices=['index', 'capture', 'check'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--id', action='append', dest='ids')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'index':
        print(f'已整理{len(materialize(args.root))}个来源目录')
    elif args.action == 'capture':
        rows = capture_all(args.root, args.ids, args.workers)
        print(json.dumps({'saved': sum(r['status'] == 'saved' for r in rows),
                          'failed': [r['id'] for r in rows if r['status'] == 'failed']}, ensure_ascii=False))
    else:
        errors = check_library(args.root, args.local)
        print('\n'.join(errors) if errors else '来源资料库检查通过')
        return int(bool(errors))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
