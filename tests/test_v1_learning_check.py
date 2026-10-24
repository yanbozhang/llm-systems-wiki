"""依据schema/知识点契约.md验证新检查器；全部知识包位于临时目录。"""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import learning_check as checker


class MarkdownBlocksTests(unittest.TestCase):
    def test_supported_atx_fences_and_math_are_separate_blocks(self):
        text = '   ### 知识点一：主题 ###\n$$x=1$$\n~~~PYTHON\nf(1)\n~~~\n$$\ny=2\n$$\n'
        blocks = checker.markdown_blocks(text)
        self.assertIn(('heading', 3, '知识点一：主题'), blocks)
        self.assertIn(('math', '', 'x=1'), blocks)
        self.assertIn(('math', '', 'y=2'), blocks)
        self.assertIn(('code', 'python', 'f(1)'), blocks)
        self.assertFalse(any(kind == 'invalid' for kind, _, _ in blocks))

    def test_structure_inside_code_does_not_become_real_blocks(self):
        text = '````python\n### 知识点假\n$$x$$\n```mermaid\nA-->B\n```\n````\n### 知识点真\n'
        blocks = checker.markdown_blocks(text)
        self.assertEqual([value for kind, level, value in blocks if kind == 'heading'], ['知识点真'])
        self.assertEqual(len([b for b in blocks if b[0] == 'code']), 1)
        self.assertFalse(any(b[0] == 'math' for b in blocks))

    def test_html_comments_hide_fake_structure_and_keep_following_content(self):
        # 注释里的图使用无向边，避免箭头中的-->提前结束HTML注释。
        text = '<!--\n### 知识点假\n$$x$$\n```mermaid\nA---B\n```\n-->\n前<!-- 一 -->中<!-- 二 -->后\n### 知识点真\n'
        blocks = checker.markdown_blocks(text)
        self.assertEqual([b[2] for b in blocks if b[0] == 'heading'], ['知识点真'])
        self.assertIn(('text', '', '前中后'), blocks)
        self.assertFalse(any(b[0] in ('code', 'math') for b in blocks))
        self.assertFalse(any(b[0] == 'invalid' for b in blocks))

    def test_comment_marker_inside_code_does_not_hide_later_heading(self):
        blocks = checker.markdown_blocks('```python\ns = "<!--"\n```\n### 知识点真\n$$x$$\n')
        self.assertIn(('heading', 3, '知识点真'), blocks)
        self.assertIn(('math', '', 'x'), blocks)

    def test_fence_closing_requires_matching_character_length_and_empty_suffix(self):
        text = '````python\nf()\n```\n~~~~\n```` tail\n````\n### 知识点后续\n'
        blocks = checker.markdown_blocks(text)
        code = [b for b in blocks if b[0] == 'code']
        self.assertEqual(len(code), 1)
        self.assertIn('```` tail', code[0][2])
        self.assertIn(('heading', 3, '知识点后续'), blocks)

    def test_unclosed_fence_and_math_have_invalid_marker(self):
        for text in ('```python\nf()\n', '$$\nx=1\n', '~~~~mermaid\nA-->B\n~~~\n'):
            self.assertTrue(any(kind == 'invalid' for kind, _, _ in checker.markdown_blocks(text)))

    def test_atx_literal_trailing_hash_without_space_belongs_to_title(self):
        # ATX可选收尾#须由空白分隔；C#里的#是标题文本。
        blocks = checker.markdown_blocks('### 知识点一：C#\n')
        self.assertIn(('heading', 3, '知识点一：C#'), blocks)


class KnowledgePackageCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'package'
        self.root.mkdir()
        self.functions = ['first', 'second', 'third']
        self.titles = ['知识点一：计算', '知识点二：边界', '知识点三：状态']
        self.topics = [{'id': 'topic-a', 'page': 'wiki/topics/a.md'}]
        self.sources = [{'id': 'source-a', 'url': 'https://example.org/a'},
                        {'id': 'source-b', 'url': 'https://example.org/b'}]
        self.claims = [{'id': f'claim-{i}', 'topic': 'topic-a',
                        'evidence': [{'source_id': 'source-a'}, {'source_id': 'source-b'}]} for i in range(3)]
        self.units = [{'id': f'unit-{i}', 'topic': 'topic-a', 'title': self.titles[i],
                       'example': 'examples/demo.py', 'function': self.functions[i],
                       'source_ids': ['source-a', 'source-b'], 'claim_id': f'claim-{i}'} for i in range(3)]
        self.collections = {'knowledge/topics.json': self.topics, 'knowledge/units.json': self.units,
                            'knowledge/claims.json': self.claims, 'sources/manifest/sources.json': self.sources}
        self.persist()
        self.write('examples/demo.py', 'raise RuntimeError("检查器不得执行教学代码")\n' +
                   '\n'.join(f'def {name}(x):\n    return x + 1\n' for name in self.functions))
        self.write_page()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def save(self, relative, value):
        return self.write(relative, json.dumps(value, ensure_ascii=False))

    def persist(self):
        for path, rows in self.collections.items():
            self.save(path, rows)

    def section(self, i, math_body='x=1', python_body=None, diagram_body='flowchart LR\n A-->B'):
        python_body = self.functions[i] + '(1)' if python_body is None else python_body
        return (f'### {self.titles[i]}\n说明输入、计算与边界。\n'
                f'$$\n{math_body}\n$$\n```python\n{python_body}\n```\n'
                f'```mermaid\n{diagram_body}\n```\n')

    def write_page(self, first=None):
        self.write('wiki/topics/a.md', '# 临时主题\n## 推导或示例\n' +
                   (self.section(0) if first is None else first) + self.section(1) + self.section(2))

    def checked(self):
        try:
            errors = checker.check(self.root)
        except Exception as exc:
            self.fail(f'契约要求返回错误列表，实际抛出{type(exc).__name__}: {exc}')
        self.assertIsInstance(errors, list)
        self.assertTrue(all(isinstance(e, str) and e.strip() for e in errors))
        return errors

    def rejected(self, locator=None):
        errors = self.checked()
        self.assertTrue(errors, '非法知识包应返回可定位错误')
        if locator:
            self.assertTrue(any(locator in e for e in errors), errors)
        return errors

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}


