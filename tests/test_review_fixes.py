"""报告缺陷定向回归；契约见 schema/维护工具契约.md。"""
import copy
import json
from pathlib import Path
from unittest.mock import patch

from scripts import wiki_tool as wiki
from tests.test_wiki_tool import CurriculumCase, NetworkCase, TempCase, atom


class LocalhostFetchTests(NetworkCase):
    def assert_localhost_rejected(self, url):
        opened, _, _ = self.network({url: b'never'})
        with self.assertRaises(ValueError):
            wiki.fetch_feed(url)
        self.assertEqual(opened, [], '本地主机必须在打开网络连接前拒绝')

    def test_trailing_dot_localhost_rejected_before_open(self):
        # 报告 57d8f586a7c9 的原始触发输入。
        self.assert_localhost_rejected('https://localhost./feed')

    def test_localhost_subdomain_rejected_before_open(self):
        self.assert_localhost_rejected('https://service.localhost/feed')

    def test_nested_mixed_case_trailing_dot_localhost_rejected_before_open(self):
        self.assert_localhost_rejected('https://API.Child.LoCaLhOsT.:443/feed')

    def test_localhost_label_in_public_domain_allowed(self):
        url = 'https://localhost.example.org/feed'
        body = b'public feed'
        opened, responses, _ = self.network({url: body})
        self.assertEqual(wiki.fetch_feed(url), body)
        self.assertEqual([request.full_url for request, _ in opened], [url])
        self.assertTrue(responses[0].closed)

    def test_mixed_case_public_domain_with_trailing_dot_allowed(self):
        url = 'https://Feed.Example.Org./feed'
        body = b'public feed'
        opened, _, _ = self.network({url: body})
        self.assertEqual(wiki.fetch_feed(url), body)
        self.assertEqual([request.full_url for request, _ in opened], [url])

    def test_discover_rejects_localhost_and_continues_public_feed(self):
        # 保留 discover → 默认 fetch_feed → 解析 的真实调用链。
        public = 'https://example.org/feed'
        opened, _, _ = self.network({'https://localhost./feed': b'never', public: atom()})
        state = {'seen': [], 'checked': {'local': 'previous'}}
        before = copy.deepcopy(state)
        report, updated = wiki.discover(
            [{'id': 'local', 'url': 'https://localhost./feed'}, {'id': 'public', 'url': public}],
            state, now='2026-10-24T12:00:00+08:00')
        self.assertEqual(report['status'], 'partial_failure')
        self.assertEqual([(row['feed_id'], row['status']) for row in report['feeds']],
                         [('local', 'error'), ('public', 'ok')])
        self.assertTrue(report['feeds'][0]['error'])
        self.assertEqual([request.full_url for request, _ in opened], [public])
        self.assertEqual([row['feed_id'] for row in report['candidates']], ['public'])
        self.assertEqual(updated['checked'], {'local': 'previous', 'public': report['checked_at']})
        self.assertEqual(state, before)


class LocalhostCliTests(TempCase, NetworkCase):
    def test_cli_rejects_localhost_without_network_or_checkpoint_advance(self):
        url = 'https://Feed.LOCALHOST./feed'
        self.save('sources/manifest/feeds.json', [{'id': 'local', 'url': url}])
        state = {'seen': [], 'checked': {'local': 'previous'}}
        self.save('candidates/state.json', state)
        opened, _, _ = self.network({url: b'never'})
        code, stdout, stderr = self.cli('discover')
        self.assertEqual(code, 1, stderr)
        self.assertEqual(json.loads(stdout)['status'], 'failed')
        self.assertEqual(opened, [])
        self.assertEqual(json.loads((self.root / 'candidates/state.json').read_text()), state)
        report = json.loads((self.root / 'candidates/latest.json').read_text())
        self.assertEqual(report['candidates'], [])
        self.assertEqual(report['feeds'][0]['status'], 'error')


