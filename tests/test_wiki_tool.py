"""维护工具行为测试。

规则来自 schema/维护工具契约.md 和已读取的技术方案。
本地契约中的格式、限额、退出码和四周周期作为首版设计假设验证。
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


class PlanTests(unittest.TestCase):
    def test_weekly_six_modules_and_sunday_review(self):
        monday = date(2026, 10, 19)
        expected = ['network', 'training', 'inference', 'harness', 'knowledge', 'agents', 'review']
        rows = [wiki.plan((monday + timedelta(days=i)).isoformat()) for i in range(7)]
        self.assertEqual([r['module'] for r in rows], expected)
        self.assertTrue(all(r['reason'] for r in rows))
        self.assertTrue(all(r['topic'] for r in rows[:6]))
        self.assertIsNone(rows[6]['topic'])

    def test_four_week_topics_rotate_and_repeat(self):
        start = date(2026, 10, 19)
        for offset in range(6):
            rows = [wiki.plan(start + timedelta(days=offset + 7 * week)) for week in range(5)]
            self.assertEqual(len({row['topic'] for row in rows[:4]}), 4)
            self.assertEqual(rows[0]['topic'], rows[4]['topic'])
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
        for offset in range(28):
            if offset % 7 == 6:
                continue
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
        self.assertEqual(json.loads(stdout)['module'], 'review')

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
