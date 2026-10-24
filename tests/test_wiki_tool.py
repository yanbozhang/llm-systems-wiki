"""维护工具行为测试。

规则来自 schema/维护工具契约.md 和已读取的技术方案。
格式、限额、退出码按首版契约；学习调度按学习体系契约验证。
磁盘写入均在 TemporaryDirectory；只读主题清单核对轮换契约。
网络只在 urllib 边界替换。
"""
import copy
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape

from scripts import wiki_tool as wiki


def atom(identity='paper-1', title='候选论文', url='https://example.org/paper', updated='2026-10-24T08:00:00Z'):
    identity_xml = '' if identity is None else '<id>' + escape(identity) + '</id>'
    update_xml = '' if updated is None else '<updated>' + escape(updated) + '</updated>'
    link_xml = '' if url is None else '<link href="' + escape(url, {'"': '&quot;'}) + '"/>'
    return ('<feed xmlns="http://www.w3.org/2005/Atom"><entry>' + identity_xml
            + '<title>' + escape(title) + '</title>' + link_xml + update_xml
            + '</entry></feed>').encode()


class TempCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()

    def save(self, relative, obj):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
        return path

    def fixture(self):
        self.topics = [
            {'id': 'topic-a', 'module': 'network', 'page': 'wiki/a.md'},
            {'id': 'topic-b', 'module': 'inference', 'page': 'wiki/b.md'},
            {'id': 'topic-c', 'module': 'knowledge', 'page': 'wiki/c.md'},
        ]
        self.sources = [{'id': 'source-a', 'version': 'snapshot-a', 'status': 'active'}]
        self.claims = [{'id': 'claim-a', 'topic': 'topic-a', 'status': 'source_statement',
                        'evidence': [{'source_id': 'source-a', 'source_version': 'snapshot-a'}]}]
        self.relations = [{'id': 'rel-a', 'from': 'topic-a', 'to': 'topic-b', 'type': 'prerequisite'}]
        for topic in self.topics:
            path = self.root / topic['page']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# 临时主题\n', encoding='utf-8')
        self.persist_fixture()

    def persist_fixture(self):
        self.save('knowledge/topics.json', self.topics)
        self.save('knowledge/claims.json', self.claims)
        self.save('knowledge/relations.json', self.relations)
        self.save('sources/manifest/sources.json', self.sources)

    def check_errors(self, text):
        self.persist_fixture()
        errors = wiki.check(self.root)
        self.assertIsInstance(errors, list)
        self.assertTrue(any(text in item for item in errors), errors)

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = wiki.main(list(args) + ['--root', str(self.root)])
        return code, stdout.getvalue(), stderr.getvalue()


class JsonTests(TempCase):
    def test_read_preserves_json_types_and_unicode(self):
        data = {'说明': ['中文', 7, None, False], '嵌套': {'值': 0}}
        path = self.save('input.json', data)
        self.assertEqual(wiki.read_json(path), data)

    def test_read_corrupt_json_rejected(self):
        path = self.root / 'input.json'
        path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            wiki.read_json(path)

    def test_read_missing_file_rejected(self):
        with self.assertRaises(FileNotFoundError):
            wiki.read_json(self.root / 'missing.json')

    def test_write_creates_parent_and_round_trips(self):
        path = self.root / 'nested/result.json'
        data = {'说明': '候选', 'seen': ['key-a']}
        wiki.write_json(path, data)
        self.assertEqual(json.loads(path.read_text()), data)
        self.assertEqual(list(path.parent.iterdir()), [path])

    def test_write_replace_failure_preserves_old_bytes(self):
        path = self.save('state.json', {'seen': ['old']})
        old = path.read_bytes()
        with patch.object(Path, 'replace', autospec=True, side_effect=OSError('模拟原子替换失败')):
            with self.assertRaises(OSError):
                wiki.write_json(path, {'seen': ['new']})
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_write_serialization_failure_preserves_old_bytes(self):
        path = self.save('state.json', {'seen': ['old']})
        old = path.read_bytes()
        with self.assertRaises(TypeError):
            wiki.write_json(path, {'invalid': object()})
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(list(self.root.iterdir()), [path])