class EvidenceShapeTests(TempCase):
    def setUp(self):
        super().setUp()
        self.fixture()

    def assert_bad_shape_returns_errors(self, evidence):
        self.claims[0]['evidence'] = evidence
        self.persist_fixture()
        errors = wiki.check(self.root)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, '非法证据形状应返回结构错误')
        self.assertTrue(all(isinstance(error, str) and error for error in errors))

    def test_string_evidence_returns_errors(self):
        self.assert_bad_shape_returns_errors('source-a')

    def test_number_evidence_returns_errors(self):
        self.assert_bad_shape_returns_errors(42)

    def test_object_evidence_returns_errors(self):
        self.assert_bad_shape_returns_errors({'source_id': 'source-a', 'source_version': 'snapshot-a'})

    def test_null_evidence_returns_errors(self):
        self.assert_bad_shape_returns_errors(None)

    def test_numeric_evidence_items_return_errors(self):
        self.assert_bad_shape_returns_errors([1, 2])

    def test_null_evidence_item_returns_errors(self):
        self.assert_bad_shape_returns_errors([None])

    def test_mixed_evidence_preserves_source_and_graph_checks(self):
        # 非对象元素前后均保留合法对象；后面的版本错误和关系错误必须继续检查。
        self.claims[0]['evidence'] = [
            {'source_id': 'source-a', 'source_version': 'snapshot-a'},
            'invalid',
            {'source_id': 'source-a', 'source_version': 'wrong-snapshot'},
        ]
        self.relations[0]['to'] = 'missing-topic'
        self.persist_fixture()
        errors = wiki.check(self.root)
        self.assertTrue(any('证据' in error for error in errors), errors)
        self.assertTrue(any('来源版本无效' in error for error in errors), errors)
        self.assertTrue(any('关系端点' in error for error in errors), errors)

    def test_cli_invalid_evidence_returns_one_without_traceback(self):
        self.claims[0]['evidence'] = 'invalid'
        self.persist_fixture()
        code, stdout, stderr = self.cli('check')
        self.assertEqual(code, 1)
        self.assertTrue(stdout.strip())
        self.assertEqual(stderr, '')

    def test_invalid_evidence_container_does_not_skip_later_claims(self):
        self.claims[0]['evidence'] = 'invalid'
        self.claims.append({'id': 'claim-b', 'topic': 'topic-b', 'evidence': [
            {'source_id': 'source-a', 'source_version': 'wrong-snapshot'}]})
        self.relations[0]['to'] = 'missing-topic'
        self.persist_fixture()
        errors = wiki.check(self.root)
        self.assertTrue(any('claim-a' in error and '证据' in error for error in errors), errors)
        self.assertTrue(any('claim-b' in error and '来源版本无效' in error for error in errors), errors)
        self.assertTrue(any('关系端点' in error for error in errors), errors)


class MarkdownLinkTests(TempCase):
    def setUp(self):
        super().setUp()
        self.fixture()

    def assert_target_checked(self, filename, markdown):
        target = self.root / 'wiki' / filename
        target.write_text('# 链接目标\n', encoding='utf-8')
        (self.root / 'wiki/a.md').write_text(markdown, encoding='utf-8')
        self.assertEqual(wiki.check(self.root), [], '合法行内链接不能误报断链')
        target.unlink()
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('断链', errors[0], '不能通过忽略该语法来使合法链接变绿')

    def test_balanced_parentheses_destination(self):
        self.assert_target_checked('文档(v2).md', '[说明](文档(v2).md)')

    def test_nested_parentheses_destination(self):
        self.assert_target_checked('文档(v(2)).md', '[说明](文档(v(2)).md)')

    def test_double_quoted_title_separated_from_destination(self):
        self.assert_target_checked('文档.md', '[说明](文档.md "另一个不存在的文档.md")')

    def test_single_quoted_title_separated_from_destination(self):
        self.assert_target_checked('文档.md', "[说明](文档.md '另一个不存在的文档.md')")

    def test_parenthesized_title_separated_from_destination(self):
        self.assert_target_checked('文档.md', '[说明](文档.md (另一个不存在的文档.md))')

    def test_escaped_parentheses_destination(self):
        self.assert_target_checked('文档(v2).md', r'[说明](文档\(v2\).md)')

    def test_angle_destination_with_spaces_and_title(self):
        self.assert_target_checked('文档 v2.md', '[说明](<文档 v2.md> "说明标题")')

    def test_encoded_destination_with_title_and_anchor(self):
        self.assert_target_checked('文档(v2).md', '[说明](%E6%96%87%E6%A1%A3%28v2%29.md#标题 "说明")')

    def test_supported_destinations_still_reject_repository_escape(self):
        outside = self.base / 'outside(v2).md'
        outside.write_text('# 库外文件\n', encoding='utf-8')
        links = [
            '[平衡](../../outside(v2).md)',
            '[尖括号](<../../outside(v2).md> "标题")',
            r'[转义](../../outside\(v2\).md)',
            "[编码](%2e%2e/%2e%2e/outside%28v2%29.md '标题')",
        ]
        (self.root / 'wiki/a.md').write_text('\n'.join(links), encoding='utf-8')
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), len(links), errors)
        self.assertTrue(all('越界' in error for error in errors), errors)


