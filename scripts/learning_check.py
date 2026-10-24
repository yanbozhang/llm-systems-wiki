"""离线核对知识点的公式、教学代码、结构图与来源连接。"""
import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def markdown_blocks(text):
    """解析本库使用的标题、围栏和公式块；不执行任何标记内容。"""
    blocks, buffer = [], []
    fence, language, math_block, comment = None, '', False, False
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                blocks.append(('code', language, '\n'.join(buffer)))
                fence, buffer = None, []
            else:
                buffer.append(line)
            continue
        if math_block:
            if line.strip() == '$$':
                blocks.append(('math', '', '\n'.join(buffer)))
                math_block, buffer = False, []
            else:
                buffer.append(line)
            continue
        if not comment and marker:
            fence = marker[1]
            language = marker[2].strip().split()[0].lower() if marker[2].strip() else ''
            buffer = []
            continue
        if not comment and line.startswith(('    ', '\t')):
            continue
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
        line = ''.join(visible)
        if re.match(r'^ {0,3}\$\$', line):
            value = line.strip()[2:]
            if value.endswith('$$'):
                blocks.append(('math', '', value[:-2]))
            else:
                math_block, buffer = True, [value] if value else []
        else:
            heading = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*$', line)
            if heading:
                title = re.sub(r'\s+#+\s*$', '', heading[2])
                blocks.append(('heading', len(heading[1]), title))
            else:
                blocks.append(('text', '', line))
    if fence is not None or math_block:
        blocks.append(('invalid', '', '围栏或公式未闭合'))
    return blocks


def check(root):
    root = Path(root).resolve()
    errors = []

    def collection(relative):
        try:
            rows = json.loads((root / relative).read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            errors.append(f'{relative}: 无法读取合法JSON（{type(exc).__name__}）')
            return {}
        if not isinstance(rows, list):
            errors.append(f'{relative}: 必须是数组')
            return {}
        found = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'].strip():
                errors.append(f'{relative}: 条目或ID无效')
                continue
            if row['id'] in found:
                errors.append(f'{relative}: ID重复 {row["id"]}')
            found[row['id']] = row
        return found

    def within(value, directory, suffix=None):
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            path = (root / value).resolve()
            valid = path.is_relative_to(root / directory) and path.is_file()
        except (OSError, RuntimeError, ValueError):
            return None
        if not valid:
            return None
        return path if suffix is None or path.suffix == suffix else None

    topics = collection('knowledge/topics.json')
    units = collection('knowledge/units.json')
    sources = collection('sources/manifest/sources.json')
    claims = collection('knowledge/claims.json')
    if not topics:
        errors.append('主题清单不能为空')
    by_topic = defaultdict(list)
    functions = {}
    for key, unit in units.items():
        topic = unit.get('topic')
        if not isinstance(topic, str) or topic not in topics:
            errors.append(f'{key}: 主题引用无效')
            continue
        by_topic[topic].append(unit)
        title, function = unit.get('title'), unit.get('function')
        if not isinstance(title, str) or not title.startswith('知识点'):
            errors.append(f'{key}: 知识点标题无效')
        if not isinstance(function, str) or not function.isidentifier():
            errors.append(f'{key}: 函数名无效')
        example = within(unit.get('example'), 'examples', '.py')
        if example is None:
            errors.append(f'{key}: 示例不存在或越界')
        else:
            if example not in functions:
                try:
                    tree = ast.parse(example.read_text(encoding='utf-8'))
                    functions[example] = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                except (OSError, ValueError, SyntaxError):
                    functions[example] = set()
                    errors.append(f'{key}: 示例无法解析')
            if isinstance(function, str) and function not in functions[example]:
                errors.append(f'{key}: 示例中找不到函数 {function}')
        refs = unit.get('source_ids')
        valid_refs = isinstance(refs, list) and bool(refs) and all(isinstance(r, str) and r in sources for r in refs)
        if not valid_refs:
            errors.append(f'{key}: 来源引用无效')
        claim_id = unit.get('claim_id')
        claim = claims.get(claim_id) if isinstance(claim_id, str) else None
        if not claim or claim.get('topic') != topic:
            errors.append(f'{key}: 声明引用无效')
        elif valid_refs:
            evidence = claim.get('evidence')
            linked = {e.get('source_id') for e in evidence if isinstance(e, dict) and isinstance(e.get('source_id'), str)} if isinstance(evidence, list) else set()
            if not set(refs).issubset(linked):
                errors.append(f'{key}: 声明未绑定知识点来源')

    for key, topic in topics.items():
        registered = by_topic[key]
        if len(registered) < 3:
            errors.append(f'{key}: 至少需要三个知识点')
        path = within(topic.get('page'), 'wiki', '.md')
        if path is None:
            errors.append(f'{key}: 主题页面不存在或越界')
            continue
        try:
            blocks = markdown_blocks(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError):
            errors.append(f'{key}: 无法读取主题正文')
            continue
        sections, current = defaultdict(list), None
        heading_counts = Counter()
        for kind, arg, value in blocks:
            if kind == 'invalid':
                errors.append(f'{key}: {value}')
            if kind == 'heading' and arg <= 3:
                current = value if arg == 3 and value.startswith('知识点') else None
                if current:
                    heading_counts[current] += 1
            elif current:
                sections[current].append((kind, arg, value))
        titles = [u.get('title') for u in registered if isinstance(u.get('title'), str)]
        if len(set(titles)) != len(titles) or any(n != 1 for n in heading_counts.values()):
            errors.append(f'{key}: 知识点标题重复')
        if set(heading_counts) != set(titles):
            errors.append(f'{key}: 正文知识点与登记不一致')
        urls = set()
        for unit in registered:
            uid, title = unit['id'], unit.get('title')
            items = sections.get(title, []) if isinstance(title, str) else []
            if not any(kind == 'math' and value.strip() for kind, _, value in items):
                errors.append(f'{uid}: 缺少实质公式块')
            codes = [value for kind, lang, value in items if kind == 'code' and lang == 'python' and value.strip()]
            if not codes:
                errors.append(f'{uid}: 缺少Python代码块')
            else:
                linked_code = False
                for value in codes:
                    try:
                        nodes = list(ast.walk(ast.parse(value)))
                    except (ValueError, SyntaxError):
                        continue
                    for node in nodes:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == unit.get('function'):
                            linked_code = True
                        elif isinstance(node, ast.Call):
                            called = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else None
                            if isinstance(unit.get('function'), str) and called == unit['function']:
                                linked_code = True
                if not linked_code:
                    errors.append(f'{uid}: 代码块未以有效Python关联登记函数')
            if not any(kind == 'code' and lang == 'mermaid' and value.strip() for kind, lang, value in items):
                errors.append(f'{uid}: 缺少Mermaid结构图')
            refs = unit.get('source_ids')
            for sid in refs if isinstance(refs, list) else []:
                if isinstance(sid, str) and sid in sources and isinstance(sources[sid].get('url'), str):
                    url = sources[sid]['url'].strip()
                    if url:
                        urls.add(url)
        if len(urls) < 2:
            errors.append(f'{key}: 至少需要两个不同URL的来源')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = check(args.root)
    print('\n'.join(errors) if errors else '知识点公式、代码、结构图与来源检查通过')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