class CheckTests(TempCase):
    def setUp(self):
        super().setUp()
        self.fixture()

    def test_valid_graph_sources_and_pages(self):
        self.assertEqual(wiki.check(self.root), [])

    def test_duplicate_topic_id(self):
        self.topics.append(copy.deepcopy(self.topics[0]))
        self.check_errors('重复 ID')

    def test_duplicate_claim_id(self):
        self.claims.append(copy.deepcopy(self.claims[0]))
        self.check_errors('重复 ID')

    def test_duplicate_relation_id(self):
        self.relations.append(copy.deepcopy(self.relations[0]))
        self.check_errors('重复 ID')

    def test_duplicate_source_id(self):
        self.sources.append(copy.deepcopy(self.sources[0]))
        self.check_errors('重复 ID')

    def test_non_array_collection(self):
        self.sources = {'id': 'not-a-list'}
        self.check_errors('必须是数组')

    def test_non_object_collection_row(self):
        self.topics.append(None)
        self.check_errors('有效 ID')

    def test_blank_id(self):
        self.topics[0]['id'] = '   '
        self.check_errors('有效 ID')

    def test_non_string_id(self):
        self.sources[0]['id'] = 42
        self.check_errors('有效 ID')

    def test_invalid_module(self):
        self.topics[0]['module'] = 'unknown'
        self.check_errors('非法模块')

    def test_missing_page(self):
        self.topics[0]['page'] = 'wiki/missing.md'
        self.check_errors('页面不存在')

    def test_shared_page_rejected(self):
        self.topics[1]['page'] = self.topics[0]['page']
        self.check_errors('页面重复')

    def test_page_parent_escape_rejected(self):
        (self.base / 'outside.md').write_text('# 库外')
        self.topics[0]['page'] = '../outside.md'
        self.check_errors('越界')

    def test_page_symlink_escape_rejected(self):
        outside = self.base / 'outside.md'
        outside.write_text('# 库外')
        (self.root / 'wiki/a.md').unlink()
        (self.root / 'wiki/a.md').symlink_to(outside)
        self.check_errors('越界')

    def test_invalid_page_type_returns_errors(self):
        self.topics[0]['page'] = None
        self.persist_fixture()
        self.assertIsInstance(errors := wiki.check(self.root), list)
        self.assertTrue(errors, '非字符串页面必须作为结构错误拒绝')

    def test_blank_page_returns_structure_errors(self):
        self.topics[0]['page'] = ' \t '
        self.persist_fixture()
        errors = wiki.check(self.root)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, '空白页面路径不能成为有效页面绑定')

    def test_unknown_claim_topic(self):
        self.claims[0]['topic'] = 'unknown'
        self.check_errors('未知主题')

    def test_claim_without_evidence(self):
        self.claims[0]['evidence'] = []
        self.check_errors('缺少证据')

    def test_claim_unknown_source(self):
        self.claims[0]['evidence'][0]['source_id'] = 'missing'
        self.check_errors('来源版本无效')

    def test_claim_mismatched_snapshot(self):
        self.claims[0]['evidence'][0]['source_version'] = 'another-snapshot'
        self.check_errors('来源版本无效')

    def test_claim_and_source_both_missing_version_rejected(self):
        del self.sources[0]['version']
        del self.claims[0]['evidence'][0]['source_version']
        self.persist_fixture()
        self.assertTrue(wiki.check(self.root), '缺少来源版本不能因两侧都为空而匹配成功')

    def test_claim_and_source_blank_version_rejected(self):
        self.sources[0]['version'] = ''
        self.claims[0]['evidence'][0]['source_version'] = ''
        self.persist_fixture()
        self.assertTrue(wiki.check(self.root), '空字符串不是有效来源快照身份')

    def test_whitespace_source_version_rejected(self):
        self.sources[0]['version'] = ' \t '
        self.claims[0]['evidence'][0]['source_version'] = ' \t '
        self.persist_fixture()
        self.assertTrue(wiki.check(self.root), '空白不能作为来源快照身份')

    def test_non_string_source_version_rejected(self):
        self.sources[0]['version'] = 7
        self.claims[0]['evidence'][0]['source_version'] = 7
        self.persist_fixture()
        self.assertTrue(wiki.check(self.root), '同值但非字符串的版本不能形成快照绑定')

    def test_withdrawn_source_rejected_for_active_claim(self):
        self.sources[0]['status'] = 'withdrawn'
        self.check_errors('撤回来源')

    def test_prerequisite_self_loop(self):
        self.relations[0]['to'] = 'topic-a'
        self.check_errors('有环')

    def test_prerequisite_three_node_cycle(self):
        self.relations += [
            {'id': 'rel-b', 'from': 'topic-b', 'to': 'topic-c', 'type': 'prerequisite'},
            {'id': 'rel-c', 'from': 'topic-c', 'to': 'topic-a', 'type': 'prerequisite'},
        ]
        self.check_errors('有环')

    def test_non_prerequisite_cycle_allowed(self):
        self.relations = [
            {'id': 'rel-a', 'from': 'topic-a', 'to': 'topic-b', 'type': 'related'},
            {'id': 'rel-b', 'from': 'topic-b', 'to': 'topic-a', 'type': 'related'},
        ]
        self.persist_fixture()
        self.assertEqual(wiki.check(self.root), [])

    def test_unknown_relation_endpoint(self):
        self.relations[0]['to'] = 'absent'
        self.check_errors('关系端点')

    def test_invalid_relation_type(self):
        self.relations[0]['type'] = 'invalid'
        self.check_errors('类型无效')

    def test_local_encoded_link_and_anchor_allowed(self):
        (self.root / 'wiki/空 白.md').write_text('# 名称')
        (self.root / 'wiki/a.md').write_text('[链接](%E7%A9%BA%20%E7%99%BD.md#名称)\n[页内](#名称)')
        self.assertEqual(wiki.check(self.root), [])

    def test_dangling_markdown_link_rejected(self):
        (self.root / 'wiki/a.md').write_text('[坏链接](missing.md)')
        self.assertTrue(any('断链' in x for x in wiki.check(self.root)))

    def test_link_escape_rejected(self):
        (self.base / 'outside.md').write_text('# 库外')
        (self.root / 'wiki/a.md').write_text('[库外](../../outside.md)')
        self.assertTrue(any('越界' in x for x in wiki.check(self.root)))

    def test_images_backtick_blocks_and_http_are_ignored(self):
        (self.root / 'wiki/a.md').write_text('![图](missing.png)\n```markdown\n[示例](missing.md)\n```\n[外部](https://example.org/no-network)')
        self.assertEqual(wiki.check(self.root), [])

    def test_tilde_code_blocks_are_ignored(self):
        (self.root / 'wiki/a.md').write_text('~~~markdown\n[示例](missing.md)\n~~~\n')
        self.assertEqual(wiki.check(self.root), [], '契约排除了代码块中的链接')

    def test_indented_code_blocks_are_ignored(self):
        (self.root / 'wiki/a.md').write_text('# 代码示例\n\n    [示例](missing.md)\n')
        self.assertEqual(wiki.check(self.root), [], '契约排除了代码块中的链接')

    def test_fence_contents_ignored_and_following_link_checked(self):
        (self.root / 'wiki/a.md').write_text(
            '````markdown\n```\n~~~\n[示例](example-missing.md)\n````\n'
            '[正文](outside-missing.md)\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('outside-missing.md', errors[0])

    def test_tab_indented_code_ignored_and_following_link_checked(self):
        (self.root / 'wiki/a.md').write_text(
            '# 代码示例\n\n\t[示例](example-missing.md)\n\n'
            '[正文](outside-missing.md)\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('outside-missing.md', errors[0])

    def test_html_comments_ignore_links_but_preserve_following_prose(self):
        (self.root / 'wiki/a.md').write_text(
            '<!-- 隐藏说明\n[注释链接](comment-missing.md)\n-->\n'
            '[正文链接](prose-missing.md)\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('prose-missing.md', errors[0])

    def test_fence_with_trailing_text_does_not_close_code(self):
        (self.root / 'wiki/a.md').write_text(
            '```markdown\n```仍在代码块\n[示例](example-missing.md)\n```\n'
            '[正文](prose-missing.md)\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('prose-missing.md', errors[0])

    def test_comment_marker_in_code_does_not_hide_following_link(self):
        # 围栏中展示注释起始符，不能把围栏外的真实正文一起删掉。
        (self.root / 'wiki/a.md').write_text(
            '```html\n<!--\n```\n[正文](prose-missing.md)\n'
            '<!-- 后续独立注释 -->\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('prose-missing.md', errors[0])

    def test_fence_inside_html_comment_does_not_hide_following_link(self):
        (self.root / 'wiki/a.md').write_text(
            '<!-- 注释中的围栏示例\n```markdown\n[隐藏](comment-missing.md)\n-->\n'
            '[正文](prose-missing.md)\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('prose-missing.md', errors[0])

    def test_multiple_inline_comments_preserve_surrounding_links(self):
        (self.root / 'wiki/a.md').write_text(
            '<!-- 前注释 -->[前正文](first-missing.md)<!-- 中间注释 -->'
            '[后正文](second-missing.md)<!-- 尾注释 -->\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any('first-missing.md' in error for error in errors), errors)
        self.assertTrue(any('second-missing.md' in error for error in errors), errors)

    def test_indented_comment_marker_does_not_hide_following_link(self):
        (self.root / 'wiki/a.md').write_text(
            '# 缩进代码示例\n\n    <!--\n\n[正文](prose-missing.md)\n'
            '<!-- 独立正文注释 -->\n', encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('prose-missing.md', errors[0])


class PlanTests(unittest.TestCase):
    def test_weekly_seven_modules_and_sunday_review(self):
        monday = date(2026, 10, 19)
        expected = ['network', 'training', 'inference', 'harness', 'knowledge', 'agents', 'benchmark']
        rows = [wiki.plan((monday + timedelta(days=i)).isoformat()) for i in range(7)]
        self.assertEqual([r['module'] for r in rows], expected)
        self.assertTrue(all(r['reason'] for r in rows))
        self.assertTrue(all(r['topic'] for r in rows))
        self.assertEqual([r['review_due'] for r in rows], [False] * 6 + [True])

    def test_registered_topic_counts_define_rotation_and_repeat(self):
        start = date(2026, 10, 19)
        root = Path(__file__).resolve().parents[1]
        topics = json.loads((root / 'knowledge/topics.json').read_text(encoding='utf-8'))
        modules = json.loads((root / 'knowledge/modules.json').read_text(encoding='utf-8'))
        for module in modules:
            expected = [t['id'] for t in topics if t['module'] == module['id']]
            rows = [wiki.plan(start + timedelta(days=module['weekday'] + 7 * week))
                    for week in range(len(expected) + 1)]
            self.assertEqual([row['topic'] for row in rows[:-1]], expected)
            self.assertEqual(rows[0]['topic'], rows[-1]['topic'])
            self.assertEqual(len({row['module'] for row in rows}), 1)

    def test_rotation_uses_registered_topics_in_their_modules(self):
        # AGENTS.md指定此清单为主题身份来源，不从wiki.TOPICS生成期望值。
        manifest = Path(__file__).resolve().parents[1] / 'knowledge/topics.json'
        registered = json.loads(manifest.read_text(encoding='utf-8'))
        expected = {}
        for topic in registered:
            expected.setdefault(topic['module'], set()).add(topic['id'])
        scheduled = {}
        monday = date(2026, 10, 19)
        for offset in range(7 * max(map(len, expected.values()))):
            row = wiki.plan(monday + timedelta(days=offset))
            scheduled.setdefault(row['module'], set()).add(row['topic'])
        self.assertEqual(scheduled, expected)

    def test_year_boundary_and_leap_day(self):
        self.assertEqual(wiki.plan('2026-12-31')['module'], 'harness')
        self.assertEqual(wiki.plan('2027-01-01')['module'], 'knowledge')
        self.assertEqual(wiki.plan('2028-02-29')['module'], 'training')
        self.assertEqual(wiki.plan('2026-10-12')['module'], 'network')

    def test_invalid_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            wiki.plan('2026-02-29')

    def test_compact_date_rejected(self):
        with self.assertRaises(ValueError, msg='契约要求 YYYY-MM-DD'):
            wiki.plan('20261024')

    def test_week_date_rejected(self):
        with self.assertRaises(ValueError, msg='契约要求 YYYY-MM-DD'):
            wiki.plan('2026-W43-6')


class CurriculumCase(TempCase):
    """契约：schema/学习体系契约.md；所有知识包都在临时目录内。"""
    HEADINGS = ('学习目标', '前置知识', '基本机制', '推导或示例', '适用条件', '实践任务', '掌握标准')
    CONTENT = '学习者需要明确输入输出以及成立条件通过具体例子验证推导并记录误差与实践结果'

    def setUp(self):
        super().setUp()
        self.modules, self.topics, self.capabilities = [], [], []
        for day, mod in enumerate(('network', 'training', 'inference', 'harness',
                                   'knowledge', 'agents', 'benchmark')):
            page = f'wiki/modules/{mod}.md'
            self.write_page(page, '# 模块\n')
            self.modules.append({'id': mod, 'title': mod, 'weekday': day, 'page': page})
            for number in (1, 2):
                self.add_topic(mod, f'{mod}-{number}')
            for level in ('understand', 'derive', 'build', 'evaluate'):
                self.capabilities.append({'id': f'{mod}-{level}', 'module': mod, 'level': level,
                                          'outcome': '解释条件并核验结果', 'deliverable': '提交推导和误差分析',
                                          'topic_ids': [f'{mod}-1']})
        self.sources = [{'id': 'source-a', 'version': 'snapshot-a', 'status': 'active'}]
        self.claims = [{'id': 'claim-a', 'topic': 'network-1', 'status': 'source_statement',
                        'evidence': [{'source_id': 'source-a', 'source_version': 'snapshot-a'}]}]
        self.relations = []
        self.resources = [{'id': 'resource-a', 'title': '公开课程入口', 'url': 'https://example.org/course',
                           'module_ids': ['network', 'benchmark'], 'kind': 'course',
                           'reading_scope': '只读课程介绍与教学大纲', 'access': 'public',
                           'reviewed_at': '2026-10-24', 'source_id': 'source-a'}]
        self.persist_curriculum()

    def write_page(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def topic_body(self, changed_heading=None, replacement=None, omit=False):
        return '# 临时知识单元\n\n' + ''.join(
            f'## {heading}\n{replacement if heading == changed_heading else self.CONTENT}\n\n'
            for heading in self.HEADINGS if not (omit and heading == changed_heading))

    def add_topic(self, module, identity):
        topic = {'id': identity, 'module': module, 'title': identity,
                 'page': f'wiki/topics/{identity}.md', 'learning_objectives': [f'能够解释{identity}的边界'],
                 'depth': 'worked', 'practice_status': 'designed', 'deliverable': f'{identity}的验证记录'}
        self.topics.append(topic)
        self.write_page(topic['page'], self.topic_body())
        return topic

    def persist_curriculum(self):
        self.persist_fixture()
        self.save('knowledge/modules.json', self.modules)
        self.save('knowledge/capabilities.json', self.capabilities)
        self.save('sources/learning-resources.json', self.resources)

    def assert_curriculum_rejected(self):
        self.persist_curriculum()
        errors = wiki.check(self.root, curriculum=True)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, '非法课程知识包应返回结构错误')
        self.assertTrue(all(isinstance(error, str) and error for error in errors))

    def assert_plan_rejected(self):
        self.persist_curriculum()
        with self.assertRaises(ValueError):
            wiki.plan('2026-10-19', self.root)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}


class CurriculumPlanTests(CurriculumCase):
    def test_config_weekday_order_is_authoritative(self):
        self.modules[0]['id'] = 'architecture'
        for topic in self.topics:
            if topic['module'] == 'network':
                topic['module'] = 'architecture'
        self.modules[0]['weekday'], self.modules[1]['weekday'] = 1, 0
        self.modules.reverse()
        self.persist_curriculum()
        start = date(2026, 10, 19)
        rows = [wiki.plan(start + timedelta(days=offset), self.root) for offset in range(7)]
        self.assertEqual([row['module'] for row in rows],
                         ['training', 'architecture', 'inference', 'harness', 'knowledge', 'agents', 'benchmark'])
        self.assertEqual([row['review_due'] for row in rows], [False] * 6 + [True])

    def test_topics_rotate_in_registration_order_beyond_four(self):
        # 五主题且刻意非字母排序，识别写死四周或额外排序。
        self.topics = [t for t in self.topics if t['module'] != 'network']
        expected = ['z-last', 'a-first', 'middle', 'fourth', 'fifth']
        for identity in expected:
            self.add_topic('network', identity)
        self.persist_curriculum()
        start = date(2026, 10, 19)
        rows = [wiki.plan(start + timedelta(weeks=week), self.root) for week in range(-1, 6)]
        self.assertEqual([row['topic'] for row in rows], [expected[-1]] + expected + [expected[0]])

    def test_added_topic_is_in_next_rotation(self):
        self.assertEqual(wiki.plan('2026-11-02', self.root)['topic'], 'network-1')
        self.add_topic('network', 'new-topic')
        self.persist_curriculum()
        self.assertEqual(wiki.plan('2026-11-02', self.root)['topic'], 'new-topic')
        self.assertEqual(wiki.plan('2026-11-09', self.root)['topic'], 'network-1')

    def test_plan_returns_learning_fields_from_selected_topic(self):
        row = wiki.plan('2026-10-26', self.root)
        self.assertEqual(set(row), {'date', 'module', 'topic', 'reason', 'review_due',
                                    'learning_objective', 'deliverable'})
        self.assertEqual({key: row[key] for key in ('date', 'module', 'topic', 'review_due')},
                         {'date': '2026-10-26', 'module': 'network', 'topic': 'network-2', 'review_due': False})
        # 字段来自所选主题；首目标和 deliverable 的具体映射为实施假设。
        self.assertEqual(row['learning_objective'], '能够解释network-2的边界')
        self.assertEqual(row['deliverable'], 'network-2的验证记录')
        self.assertTrue(row['reason'])

    def test_empty_selected_module_rejected(self):
        self.topics = [t for t in self.topics if t['module'] != 'network']
        self.assert_plan_rejected()

    def test_duplicate_module_rejected(self):
        self.modules[1]['id'] = 'network'
        self.assert_plan_rejected()

    def test_six_modules_rejected(self):
        self.modules.pop()
        self.assert_plan_rejected()

    def test_missing_benchmark_rejected(self):
        self.modules[-1]['id'] = 'review'
        self.assert_plan_rejected()

    def test_duplicate_weekday_rejected(self):
        self.modules[1]['weekday'] = 0
        self.assert_plan_rejected()

    def test_string_weekday_rejected(self):
        self.modules[0]['weekday'] = '0'
        self.assert_plan_rejected()

    def test_float_weekday_rejected(self):
        self.modules[0]['weekday'] = 0.0
        self.assert_plan_rejected()

    def test_boolean_weekday_rejected(self):
        self.modules[0]['weekday'] = False
        self.assert_plan_rejected()

    def test_out_of_range_weekday_rejected(self):
        self.modules[0]['weekday'] = 7
        self.assert_plan_rejected()

    def test_missing_module_title_rejected(self):
        del self.modules[0]['title']
        self.assert_plan_rejected()

    def test_missing_module_page_rejected(self):
        del self.modules[0]['page']
        self.assert_plan_rejected()

    def test_module_collection_must_be_array(self):
        self.modules = {'network': self.modules[0]}
        self.assert_plan_rejected()

    def test_non_object_module_rejected(self):
        self.modules[0] = None
        self.assert_plan_rejected()

    def test_blank_module_id_rejected(self):
        self.modules[0]['id'] = ' \t '
        self.assert_plan_rejected()

    def test_topic_collection_must_be_array(self):
        self.topics = {'network-1': self.topics[0]}
        self.assert_plan_rejected()

    def test_blank_topic_id_rejected(self):
        self.topics[0]['id'] = ' '
        self.assert_plan_rejected()

    def test_plan_missing_modules_does_not_use_legacy_schedule(self):
        (self.root / 'knowledge/modules.json').unlink()
        code, _, _ = self.cli('plan', '--date', '2026-10-19')
        self.assertNotEqual(code, 0)

    def test_plan_cli_uses_custom_root_and_does_not_write(self):
        before = self.snapshot()
        code, stdout, stderr = self.cli('plan', '--date', '2026-10-25')
        self.assertEqual(code, 0, stderr)
        row = json.loads(stdout)
        self.assertEqual((row['module'], row['topic'], row['review_due']), ('benchmark', 'benchmark-1', True))
        self.assertEqual(self.snapshot(), before)


class CurriculumCheckTests(CurriculumCase):
    def test_complete_curriculum_is_valid_offline_and_read_only(self):
        before = self.snapshot()
        with patch.object(wiki.urllib.request, 'build_opener', autospec=True) as network:
            self.assertEqual(wiki.check(self.root, curriculum=True), [])
            code, stdout, stderr = self.cli('check', '--curriculum')
        self.assertEqual(code, 0, stderr)
        self.assertIn('通过', stdout)
        network.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_default_check_uses_configured_module_ids(self):
        self.modules[0]['id'] = 'architecture'
        for topic in self.topics:
            if topic['module'] == 'network':
                topic['module'] = 'architecture'
        self.persist_curriculum()
        self.assertEqual(wiki.check(self.root), [])

    def test_default_check_rejects_module_not_in_manifest(self):
        self.modules[0]['id'] = 'architecture'
        self.persist_curriculum()
        self.assertTrue(wiki.check(self.root))

    def test_legacy_check_accepts_benchmark_and_keeps_graph_checks(self):
        (self.root / 'knowledge/modules.json').unlink()
        self.assertEqual(wiki.check(self.root), [])
        self.relations = [{'id': 'broken', 'from': 'network-1', 'to': 'absent', 'type': 'prerequisite'}]
        self.persist_fixture()
        self.assertTrue(wiki.check(self.root), '兼容模式仍须拒绝坏引用')

    def test_strict_check_requires_module_manifest(self):
        (self.root / 'knowledge/modules.json').unlink()
        self.assertTrue(wiki.check(self.root, curriculum=True))

    def test_invalid_manifest_is_returned_as_check_error(self):
        self.modules[0]['weekday'] = False
        self.persist_curriculum()
        self.assertIsInstance(errors := wiki.check(self.root), list)
        self.assertTrue(errors)

    def test_default_check_rejects_missing_module_page(self):
        # 契约“模块与轮换”：模块页面必须位于仓库内且存在。
        (self.root / self.modules[0]['page']).unlink()
        self.assertTrue(wiki.check(self.root), '缺失模块页面应在默认结构检查中被识别')

    def test_default_check_rejects_module_page_escape(self):
        (self.base / 'outside.md').write_text('# 库外模块\n', encoding='utf-8')
        self.modules[0]['page'] = '../outside.md'
        self.persist_curriculum()
        self.assertTrue(wiki.check(self.root), '默认结构检查也必须拒绝库外模块页面')

    def test_default_check_rejects_module_page_symlink_escape(self):
        outside = self.base / 'outside.md'
        outside.write_text('# 库外模块\n', encoding='utf-8')
        page = self.root / self.modules[0]['page']
        page.unlink()
        page.symlink_to(outside)
        self.assertTrue(wiki.check(self.root), '符号链接不能绕过默认模块路径边界')

    def test_strict_check_rejects_module_page_escape(self):
        (self.base / 'outside.md').write_text('# 库外模块\n', encoding='utf-8')
        self.modules[0]['page'] = '../outside.md'
        self.assert_curriculum_rejected()

    def test_strict_check_rejects_module_page_symlink_escape(self):
        outside = self.base / 'outside.md'
        outside.write_text('# 库外模块\n', encoding='utf-8')
        page = self.root / self.modules[0]['page']
        page.unlink()
        page.symlink_to(outside)
        self.assert_curriculum_rejected()

    def test_missing_learning_objectives_rejected(self):
        del self.topics[0]['learning_objectives']
        self.assert_curriculum_rejected()

    def test_empty_learning_objectives_rejected(self):
        self.topics[0]['learning_objectives'] = []
        self.assert_curriculum_rejected()

    def test_blank_learning_objective_rejected(self):
        self.topics[0]['learning_objectives'] = [' \t ']
        self.assert_curriculum_rejected()

    def test_invalid_depth_rejected(self):
        self.topics[0]['depth'] = 'mastered'
        self.assert_curriculum_rejected()

    def test_invalid_practice_status_rejected(self):
        self.topics[0]['practice_status'] = 'unknown'
        self.assert_curriculum_rejected()

    def test_reproduced_requires_record(self):
        self.topics[0]['depth'] = 'reproduced'
        self.assert_curriculum_rejected()

    def test_executed_requires_record(self):
        self.topics[0]['practice_status'] = 'executed'
        self.assert_curriculum_rejected()

    def test_real_record_allows_executed_and_reproduced(self):
        self.write_page('experiments/record.md', '# 实验记录\n输入、执行过程和实际输出均已记录。\n')
        self.topics[0].update(depth='reproduced', practice_status='executed', experiment_record='experiments/record.md')
        self.persist_curriculum()
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_experiment_record_escape_rejected(self):
        (self.base / 'outside.md').write_text('# 库外记录\n', encoding='utf-8')
        self.topics[0].update(depth='reproduced', experiment_record='../outside.md')
        self.assert_curriculum_rejected()

    def test_missing_required_section_rejected(self):
        self.write_page(self.topics[0]['page'], self.topic_body('实践任务', omit=True))
        self.assert_curriculum_rejected()

    def test_every_required_section_is_enforced(self):
        for heading in self.HEADINGS:
            self.write_page(self.topics[0]['page'], self.topic_body(heading, omit=True))
            self.assertTrue(wiki.check(self.root, curriculum=True), f'缺少{heading}必须拒绝')

    def test_placeholder_only_section_rejected(self):
        # 契约明确“不是只有标题或占位符”，不能靠重复占位符凑满长度。
        self.write_page(self.topics[0]['page'], self.topic_body('基本机制', 'TODO 待补充 ' * 12))
        self.assert_curriculum_rejected()

    def test_code_fence_headings_do_not_replace_real_sections(self):
        example = '# 示例文本\n\n```markdown\n' + self.topic_body() + '\n```\n'
        self.write_page(self.topics[0]['page'], example)
        self.assert_curriculum_rejected()

    def test_tilde_fence_cannot_supply_sections(self):
        self.write_page(self.topics[0]['page'], '# 示例\n\n~~~markdown\n' + self.topic_body() + '\n~~~\n')
        self.assert_curriculum_rejected()

    def test_indented_code_cannot_fill_section(self):
        self.write_page(self.topics[0]['page'], self.topic_body('基本机制', '    ' + self.CONTENT))
        self.assert_curriculum_rejected()

    def test_comments_cannot_fill_section(self):
        self.write_page(self.topics[0]['page'], self.topic_body('基本机制', '<!--\n' + self.CONTENT + '\n-->'))
        self.assert_curriculum_rejected()

    def test_html_tags_cannot_fill_section(self):
        self.write_page(self.topics[0]['page'], self.topic_body('基本机制', '<span class="long-placeholder-tag"></span>' * 3))
        self.assert_curriculum_rejected()

    def test_placeholder_variants_cannot_fill_section(self):
        for placeholder in ('TODO', 'tbd', 'FIXME', 'placeholder', '待补充', '待完善', '待填写', '占位符'):
            self.write_page(self.topics[0]['page'], self.topic_body('基本机制', (placeholder + ' ') * 24))
            self.assertTrue(wiki.check(self.root, curriculum=True), f'不能靠重复{placeholder}凑字数')

    def test_substantive_section_allows_code_and_placeholder_mentions(self):
        content = self.CONTENT + '\n\n使用TODO跟踪尚未核验的问题。\n\n```python\nprint(1)\n```\n'
        self.write_page(self.topics[0]['page'], self.topic_body('基本机制', content))
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_comment_with_fence_does_not_hide_real_sections(self):
        comment = '<!--\n```markdown\n## 只是注释中的标题\n-->\n'
        self.write_page(self.topics[0]['page'], comment + self.topic_body())
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_blank_section_rejected(self):
        self.write_page(self.topics[0]['page'], self.topic_body('基本机制', ' \t\n '))
        self.assert_curriculum_rejected()

    def test_section_with_nineteen_characters_rejected(self):
        self.write_page(self.topics[0]['page'], self.topic_body('推导或示例', '推' * 19))
        self.assert_curriculum_rejected()

    def test_section_with_twenty_characters_allowed(self):
        self.write_page(self.topics[0]['page'], self.topic_body('推导或示例', '推' * 20))
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_markup_only_section_rejected(self):
        self.write_page(self.topics[0]['page'], self.topic_body('适用条件', '* ` # > - \n' * 20))
        self.assert_curriculum_rejected()

    def test_unregistered_topic_file_rejected(self):
        self.write_page('wiki/topics/orphan.md', self.topic_body())
        self.assert_curriculum_rejected()

    def test_nested_unregistered_topic_file_rejected(self):
        self.write_page('wiki/topics/extra/orphan.md', self.topic_body())
        self.assert_curriculum_rejected()

    def test_nested_registered_topic_allowed(self):
        nested = 'wiki/topics/extra/network-1.md'
        destination = self.root / nested
        destination.parent.mkdir()
        (self.root / self.topics[0]['page']).rename(destination)
        self.topics[0]['page'] = nested
        self.persist_curriculum()
        self.assertEqual(wiki.check(self.root, curriculum=True), [], '嵌套主题已经登记，应正常通过')

    def test_capability_file_required(self):
        (self.root / 'knowledge/capabilities.json').unlink()
        self.assertTrue(wiki.check(self.root, curriculum=True))

    def test_capability_collection_must_be_array(self):
        self.capabilities = {'id': 'not-an-array'}
        self.assert_curriculum_rejected()

    def test_capability_id_unique(self):
        self.capabilities.append(copy.deepcopy(self.capabilities[0]))
        self.assert_curriculum_rejected()

    def test_capability_id_required(self):
        del self.capabilities[0]['id']
        self.assert_curriculum_rejected()

    def test_each_module_requires_all_four_levels(self):
        self.capabilities = [c for c in self.capabilities if c['id'] != 'benchmark-evaluate']
        self.assert_curriculum_rejected()

    def test_capability_level_must_be_known(self):
        self.capabilities[0]['level'] = 'mastered'
        self.assert_curriculum_rejected()

    def test_capability_module_must_be_registered(self):
        self.capabilities[0]['module'] = 'missing'
        self.assert_curriculum_rejected()

    def test_capability_topics_must_exist(self):
        self.capabilities[0]['topic_ids'] = ['network-1', 'missing']
        self.assert_curriculum_rejected()

    def test_capability_requires_own_module_topic(self):
        self.capabilities[0]['topic_ids'] = ['training-1']
        self.assert_curriculum_rejected()

    def test_capability_allows_cross_module_prerequisite(self):
        self.capabilities[0]['topic_ids'] = ['training-1', 'network-1']
        self.persist_curriculum()
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_capability_outcome_required(self):
        self.capabilities[0]['outcome'] = ' '
        self.assert_curriculum_rejected()

    def test_capability_deliverable_required(self):
        del self.capabilities[0]['deliverable']
        self.assert_curriculum_rejected()

    def test_resource_file_required(self):
        (self.root / 'sources/learning-resources.json').unlink()
        self.assertTrue(wiki.check(self.root, curriculum=True))

    def test_resource_collection_must_be_array(self):
        self.resources = {'id': 'not-an-array'}
        self.assert_curriculum_rejected()

    def test_resource_id_unique(self):
        self.resources.append(copy.deepcopy(self.resources[0]))
        self.assert_curriculum_rejected()

    def test_resource_id_required(self):
        self.resources[0]['id'] = ' '
        self.assert_curriculum_rejected()

    def test_resource_requires_https(self):
        self.resources[0]['url'] = 'http://example.org/course'
        self.assert_curriculum_rejected()

    def test_resource_requires_hostname(self):
        self.resources[0]['url'] = 'https:///course'
        self.assert_curriculum_rejected()

    def test_resource_modules_must_exist(self):
        self.resources[0]['module_ids'] = ['network', 'missing']
        self.assert_curriculum_rejected()

    def test_resource_requires_source(self):
        self.resources[0]['source_id'] = 'missing'
        self.assert_curriculum_rejected()

    def test_resource_reading_scope_required(self):
        self.resources[0]['reading_scope'] = ' \t '
        self.assert_curriculum_rejected()

    def test_resource_title_required(self):
        del self.resources[0]['title']
        self.assert_curriculum_rejected()

    def test_resource_kind_required(self):
        del self.resources[0]['kind']
        self.assert_curriculum_rejected()

    def test_resource_access_required(self):
        del self.resources[0]['access']
        self.assert_curriculum_rejected()

    def test_resource_reviewed_at_required(self):
        del self.resources[0]['reviewed_at']
        self.assert_curriculum_rejected()

    def test_cli_strict_failure_differs_from_legacy_check(self):
        self.topics[0]['learning_objectives'] = []
        self.persist_curriculum()
        before = self.snapshot()
        self.assertEqual(self.cli('check')[0], 0)
        code, stdout, _ = self.cli('check', '--curriculum')
        self.assertEqual(code, 1)
        self.assertTrue(stdout)
        self.assertEqual(self.snapshot(), before)


class FeedTests(unittest.TestCase):
    def test_atom_fields_and_unread_status(self):
        item, = wiki.parse_feed(atom(), 'feed-a')
        self.assertEqual({k: item[k] for k in ['feed_id', 'entry_id', 'title', 'url', 'updated']}, {
            'feed_id': 'feed-a', 'entry_id': 'paper-1', 'title': '候选论文',
            'url': 'https://example.org/paper', 'updated': '2026-10-24T08:00:00Z'})
        self.assertEqual(item['status'], 'pending_read')
        self.assertEqual(item['reading_scope'], 'feed_metadata')
        self.assertRegex(item['id'], r'^[0-9a-f]{64}$')

    def test_rss_guid_title_link_and_date(self):
        xml = b'<rss version="2.0"><channel><item><guid>stable-guid</guid><title>RSS item</title><link>http://example.org/rss</link><pubDate>Sat, 24 Oct 2026 08:00:00 GMT</pubDate></item></channel></rss>'
        item, = wiki.parse_feed(xml, 'rss-a')
        self.assertEqual(item['entry_id'], 'stable-guid')
        self.assertEqual(item['title'], 'RSS item')
        self.assertEqual(item['url'], 'http://example.org/rss')
        self.assertEqual(item['updated'], 'Sat, 24 Oct 2026 08:00:00 GMT')

    def test_atom_alternate_link_selected(self):
        xml = atom().replace(b'<link ', b'<link rel="self" href="https://example.org/api"/><link ')
        item, = wiki.parse_feed(xml, 'feed-a')
        self.assertEqual(item['url'], 'https://example.org/paper')

    def test_link_is_fallback_identity(self):
        item, = wiki.parse_feed(atom(identity=None), 'feed-a')
        self.assertEqual(item['entry_id'], 'https://example.org/paper')

    def test_missing_date_stays_unknown(self):
        item, = wiki.parse_feed(atom(updated=None), 'feed-a')
        self.assertIsNone(item['updated'])

    def test_missing_link_skipped(self):
        self.assertEqual(wiki.parse_feed(atom(url=None), 'feed-a'), [])

    def test_non_http_link_skipped(self):
        self.assertEqual(wiki.parse_feed(atom(url='file:///tmp/paper'), 'feed-a'), [])

    def test_http_link_without_host_skipped(self):
        self.assertEqual(wiki.parse_feed(atom(url='https:///paper'), 'feed-a'), [])

    def test_userinfo_link_skipped(self):
        self.assertEqual(wiki.parse_feed(atom(url='https://reader@example.org/paper'), 'feed-a'), [])

    def test_duplicate_entries_deduplicated(self):
        xml = atom()
        entry = xml[xml.index(b'<entry>'):xml.index(b'</entry>') + len(b'</entry>')]
        duplicate = xml.replace(b'</feed>', entry + b'</feed>')
        self.assertEqual(wiki.parse_feed(duplicate, 'feed-a'), wiki.parse_feed(xml, 'feed-a'))

    def test_each_material_field_revision_changes_key(self):
        original, = wiki.parse_feed(atom(), 'feed-a')
        alternatives = [atom(identity='paper-2'), atom(title='修订标题'),
                        atom(url='https://example.org/other'), atom(updated='2026-10-25T00:00:00Z')]
        keys = [wiki.parse_feed(xml, 'feed-a')[0]['id'] for xml in alternatives]
        keys.append(wiki.parse_feed(atom(), 'feed-b')[0]['id'])
        self.assertEqual(len(set(keys + [original['id']])), 6)

    def test_whitespace_normalization_is_idempotent(self):
        clean = wiki.parse_feed(atom(), 'feed-a')
        padded = wiki.parse_feed(atom(identity=' paper-1 ', title=' 候选论文 ', url=' https://example.org/paper ', updated=' 2026-10-24T08:00:00Z '), 'feed-a')
        self.assertEqual(padded, clean)

    def test_unsupported_root_fails_instead_of_empty_feed(self):
        with self.assertRaises(ValueError):
            wiki.parse_feed(b'<html/>', 'feed-a')

    def test_malformed_xml_fails_instead_of_empty_feed(self):
        from xml.etree.ElementTree import ParseError
        with self.assertRaises(ParseError):
            wiki.parse_feed(b'<feed', 'feed-a')

    def test_empty_atom_feed_is_valid(self):
        self.assertEqual(wiki.parse_feed(b'<feed xmlns="http://www.w3.org/2005/Atom"/>', 'feed-a'), [])


class FakeResponse(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.read_limits = []

    def read(self, size=-1):
        self.read_limits.append(size)
        return super().read(size)


class NetworkCase(unittest.TestCase):
    def network(self, responses):
        opened = []
        response_objects = []
        class Opener:
            def open(self, request, timeout):
                opened.append((request, timeout))
                body = responses[request.full_url]
                if isinstance(body, Exception):
                    raise body
                response = FakeResponse(body)
                response_objects.append(response)
                return response
        patcher = patch.object(wiki.urllib.request, 'build_opener', autospec=True, return_value=Opener())
        factory = patcher.start()
        self.addCleanup(patcher.stop)
        return opened, response_objects, factory


class FetchTests(NetworkCase):
    def test_https_request_bounds_and_no_credentials(self):
        opened, responses, _ = self.network({'https://example.org/feed': b'<rss/>'})
        self.assertEqual(wiki.fetch_feed('https://example.org/feed'), b'<rss/>')
        self.assertEqual(len(opened), 1)
        request, timeout = opened[0]
        self.assertEqual(timeout, 20)
        self.assertEqual(request.get_method(), 'GET')
        self.assertIsNone(request.data)
        self.assertNotIn('authorization', {k.lower() for k in request.headers})
        self.assertNotIn('cookie', {k.lower() for k in request.headers})
        self.assertEqual(responses[0].read_limits, [2 * 1024 * 1024 + 1])
        self.assertTrue(responses[0].closed)

    def test_body_at_size_limit_allowed(self):
        body = b'x' * (2 * 1024 * 1024)
        self.network({'https://example.org/feed': body})
        self.assertEqual(wiki.fetch_feed('https://example.org/feed'), body)

    def test_body_over_size_limit_rejected(self):
        _, responses, _ = self.network({'https://example.org/feed': b'x' * (2 * 1024 * 1024 + 1)})
        with self.assertRaises(ValueError):
            wiki.fetch_feed('https://example.org/feed')
        self.assertTrue(responses[0].closed)

    def reject_url(self, url):
        opened, _, _ = self.network({url: b'never'})
        with self.assertRaises(ValueError):
            wiki.fetch_feed(url)
        self.assertEqual(opened, [])

    def test_http_rejected_before_network(self):
        self.reject_url('http://example.org/feed')

    def test_userinfo_rejected_before_network(self):
        self.reject_url('https://user@example.org/feed')

    def test_localhost_rejected_before_network(self):
        self.reject_url('https://LOCALHOST/feed')

    def test_ipv4_rejected_before_network(self):
        self.reject_url('https://127.0.0.1/feed')

    def test_ipv6_rejected_before_network(self):
        self.reject_url('https://[::1]/feed')

    def test_missing_hostname_rejected_before_network(self):
        self.reject_url('https:///feed')

    def test_redirect_does_not_fetch_unregistered_target(self):
        from email.message import Message
        from urllib.error import HTTPError
        from urllib.response import addinfourl

        headers = Message()
        headers['Location'] = 'https://unregistered.example.org/feed'
        response = addinfourl(io.BytesIO(b''), headers, 'https://example.org/feed', 302)
        response.msg = 'Found'
        self.addCleanup(response.close)
        # 保留真实opener和重定向处理器，只替换HTTPS传输边界。
        with patch.object(wiki.urllib.request.HTTPSHandler, 'https_open',
                          autospec=True, return_value=response) as transport:
            with self.assertRaises(HTTPError) as raised:
                wiki.fetch_feed('https://example.org/feed')
        self.addCleanup(raised.exception.close)
        self.assertEqual(raised.exception.code, 302)
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(transport.call_args.args[1].full_url, 'https://example.org/feed')


class DiscoverTests(NetworkCase):
    NOW = '2026-10-25T00:00:00+08:00'
    FEEDS = [{'id': 'feed-a', 'url': 'https://example.org/a'}, {'id': 'feed-b', 'url': 'https://example.org/b'}]

    def test_new_candidate_is_changed_without_mutating_input(self):
        state = {'seen': [], 'checked': {'old': 'earlier'}, 'metadata': {'keep': [1]}}
        original = copy.deepcopy(state)
        self.network({'https://example.org/a': atom()})
        report, new_state = wiki.discover(self.FEEDS[:1], state, now=self.NOW)
        self.assertEqual(report['status'], 'changed')
        self.assertEqual(len(report['candidates']), 1)
        self.assertEqual(new_state['seen'], [report['candidates'][0]['id']])
        self.assertEqual(new_state['checked'], {'old': 'earlier', 'feed-a': self.NOW})
        new_state['metadata']['keep'].append(2)
        self.assertEqual(state, original)

    def test_repeat_is_unchanged_and_advances_success_check(self):
        self.network({'https://example.org/a': atom()})
        first, state = wiki.discover(self.FEEDS[:1], {}, now=self.NOW)
        second, updated = wiki.discover(self.FEEDS[:1], state, now='2026-10-26T00:00:00+08:00')
        self.assertEqual(second['status'], 'unchanged')
        self.assertEqual(second['candidates'], [])
        self.assertEqual(updated['seen'], state['seen'])
        self.assertNotEqual(updated['checked'], state['checked'])
        self.assertEqual(first['candidates'][0]['reading_scope'], 'feed_metadata')

    def test_revision_survives_previous_identity(self):
        versions = iter([atom(), atom(title='修订')])
        _, state = wiki.discover(self.FEEDS[:1], {}, fetcher=lambda _: next(versions), now=self.NOW)
        report, new_state = wiki.discover(self.FEEDS[:1], state, fetcher=lambda _: next(versions), now=self.NOW)
        self.assertEqual(report['status'], 'changed')
        self.assertEqual(len(new_state['seen']), 2)
        self.assertEqual(report['candidates'][0]['title'], '修订')

    def test_duplicate_feed_entries_do_not_repeat_candidate(self):
        self.network({'https://example.org/a': atom()})
        report, state = wiki.discover([self.FEEDS[0], self.FEEDS[0]], {}, now=self.NOW)
        self.assertEqual(len(report['candidates']), 1)
        self.assertEqual([f['new_count'] for f in report['feeds']], [1, 0])
        self.assertEqual(len(state['seen']), 1)

    def test_transport_failure_keeps_checkpoint(self):
        self.network({'https://example.org/a': OSError('来源暂时不可读')})
        state = {'seen': ['previous'], 'checked': {'feed-a': 'previous-time'}}
        report, updated = wiki.discover(self.FEEDS[:1], state, now=self.NOW)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['candidates'], [])
        self.assertEqual(updated, state)
        self.assertIn('不可读', report['feeds'][0]['error'])

    def test_parse_failure_keeps_checkpoint(self):
        self.network({'https://example.org/a': b'<html/>'})
        state = {'seen': [], 'checked': {'feed-a': 'old'}}
        report, updated = wiki.discover(self.FEEDS[:1], state, now=self.NOW)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(updated, state)
        self.assertEqual(report['feeds'][0]['status'], 'error')

    def test_failed_first_feed_does_not_block_later_feed(self):
        opened, _, _ = self.network({'https://example.org/a': OSError('临时失败'), 'https://example.org/b': atom()})
        report, updated = wiki.discover(self.FEEDS, {'checked': {'feed-a': 'old'}, 'seen': []}, now=self.NOW)
        self.assertEqual([r.full_url for r, _ in opened], [f['url'] for f in self.FEEDS])
        self.assertEqual(report['status'], 'partial_failure')
        self.assertEqual(updated['checked'], {'feed-a': 'old', 'feed-b': self.NOW})
        self.assertEqual([r['feed_id'] for r in report['candidates']], ['feed-b'])

    def test_partial_failure_never_becomes_unchanged(self):
        self.network({'https://example.org/a': b'<feed xmlns="http://www.w3.org/2005/Atom"/>',
                      'https://example.org/b': OSError('失败')})
        report, updated = wiki.discover(self.FEEDS, {}, now=self.NOW)
        self.assertEqual(report['status'], 'partial_failure')
        self.assertEqual(report['candidates'], [])
        self.assertEqual(updated['checked'], {'feed-a': self.NOW})

    def test_empty_feed_list_has_no_changes(self):
        report, state = wiki.discover([], {'seen': ['old'], 'checked': {}}, now=self.NOW)
        self.assertEqual(report['status'], 'unchanged')
        self.assertEqual(report['feeds'], [])
        self.assertEqual(state['seen'], ['old'])

    def test_invalid_feed_row_does_not_block_other_sources(self):
        opened, _, _ = self.network({'https://example.org/a': atom(), 'https://example.org/b': atom()})
        report, state = wiki.discover([{'url': 'https://example.org/a'}, self.FEEDS[1]], {}, now=self.NOW)
        self.assertEqual(report['status'], 'partial_failure')
        self.assertEqual([r['status'] for r in report['feeds']], ['error', 'ok'])
        self.assertEqual([r['feed_id'] for r in report['candidates']], ['feed-b'])
        self.assertEqual(state['checked'], {'feed-b': self.NOW})
        self.assertEqual([request.full_url for request, _ in opened], ['https://example.org/b'])

    def assert_invalid_feed_is_isolated(self, invalid_row):
        opened, _, _ = self.network({'https://example.org/b': atom()})
        original = {'seen': ['old'], 'checked': {'earlier-feed': 'old-time'}}
        state = copy.deepcopy(original)
        report, updated = wiki.discover([invalid_row, self.FEEDS[1]], state, now=self.NOW)
        self.assertEqual(report['status'], 'partial_failure')
        self.assertEqual([row['status'] for row in report['feeds']], ['error', 'ok'])
        self.assertTrue(report['feeds'][0]['error'])
        self.assertEqual([item['feed_id'] for item in report['candidates']], ['feed-b'])
        self.assertEqual(updated['checked'], {'earlier-feed': 'old-time', 'feed-b': self.NOW})
        self.assertEqual(set(updated['seen']), {'old', report['candidates'][0]['id']})
        self.assertEqual([request.full_url for request, _ in opened], ['https://example.org/b'])
        self.assertEqual(state, original)

    def test_blank_feed_id_does_not_block_other_sources(self):
        self.assert_invalid_feed_is_isolated({'id': '', 'url': 'https://example.org/a'})

    def test_whitespace_feed_id_does_not_block_other_sources(self):
        self.assert_invalid_feed_is_isolated({'id': ' \t ', 'url': 'https://example.org/a'})

    def test_non_string_feed_id_does_not_block_other_sources(self):
        self.assert_invalid_feed_is_isolated({'id': 7, 'url': 'https://example.org/a'})

    def test_non_object_feed_row_does_not_block_other_sources(self):
        self.assert_invalid_feed_is_isolated(None)

    def test_all_invalid_feed_rows_fail_without_advancing_checkpoint(self):
        opened, _, _ = self.network({})
        state = {'seen': ['old'], 'checked': {'feed-a': 'old-time'}}
        original = copy.deepcopy(state)
        report, updated = wiki.discover([None, {'id': ''}], state, now=self.NOW)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual([row['status'] for row in report['feeds']], ['error', 'error'])
        self.assertEqual(report['candidates'], [])
        self.assertEqual(updated, original)
        self.assertEqual(state, original)
        self.assertEqual(opened, [])


class CliTests(TempCase, NetworkCase):
    def setUp(self):
        super().setUp()
        self.fixture()
        # 新版 plan 必须读取传入 root 的七模块配置，旧 check fixture 保持独立。
        modules = []
        for day, module in enumerate(('network', 'training', 'inference', 'harness',
                                      'knowledge', 'agents', 'benchmark')):
            page = f'wiki/modules/{module}.md'
            path = self.root / page
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# 模块页面\n', encoding='utf-8')
            modules.append({'id': module, 'title': module, 'weekday': day, 'page': page})
            if not any(topic['module'] == module for topic in self.topics):
                self.topics.append({'id': module + '-topic', 'module': module, 'page': f'wiki/{module}.md'})
                (self.root / f'wiki/{module}.md').write_text('# 测试主题\n', encoding='utf-8')
        self.save('knowledge/modules.json', modules)
        self.persist_fixture()
        self.out = self.base / 'output'
        self.save('sources/manifest/feeds.json', [{'id': 'feed-a', 'url': 'https://example.org/a'}])
        note = self.root / 'user-notes/private.md'
        note.parent.mkdir()
        note.write_text('用户自己的笔记', encoding='utf-8')

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def initial_state(self):
        self.out.mkdir()
        path = self.out / 'state.json'
        path.write_text('{"seen": ["old"], "checked": {"feed-a": "old-time"}}')
        return path, path.read_bytes()

    def test_check_success_does_not_write(self):
        before = self.snapshot()
        code, stdout, stderr = self.cli('check')
        self.assertEqual(code, 0)
        self.assertIn('通过', stdout)
        self.assertEqual(stderr, '')
        self.assertEqual(self.snapshot(), before)

    def test_check_structure_error_exits_one(self):
        self.relations[0]['to'] = 'topic-a'
        self.persist_fixture()
        code, stdout, _ = self.cli('check')
        self.assertEqual(code, 1)
        self.assertIn('有环', stdout)

    def test_plan_explicit_date_does_not_write(self):
        before = self.snapshot()
        code, stdout, stderr = self.cli('plan', '--date', '2026-10-24')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)['module'], 'agents')
        self.assertEqual(stderr, '')
        self.assertEqual(self.snapshot(), before)

    def test_plan_invalid_date_exits_nonzero(self):
        code, _, stderr = self.cli('plan', '--date', '2026-02-29')
        self.assertNotEqual(code, 0)
        self.assertIn('失败', stderr)

    def test_default_date_uses_shanghai_midnight_boundary(self):
        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 24, 16, 1, tzinfo=timezone.utc).astimezone(tz)
        with patch.object(wiki, 'datetime', FrozenDateTime):
            code, stdout, _ = self.cli('plan')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)['date'], '2026-10-25')
        self.assertEqual(json.loads(stdout)['module'], 'benchmark')
        self.assertIs(json.loads(stdout)['review_due'], True)

    def test_discover_writes_candidate_before_state_and_is_idempotent(self):
        self.network({'https://example.org/a': atom()})
        before = self.snapshot()
        real_replace = Path.replace
        committed = []
        def track_replace(source, target):
            committed.append(Path(target))
            if Path(target).name == 'state.json':
                reports = list((self.out / 'runs').glob('*.json'))
                self.assertTrue(reports, '写检查点时必须已存在候选日志')
                self.assertEqual(len(json.loads(reports[0].read_text())['candidates']), 1)
            return real_replace(source, target)
        with patch.object(Path, 'replace', track_replace):
            code, stdout, stderr = self.cli('discover', '--output', str(self.out))
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), {'status': 'changed', 'new_count': 1})
        self.assertEqual(committed[-1], self.out / 'state.json')
        report = json.loads((self.out / 'latest.json').read_text())
        state = json.loads((self.out / 'state.json').read_text())
        self.assertEqual(state['seen'], [report['candidates'][0]['id']])
        code, stdout, _ = self.cli('discover', '--output', str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {'status': 'unchanged', 'new_count': 0})
        self.assertEqual(len(json.loads((self.out / 'state.json').read_text())['seen']), 1)
        self.assertEqual(self.snapshot(), before)

    def test_partial_failure_saves_report_and_exits_one(self):
        self.save('sources/manifest/feeds.json', [
            {'id': 'feed-a', 'url': 'https://example.org/a'},
            {'id': 'feed-b', 'url': 'https://example.org/b'},
        ])
        self.network({'https://example.org/a': atom(), 'https://example.org/b': OSError('暂不可读')})
        code, stdout, _ = self.cli('discover', '--output', str(self.out))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout)['status'], 'partial_failure')
        report = json.loads((self.out / 'latest.json').read_text())
        state = json.loads((self.out / 'state.json').read_text())
        self.assertEqual(len(report['candidates']), 1)
        self.assertEqual(report['feeds'][1]['status'], 'error')
        self.assertEqual(set(state['checked']), {'feed-a'})

    def test_invalid_feed_row_persists_error_and_valid_candidate(self):
        self.save('sources/manifest/feeds.json', [None, {'id': 'feed-b', 'url': 'https://example.org/b'}])
        opened, _, _ = self.network({'https://example.org/b': atom()})
        before = self.snapshot()
        code, stdout, _ = self.cli('discover', '--output', str(self.out))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout), {'status': 'partial_failure', 'new_count': 1})
        report = json.loads((self.out / 'latest.json').read_text())
        state = json.loads((self.out / 'state.json').read_text())
        self.assertEqual([row['status'] for row in report['feeds']], ['error', 'ok'])
        self.assertTrue(report['feeds'][0]['error'])
        self.assertEqual(set(state['checked']), {'feed-b'})
        self.assertEqual(state['seen'], [report['candidates'][0]['id']])
        self.assertEqual(len(list((self.out / 'runs').glob('*.json'))), 1)
        self.assertEqual([request.full_url for request, _ in opened], ['https://example.org/b'])
        self.assertEqual(self.snapshot(), before)

    def test_discover_default_output_is_inside_root(self):
        self.network({'https://example.org/a': atom()})
        code, stdout, _ = self.cli('discover')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), {'status': 'changed', 'new_count': 1})
        output = self.root / 'candidates'
        report = json.loads((output / 'latest.json').read_text())
        state = json.loads((output / 'state.json').read_text())
        self.assertEqual(state['seen'], [report['candidates'][0]['id']])
        self.assertEqual(set(state['checked']), {'feed-a'})
        self.assertEqual(len(list((output / 'runs').glob('*.json'))), 1)
        self.assertFalse(self.out.exists())

    def test_all_feeds_fail_keeps_previous_check_and_saves_failure(self):
        state_path, old = self.initial_state()
        self.network({'https://example.org/a': OSError('读取失败')})
        code, stdout, _ = self.cli('discover', '--output', str(self.out))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout)['status'], 'failed')
        self.assertEqual(json.loads(state_path.read_text()), json.loads(old))
        self.assertEqual(json.loads((self.out / 'latest.json').read_text())['feeds'][0]['status'], 'error')

    def failure_on_replace(self, target_kind):
        state_path, old = self.initial_state()
        self.network({'https://example.org/a': atom()})
        real_replace = Path.replace
        def failing_replace(source, target):
            target = Path(target)
            if (target_kind == 'run' and target.parent.name == 'runs') or target.name == target_kind:
                raise OSError('模拟候选或状态落盘失败')
            return real_replace(source, target)
        with patch.object(Path, 'replace', failing_replace):
            code, _, stderr = self.cli('discover', '--output', str(self.out))
        self.assertNotEqual(code, 0)
        self.assertIn('落盘失败', stderr)
        self.assertEqual(state_path.read_bytes(), old)

    def test_candidate_log_write_failure_does_not_advance_state(self):
        self.failure_on_replace('run')

    def test_latest_write_failure_does_not_advance_state(self):
        self.failure_on_replace('latest.json')

    def test_state_replace_failure_keeps_old_state_and_candidate(self):
        self.failure_on_replace('state.json')
        reports = list((self.out / 'runs').glob('*.json'))
        self.assertEqual(len(reports), 1)
        self.assertEqual(len(json.loads(reports[0].read_text())['candidates']), 1)

    def test_corrupt_state_json_not_overwritten(self):
        path, _ = self.initial_state()
        path.write_text('{broken')
        old = path.read_bytes()
        opened, _, _ = self.network({})
        code, _, stderr = self.cli('discover', '--output', str(self.out))
        self.assertNotEqual(code, 0)
        self.assertTrue(stderr)
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(opened, [])

    def test_corrupt_feeds_json_not_overwrite_state(self):
        path, old = self.initial_state()
        (self.root / 'sources/manifest/feeds.json').write_text('not json')
        code, _, _ = self.cli('discover', '--output', str(self.out))
        self.assertNotEqual(code, 0)
        self.assertEqual(path.read_bytes(), old)

    def test_invalid_state_shape_returns_nonzero_without_overwrite(self):
        path, _ = self.initial_state()
        path.write_text('[]')
        old = path.read_bytes()
        try:
            code, _, _ = self.cli('discover', '--output', str(self.out))
        except (AttributeError, TypeError, ValueError, KeyError):
            # 契约仅承诺 CLI 非零退出，未承诺 main 必须捕获每种结构错误。
            # __main__ 中未捕获的异常同样令进程非零退出。
            code = 1
        self.assertNotEqual(code, 0)
        self.assertEqual(path.read_bytes(), old)