class TopicBoundaryTests(CurriculumCase):
    def move_topic(self, destination, declared=None):
        target = self.root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        (self.root / self.topics[0]['page']).rename(target)
        self.topics[0]['page'] = declared or destination
        self.persist_curriculum()
        return target

    def assert_boundary_rejected(self, curriculum):
        errors = wiki.check(self.root, curriculum=curriculum)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, 'wiki外的真实主题文件不能成为有效页面')
        self.assertTrue(all(isinstance(error, str) and error for error in errors))
        return errors

    def test_default_check_rejects_complete_topic_in_docs(self):
        self.move_topic('docs/topic.md')
        self.assert_boundary_rejected(False)

    def test_curriculum_check_rejects_complete_topic_in_docs(self):
        self.move_topic('docs/topic.md')
        self.assert_boundary_rejected(True)

    def test_normalized_parent_path_outside_wiki_rejected(self):
        self.move_topic('docs/topic.md', 'wiki/../docs/topic.md')
        self.assert_boundary_rejected(False)
        self.assert_boundary_rejected(True)

    def test_symlink_outside_wiki_is_not_registered(self):
        original = self.root / self.topics[0]['page']
        target = self.root / 'docs/topic.md'
        target.parent.mkdir()
        original.rename(target)
        original.symlink_to(target)
        self.assert_boundary_rejected(False)
        errors = self.assert_boundary_rejected(True)
        self.assertTrue(any('主题文件未登记' in error for error in errors), errors)

    def test_wiki_root_topic_remains_valid_for_both_checks(self):
        self.move_topic('wiki/network-1.md')
        self.assertEqual(wiki.check(self.root), [])
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_normalized_path_into_wiki_remains_valid(self):
        (self.root / 'docs').mkdir()
        self.topics[0]['page'] = 'docs/../wiki/topics/network-1.md'
        self.persist_curriculum()
        self.assertEqual(wiki.check(self.root), [])
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_symlink_with_real_target_inside_wiki_remains_valid(self):
        original = self.root / self.topics[0]['page']
        target = self.root / 'wiki/shared-topic.md'
        original.rename(target)
        original.symlink_to(target)
        self.assertEqual(wiki.check(self.root), [])
        self.assertEqual(wiki.check(self.root, curriculum=True), [])

    def test_cli_curriculum_rejects_topic_in_docs(self):
        self.move_topic('docs/topic.md')
        code, stdout, stderr = self.cli('check', '--curriculum')
        self.assertEqual(code, 1)
        self.assertTrue(stdout.strip())
        self.assertEqual(stderr, '')

    def test_curriculum_does_not_read_outside_wiki_as_topic_body(self):
        outside = self.move_topic('docs/topic.md')
        # 单独观察既有课程入口的文件读取；通用链接扫描不属于此正文准入检查。
        original_read = Path.read_text
        reads = []

        def read_file(path, *args, **kwargs):
            reads.append(path.resolve())
            return original_read(path, *args, **kwargs)

        with patch.object(Path, 'read_text', autospec=True, side_effect=read_file):
            wiki.curriculum_errors(self.root,
                {topic['id']: topic for topic in self.topics},
                {source['id']: source for source in self.sources}, self.modules)
        self.assertNotIn(outside.resolve(), reads, 'wiki外页面不能当课程主题正文读取')
        self.assertIn((self.root / self.topics[1]['page']).resolve(), reads,
                      '正常主题仍应执行真实正文检查')


class ModuleScheduleTests(CurriculumCase):
    def move_benchmark_to_monday(self):
        # 保持全部weekday合法且唯一，只破坏契约规定的周日Benchmark。
        self.modules[0]['weekday'], self.modules[-1]['weekday'] = 6, 0
        self.persist_curriculum()

    def test_load_modules_rejects_benchmark_on_monday(self):
        self.move_benchmark_to_monday()
        with self.assertRaises(ValueError):
            wiki.load_modules(self.root)

    def test_curriculum_check_rejects_benchmark_on_monday(self):
        self.move_benchmark_to_monday()
        errors = wiki.check(self.root, curriculum=True)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors)

    def test_default_check_rejects_benchmark_on_monday(self):
        self.move_benchmark_to_monday()
        self.assertTrue(wiki.check(self.root))

    def test_sunday_plan_rejects_benchmark_on_monday(self):
        self.move_benchmark_to_monday()
        with self.assertRaises(ValueError):
            wiki.plan('2026-10-25', self.root)

    def test_cli_sunday_plan_rejects_benchmark_on_monday(self):
        self.move_benchmark_to_monday()
        code, stdout, stderr = self.cli('plan', '--date', '2026-10-25')
        self.assertEqual(code, 1)
        self.assertEqual(stdout, '')
        self.assertTrue(stderr.strip())

    def test_load_modules_accepts_reordered_other_weekdays(self):
        self.modules[0]['weekday'], self.modules[1]['weekday'] = 1, 0
        self.modules.reverse()
        self.persist_curriculum()
        loaded = wiki.load_modules(self.root)
        self.assertEqual([row['weekday'] for row in loaded], list(range(7)))
        self.assertEqual([row['id'] for row in loaded],
                         ['training', 'network', 'inference', 'harness', 'knowledge', 'agents', 'benchmark'])