class LearningCheckTests(KnowledgePackageCase):
    def test_complete_fixture_is_valid_offline_read_only_and_does_not_execute_example(self):
        before = self.snapshot()
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('禁止联网')) as connect, \
             patch.object(socket, 'create_connection', side_effect=AssertionError('禁止联网')) as create:
            self.assertEqual(self.checked(), [])
        connect.assert_not_called()
        create.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_json_collections_require_arrays_and_readable_json(self):
        for path, original in self.collections.items():
            for value in ({}, None, 'wrong', 1):
                self.save(path, value)
                self.rejected(path)
            self.write(path, '{broken')
            self.rejected(path)
            self.save(path, original)
        (self.root / 'knowledge/units.json').unlink()
        self.rejected('knowledge/units.json')

    def test_collection_elements_and_ids_must_be_valid_and_unique(self):
        for path, original in self.collections.items():
            for extra in (None, 2, [], {}, {'id': None}, {'id': []}, {'id': '   '}, copy.deepcopy(original[0])):
                self.save(path, original + [extra])
                self.rejected(path)
            self.save(path, original)

    def test_topic_collection_cannot_be_empty(self):
        self.save('knowledge/topics.json', [])
        self.rejected()

    def test_unit_required_fields_missing_or_wrong_types_return_errors(self):
        for field in ('topic', 'title', 'example', 'function', 'source_ids', 'claim_id'):
            for value in (None, {}, 2):
                rows = copy.deepcopy(self.units)
                rows[0][field] = value
                self.save('knowledge/units.json', rows)
                self.rejected('unit-0')
            rows = copy.deepcopy(self.units)
            del rows[0][field]
            self.save('knowledge/units.json', rows)
            self.rejected('unit-0')
        self.save('knowledge/units.json', self.units)

    def test_unknown_topic_and_invalid_title_or_function_are_rejected(self):
        for field, value in (('topic', 'unknown'), ('title', '普通标题'), ('function', 'not-a-function'), ('function', '')):
            rows = copy.deepcopy(self.units)
            rows[0][field] = value
            self.save('knowledge/units.json', rows)
            self.rejected('unit-0')

    def test_source_list_nonempty_registered_and_typed(self):
        for refs in ([], 'source-a', ['missing'], [None], [{}], ['source-a', 1]):
            rows = copy.deepcopy(self.units)
            rows[0]['source_ids'] = refs
            self.save('knowledge/units.json', rows)
            self.rejected('unit-0')

    def test_claim_reference_must_exist_and_belong_to_same_topic(self):
        rows = copy.deepcopy(self.units)
        rows[0]['claim_id'] = 'missing'
        self.save('knowledge/units.json', rows)
        self.rejected('unit-0')
        self.save('knowledge/units.json', self.units)
        self.claims[0]['topic'] = 'other-topic'
        self.persist()
        self.rejected('unit-0')

    def test_claim_must_bind_all_listed_sources_and_malformed_evidence_is_rejected(self):
        for evidence in ([{'source_id': 'source-a'}], None, {}, [None], [{'source_id': []}]):
            self.claims[0]['evidence'] = evidence
            self.persist()
            self.rejected('unit-0')

    def test_each_topic_requires_three_units_not_only_global_total(self):
        self.save('knowledge/units.json', self.units[:2])
        self.rejected('topic-a')
        self.save('knowledge/units.json', self.units)
        self.topics.append({'id': 'topic-b', 'page': 'wiki/topics/b.md'})
        self.write('wiki/topics/b.md', '# 第二主题\n')
        self.persist()
        self.rejected('topic-b')

    def test_duplicate_registered_titles_are_rejected(self):
        self.units[1]['title'] = self.units[0]['title']
        self.persist()
        self.rejected('topic-a')

    def test_duplicate_page_heading_is_rejected(self):
        self.write_page(self.section(0) + self.section(0))
        self.rejected('topic-a')

    def test_missing_or_unregistered_page_heading_is_rejected(self):
        self.write_page(self.section(0).replace(self.titles[0], '知识点额外：未登记'))
        self.rejected('topic-a')
        self.write_page(self.section(0).replace('### ', '#### ', 1))
        self.rejected('topic-a')

    def test_formula_code_and_diagram_must_each_be_nonempty(self):
        for changed in ({'math_body': ' \t'}, {'python_body': ' \t'}, {'diagram_body': ' \t'}):
            self.write_page(self.section(0, **changed))
            self.rejected('unit-0')

    def test_formula_or_diagram_inside_python_fence_cannot_satisfy_structure(self):
        fake = (f'### {self.titles[0]}\n````python\nfirst(1)\n$$x$$\n'
                '```mermaid\nflowchart LR\nA-->B\n```\n````\n')
        self.write_page(fake)
        self.rejected('unit-0')

    def test_commented_heading_formula_code_and_diagram_do_not_count(self):
        self.write_page('<!--\n' + self.section(0, diagram_body='flowchart LR\n A---B') + '\n-->\n')
        self.rejected('topic-a')
        self.write_page(f'### {self.titles[0]}\n<!--\n$$x$$\n```mermaid\nA---B\n```\n-->\n```python\nfirst(1)\n```\n')
        self.rejected('unit-0')

    def test_other_sections_and_neighbor_units_cannot_supply_missing_formula(self):
        self.write_page(self.section(0, math_body='').replace('$$\n\n$$', '') +
                        '\n## 其他段落\n$$x=100$$\n')
        self.rejected('unit-0')

    def test_python_block_must_reference_whole_registered_function_name(self):
        self.write_page(self.section(0, python_body='firstly(1)'))
        self.rejected('unit-0')

    def test_python_comments_strings_and_syntax_errors_do_not_link_function(self):
        for body in ('# first(1)', '"first(1)"', 'def first(:', 'x = 1\n# first(1)'):
            self.write_page(self.section(0, python_body=body))
            self.rejected('unit-0')

    def test_valid_python_definition_or_call_links_registered_function(self):
        for body in ('def first(x):\n    return x + 1',
                     'async def first(x):\n    return x + 1',
                     'first(1)', 'demo.first(1)'):
            self.write_page(self.section(0, python_body=body))
            self.assertEqual(self.checked(), [])

    def test_literal_hash_in_registered_title_matches_page(self):
        self.titles[0] = '知识点一：C#'
        self.units[0]['title'] = self.titles[0]
        self.persist()
        self.write_page()
        self.assertEqual(self.checked(), [])

    def test_unclosed_fences_and_formula_are_reported_for_topic(self):
        page = self.root / 'wiki/topics/a.md'
        original = page.read_text()
        for tail in ('\n```python\nfirst(1)\n', '\n$$\nx=1\n'):
            page.write_text(original + tail)
            self.rejected('topic-a')

    def test_top_level_async_function_can_be_located_without_execution(self):
        self.write('examples/demo.py', 'raise RuntimeError("不得执行")\n' +
                   '\n'.join(f'async def {name}(x):\n    return x\n' for name in self.functions))
        self.assertEqual(self.checked(), [])

    def test_nested_function_class_method_and_comment_are_not_top_level_function(self):
        for first in ('def wrapper():\n    def first(x):\n        return x\n',
                      'class C:\n    def first(self, x):\n        return x\n', '# def first(x): pass\n'):
            self.write('examples/demo.py', first + '\ndef second(x): return x\ndef third(x): return x\n')
            self.rejected('unit-0')

    def test_unparseable_example_returns_error_list(self):
        self.write('examples/demo.py', 'def first(:\n')
        self.rejected('unit-0')

    def test_invalid_utf8_in_input_files_returns_error_list(self):
        for relative in ('knowledge/topics.json', 'wiki/topics/a.md', 'examples/demo.py'):
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(b'\xff\xfe')
            self.rejected()
            path.write_bytes(original)

    def test_topic_page_must_be_valid_typed_existing_file(self):
        for value in (None, [], {}, 5, '', '   ', 'wiki/missing.md', 'wiki/topics'):
            self.topics[0]['page'] = value
            self.persist()
            self.rejected('topic-a')

    def test_missing_non_python_or_non_file_example_is_rejected(self):
        self.write('examples/demo.txt', 'def first(x): return x\n')
        for value in ('examples/missing.py', 'examples/demo.txt', 'examples'):
            rows = copy.deepcopy(self.units)
            rows[0]['example'] = value
            self.save('knowledge/units.json', rows)
            self.rejected('unit-0')

    def test_outside_example_is_rejected_before_reading(self):
        outside = self.base / 'outside.py'
        outside.write_text('raise AssertionError("不得读取")')
        original_read = Path.read_text

        def guarded_read(path, *args, **kwargs):
            if path.resolve() == outside.resolve():
                raise AssertionError('越界示例在验证前被读取')
            return original_read(path, *args, **kwargs)

        for target in ('../outside.py', str(outside)):
            self.units[0]['example'] = target
            self.persist()
            with patch.object(Path, 'read_text', guarded_read):
                self.rejected('unit-0')

    def test_outside_topic_is_rejected_before_reading(self):
        outside = self.base / 'outside.md'
        outside.write_text(self.section(0) + self.section(1) + self.section(2))
        self.topics[0]['page'] = '../outside.md'
        self.persist()
        original_read = Path.read_text

        def guarded_read(path, *args, **kwargs):
            if path.resolve() == outside.resolve():
                raise AssertionError('越界主题在验证前被读取')
            return original_read(path, *args, **kwargs)

        with patch.object(Path, 'read_text', guarded_read):
            self.rejected('topic-a')

    def test_symlink_escape_is_rejected_before_reading(self):
        outside = self.base / 'outside.py'
        outside.write_text('def first(x): return x\n')
        (self.root / 'examples/link.py').symlink_to(outside)
        self.units[0]['example'] = 'examples/link.py'
        self.persist()
        original_read = Path.read_text

        def guarded_read(path, *args, **kwargs):
            if path.resolve() == outside.resolve():
                raise AssertionError('越界符号链接被读取')
            return original_read(path, *args, **kwargs)

        with patch.object(Path, 'read_text', guarded_read):
            self.rejected('unit-0')

    def test_invalid_example_path_character_returns_errors_instead_of_crashing(self):
        self.units[0]['example'] = 'examples/bad\x00.py'
        self.persist()
        self.rejected('unit-0')

    def test_invalid_topic_path_character_returns_errors_instead_of_crashing(self):
        self.topics[0]['page'] = 'wiki/bad\x00.md'
        self.persist()
        self.rejected('topic-a')

    def test_symlink_cycle_returns_errors_instead_of_crashing(self):
        (self.root / 'examples/cycle.py').symlink_to('cycle.py')
        self.units[0]['example'] = 'examples/cycle.py'
        self.persist()
        self.rejected('unit-0')

    def test_different_source_ids_with_same_url_do_not_count_as_two_sources(self):
        self.sources[1]['url'] = self.sources[0]['url']
        self.persist()
        self.rejected('topic-a')

    def test_empty_or_whitespace_strings_are_not_distinct_urls(self):
        self.sources[0]['url'] = ''
        self.sources[1]['url'] = '   '
        self.persist()
        self.rejected('topic-a')

    def test_missing_and_wrong_type_urls_cannot_supply_second_source(self):
        for value in (None, [], {}, 42):
            self.sources[1]['url'] = value
            self.persist()
            self.rejected('topic-a')
        del self.sources[1]['url']
        self.persist()
        self.rejected('topic-a')

    def test_cli_valid_fixture_root_exits_zero_and_does_not_write(self):
        before = self.snapshot()
        result = subprocess.run([sys.executable, '-B', str(Path(checker.__file__).resolve()), '--root', str(self.root)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip())
        self.assertEqual(self.snapshot(), before)

    def test_cli_structural_failure_exits_one_with_locatable_error(self):
        self.units[0]['function'] = 'missing_function'
        self.persist()
        before = self.snapshot()
        result = subprocess.run([sys.executable, '-B', str(Path(checker.__file__).resolve()), '--root', str(self.root)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('unit-0', result.stdout)
        self.assertNotIn('Traceback', result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)
