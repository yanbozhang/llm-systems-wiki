"""来源资料库契约的行为测试；只在临时仓库写入，网络在 DNS/HTTP 边界隔离。"""
import copy
from contextlib import redirect_stdout
import hashlib
import http.client
import io
import json
from pathlib import Path
import re
import socket
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

from scripts import source_library as library
from tests.test_wiki_tool import TempCase


LIMIT = 20 * 1024 * 1024  # schema/来源资料库契约.md§本地原文
PUBLIC_URL = 'https://papers.example.org/article'


def addresses(*ips):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in ips]


class Response(io.BytesIO):
    def __init__(self, body=b'public source bytes', content_type='text/plain'):
        super().__init__(body)
        self.headers = {'Content-Type': content_type}
        self.requested_sizes = []

    def read(self, size=-1):
        self.requested_sizes.append(size)
        return super().read(size)


class SourceCase(TempCase):
    def setUp(self):
        super().setUp()
        self.sources = [
            {'id': 'paper-a', 'title': '论文甲', 'url': PUBLIC_URL,
             'version': 'declared-text-v1', 'text_sha256': '1' * 64,
             'native_version': 'author-v3', 'reading_scope': '摘要',
             'locator': 'abstract', 'status': 'active'},
            {'id': 'code-b', 'title': '源码乙', 'url': 'https://code.example.org/source',
             'version': 'declared-code-v2', 'text_sha256': '2' * 64,
             'native_version': 'commit-v2', 'reading_scope': '单文件', 'status': 'active'},
        ]
        self.topics = [
            {'id': 'topic-a', 'title': '网络', 'module': 'network', 'page': 'wiki/topics/a.md'},
            {'id': 'topic-b', 'title': '推理', 'module': 'inference', 'page': 'wiki/topics/b.md'},
        ]
        self.claims = [{'id': 'claim-a', 'topic': 'topic-a', 'evidence': [
            {'source_id': 'paper-a', 'source_version': 'declared-text-v1'}]}]
        self.units = [{'id': 'unit-b', 'topic': 'topic-b', 'source_ids': ['paper-a']}]
        self.save('sources/manifest/sources.json', self.sources)
        self.save('knowledge/topics.json', self.topics)
        self.save('knowledge/claims.json', self.claims)
        self.save('knowledge/units.json', self.units)
        self.dns = self.enterContext(patch('socket._socket.getaddrinfo', return_value=addresses('8.8.8.8')))
        self.opener = Mock(spec=urllib.request.OpenerDirector)
        self.opener.open.side_effect = AssertionError('测试未配置HTTP响应')
        self.build_opener = self.enterContext(patch.object(library.urllib.request, 'build_opener', return_value=self.opener))

    def folder(self, sid='paper-a'):
        return self.root / 'sources/library' / sid

    def archive(self, sid='paper-a'):
        return json.loads((self.folder(sid) / 'archive.json').read_text())

    def store_archive(self, value, sid='paper-a'):
        self.save(f'sources/library/{sid}/archive.json', value)

    def capture(self, body=b'raw bytes independent of declared text', source=None):
        source = source or self.sources[0]
        fetcher = Mock(return_value={'body': body, 'url': source['url'], 'content_type': 'text/plain'})
        result = library.capture_one(self.root, source, fetcher=fetcher)
        return result, fetcher

    def saved(self):
        library.materialize(self.root)
        self.capture()
        archive = self.archive()
        return archive, self.root / archive['captures'][0]['cache_file']

    def check_has_error(self, local=False):
        errors = library.check_library(self.root, local=local)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, '契约要求拒绝损坏或不一致的资料库')

    def command(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = library.main([*args, '--root', str(self.root)])
        return code, output.getvalue()


class DirectoryTests(SourceCase):
    def test_materialize_indexes_all_sources_without_changing_identity(self):
        authoritative = ['sources/manifest/sources.json', 'knowledge/claims.json', 'knowledge/units.json']
        before = {name: (self.root / name).read_bytes() for name in authoritative}
        index = library.materialize(self.root)
        self.assertEqual({row['id'] for row in index}, {'paper-a', 'code-b'})
        self.assertEqual(library.read_json(self.root / 'sources/library/index.json'), index)
        for source in self.sources:
            folder = self.folder(source['id'])
            self.assertTrue((folder / 'README.md').is_file())
            self.assertEqual(library.read_json(folder / 'source.json'), source)
            card = (folder / 'README.md').read_text()
            for value in (source['title'], source['url'], source['reading_scope'], source['version'], source['native_version']):
                self.assertIn(value, card)
            self.assertEqual(self.archive(source['id'])['status'], 'not_requested')
        self.assertEqual({name: (self.root / name).read_bytes() for name in authoritative}, before)
        self.assertFalse((self.root / 'sources/.local').exists())

    def test_topic_bindings_merge_claims_units_and_frontiers_without_duplicates(self):
        self.save('knowledge/frontiers.json', [{'id': 'frontier-a', 'source_ids': ['paper-a', 'code-b'], 'topic_ids': ['topic-b']}])
        rows = {row['id']: row for row in library.materialize(self.root)}
        self.assertEqual(set(rows['paper-a']['topic_ids']), {'topic-a', 'topic-b'})
        self.assertEqual(len(rows['paper-a']['topic_ids']), 2)
        self.assertEqual(set(rows['paper-a']['module_ids']), {'network', 'inference'})
        self.assertEqual(rows['code-b']['topic_ids'], ['topic-b'])

    def test_repeat_index_preserves_archive_history_and_original_bytes(self):
        _, cached = self.saved()
        before = (self.folder() / 'archive.json').read_bytes(), cached.read_bytes()
        library.materialize(self.root)
        library.materialize(self.root)
        self.assertEqual(((self.folder() / 'archive.json').read_bytes(), cached.read_bytes()), before)

    def test_valid_id_alphabet_is_accepted(self):
        self.sources[0]['id'] = '9paper.a_b-c'
        self.save('sources/manifest/sources.json', self.sources)
        library.materialize(self.root)
        self.assertTrue((self.folder('9paper.a_b-c') / 'source.json').is_file())

    def test_traversal_id_is_rejected_before_writes(self):
        self.sources[1]['id'] = '../outside'
        self.save('sources/manifest/sources.json', self.sources)
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertFalse((self.root / 'sources/library').exists())

    def test_duplicate_id_is_rejected_before_writes(self):
        self.sources[1]['id'] = self.sources[0]['id']
        self.save('sources/manifest/sources.json', self.sources)
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertFalse((self.root / 'sources/library').exists())

    def test_manifest_must_be_array(self):
        self.save('sources/manifest/sources.json', {'paper-a': self.sources[0]})
        with self.assertRaises(ValueError):
            library.load_sources(self.root)

    def test_invalid_json_read_is_not_silently_treated_as_empty(self):
        path = self.root / 'sources/manifest/sources.json'
        path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            library.read_json(path)
        self.check_has_error()

    def test_library_symlink_cannot_write_outside_repository(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.root / 'sources/library').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_metadata_symlink_cannot_overwrite_external_file(self):
        library.materialize(self.root)
        outside = self.base / 'outside.json'
        outside.write_text('external sentinel')
        target = self.folder() / 'source.json'
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual(outside.read_text(), 'external sentinel')

    def test_atomic_json_replace_failure_preserves_previous_file(self):
        path = self.save('state.json', {'value': 'previous'})
        before = path.read_bytes()
        with patch.object(Path, 'replace', autospec=True, side_effect=OSError('模拟原子替换失败')):
            with self.assertRaises(OSError):
                library.write_json(path, {'value': 'new'})
        self.assertEqual(path.read_bytes(), before)


class PublicNetworkTests(SourceCase):
    def test_public_https_accepts_dns_and_removes_fragment(self):
        resolver = Mock(return_value=addresses('8.8.8.8', '1.1.1.1'))
        self.assertEqual(library.validate_url(PUBLIC_URL + '?q=1#section', resolver), PUBLIC_URL + '?q=1')
        resolver.assert_called_once_with('papers.example.org', 443, type=socket.SOCK_STREAM)

    def test_mixed_public_private_dns_is_rejected(self):
        with self.assertRaises(ValueError):
            library.validate_url(PUBLIC_URL, Mock(return_value=addresses('8.8.8.8', '10.1.2.3')))

    def test_empty_dns_is_rejected(self):
        with self.assertRaises(ValueError):
            library.validate_url(PUBLIC_URL, Mock(return_value=[]))

    def test_response_limit_accepts_exactly_twenty_mib(self):
        response = Response(b'x' * LIMIT)
        self.opener.open.side_effect = [response]
        result = library.fetch_public(PUBLIC_URL)
        self.assertEqual(len(result['body']), LIMIT)
        self.assertEqual(response.requested_sizes, [LIMIT + 1])
        self.assertTrue(response.closed)

    def test_response_limit_rejects_one_byte_over(self):
        response = Response(b'x' * (LIMIT + 1))
        self.opener.open.side_effect = [response]
        with self.assertRaises(ValueError):
            library.fetch_public(PUBLIC_URL)
        self.assertTrue(response.closed)

    def test_empty_response_is_rejected_and_closed(self):
        response = Response(b'')
        self.opener.open.side_effect = [response]
        with self.assertRaises(ValueError):
            library.fetch_public(PUBLIC_URL)
        self.assertTrue(response.closed)

    def test_fetch_sets_timeout_without_login_headers(self):
        self.opener.open.side_effect = [Response()]
        library.fetch_public(PUBLIC_URL)
        request = self.opener.open.call_args.args[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertNotIn('cookie', headers)
        self.assertNotIn('authorization', headers)
        self.assertGreater(self.opener.open.call_args.kwargs['timeout'], 0)

    def test_redirect_to_private_dns_is_rejected_before_second_request(self):
        self.dns.side_effect = [addresses('8.8.8.8'), addresses('127.0.0.1')]
        self.opener.open.side_effect = [urllib.error.HTTPError(PUBLIC_URL, 302, 'redirect', {'Location': 'https://internal.example.org/private'}, None)]
        with self.assertRaises(ValueError):
            library.fetch_public(PUBLIC_URL)
        self.assertEqual(self.opener.open.call_count, 1)
        self.assertEqual(self.dns.call_count, 2)

    def test_three_redirects_are_accepted_and_each_hop_revalidated(self):
        self.opener.open.side_effect = [
            urllib.error.HTTPError(PUBLIC_URL, 302, 'redirect', {'Location': '/hop1'}, None),
            urllib.error.HTTPError(PUBLIC_URL, 307, 'redirect', {'Location': '/hop2'}, None),
            urllib.error.HTTPError(PUBLIC_URL, 308, 'redirect', {'Location': '/hop3'}, None), Response()]
        result = library.fetch_public(PUBLIC_URL)
        self.assertEqual(result['url'], 'https://papers.example.org/hop3')
        self.assertEqual(self.opener.open.call_count, 4)
        self.assertEqual(self.dns.call_count, 4)

    def test_fourth_redirect_is_rejected_without_fifth_request(self):
        self.opener.open.side_effect = [urllib.error.HTTPError(PUBLIC_URL, 302, 'redirect', {'Location': '/next'}, None) for _ in range(4)]
        with self.assertRaises((urllib.error.HTTPError, ValueError)):
            library.fetch_public(PUBLIC_URL)
        self.assertEqual(self.opener.open.call_count, 4)

    def test_github_fixed_commit_blob_keeps_exact_revision_and_path(self):
        revision = 'a' * 40
        self.assertEqual(library.candidates(f'https://github.com/team/project/blob/{revision}/src/file.py#L3'),
                         [(f'https://raw.githubusercontent.com/team/project/{revision}/src/file.py', 'source_file')])

    def test_arxiv_candidate_versions_are_preserved_in_all_representations(self):
        for entry in ('abs/2401.01234v3', 'html/2401.01234v3', 'pdf/2401.01234v3.pdf'):
            result = library.candidates('https://arxiv.org/' + entry)
            self.assertEqual([url for url, _ in result], [
                'https://arxiv.org/html/2401.01234v3', 'https://arxiv.org/pdf/2401.01234v3', 'https://arxiv.org/abs/2401.01234v3'])


def rejected_url_test(url):
    def test(self):
        resolver = Mock(return_value=addresses('8.8.8.8'))
        with self.assertRaises(ValueError):
            library.validate_url(url, resolver)
        resolver.assert_not_called()
    return test


for _name, _url in {
    'http': 'http://papers.example.org/article',
    'credentials': 'https://reader:placeholder@papers.example.org/article',
    'empty_userinfo': 'https://@papers.example.org/article',
    'localhost': 'https://Sub.Localhost./article',
    'ipv4_literal': 'https://8.8.8.8/article',
    'ipv6_literal': 'https://[2606:4700:4700::1111]/article',
    'control_character': 'https://papers.example.org/\narticle',
    'nonstandard_port': 'https://papers.example.org:444/article',
}.items():
    setattr(PublicNetworkTests, 'test_reject_' + _name, rejected_url_test(_url))


class CaptureTests(SourceCase):
    def test_capture_records_real_bytes_separate_from_declared_identity(self):
        library.materialize(self.root)
        before = copy.deepcopy(self.sources[0])
        result, fetcher = self.capture(b'new raw content')
        self.assertEqual(result['status'], 'saved')
        archive = self.archive()
        capture = archive['captures'][0]
        self.assertEqual(archive['source_id'], 'paper-a')
        self.assertEqual(capture['sha256'], hashlib.sha256(b'new raw content').hexdigest())
        self.assertEqual(capture['bytes'], len(b'new raw content'))
        self.assertEqual(capture['resolved_url'], PUBLIC_URL)
        self.assertEqual(capture['content_type'], 'text/plain')
        self.assertTrue(capture['retrieved_at'])
        self.assertEqual(capture['declared_source_version'], before['version'])
        self.assertEqual((self.root / capture['cache_file']).read_bytes(), b'new raw content')
        self.assertEqual(library.read_json(self.folder() / 'source.json'), before)
        self.assertEqual(self.sources[0], before)
        fetcher.assert_called_once_with(PUBLIC_URL)
        self.assertTrue(capture['cache_file'].startswith('sources/.local/'))
        self.assertFalse((self.folder() / 'snapshot').exists())

    def test_duplicate_bytes_use_single_content_addressed_object(self):
        library.materialize(self.root)
        self.capture(b'identical bytes')
        self.capture(b'identical bytes', self.sources[1])
        captures = [self.archive(source['id'])['captures'][0] for source in self.sources]
        self.assertEqual(captures[0]['cache_file'], captures[1]['cache_file'])
        self.assertEqual(len(list((self.root / 'sources/.local/objects').glob('*.bin'))), 1)

    def test_new_version_preserves_old_file_and_capture_history(self):
        _, old_file = self.saved()
        old_bytes = old_file.read_bytes()
        self.capture(b'changed bytes')
        self.assertEqual(len(self.archive()['captures']), 2)
        self.assertEqual(old_file.read_bytes(), old_bytes)
        self.assertEqual(library.check_library(self.root, local=True), [])

    def test_network_failure_preserves_successful_capture_and_marks_last_attempt(self):
        archive, cached = self.saved()
        original = cached.read_bytes()
        result = library.capture_one(self.root, self.sources[0], fetcher=Mock(side_effect=TimeoutError('模拟超时')))
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['previous_capture_kept'])
        updated = self.archive()
        self.assertEqual(updated['captures'], archive['captures'])
        self.assertEqual(updated['status'], 'saved')
        self.assertEqual(updated['last_attempt']['status'], 'failed')
        self.assertEqual(cached.read_bytes(), original)

    def test_first_failure_records_error_without_claiming_saved(self):
        library.materialize(self.root)
        result = library.capture_one(self.root, self.sources[0], fetcher=Mock(side_effect=TimeoutError('模拟超时')))
        self.assertEqual(result['status'], 'failed')
        archive = self.archive()
        self.assertEqual(archive['status'], 'failed')
        self.assertEqual(archive['captures'], [])
        self.assertTrue(archive['last_attempt']['errors'])
        self.assertFalse((self.root / 'sources/.local').exists())

    def test_capture_rejects_oversized_injected_body(self):
        library.materialize(self.root)
        result, _ = self.capture(b'x' * (LIMIT + 1))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.archive()['captures'], [])
        self.assertFalse((self.root / 'sources/.local/objects').exists())

    def test_arxiv_fallback_records_only_actual_representation_and_version(self):
        library.materialize(self.root)
        source = dict(self.sources[0], url='https://arxiv.org/abs/2401.01234v3')
        fetcher = Mock(side_effect=[OSError('HTML unavailable'), OSError('PDF unavailable'),
                                  {'body': b'abstract only', 'url': source['url'], 'content_type': 'text/html'}])
        result = library.capture_one(self.root, source, fetcher)
        self.assertEqual(result['status'], 'saved')
        capture = self.archive()['captures'][0]
        self.assertEqual(capture['representation'], 'paper_landing_page')
        self.assertEqual(capture['requested_url'], source['url'])
        self.assertEqual(fetcher.call_count, 3)

    def test_existing_corrupt_object_is_repaired_or_reported_as_failure(self):
        _, cached = self.saved()
        original = cached.read_bytes()
        cached.write_bytes(b'X' * len(original))
        result, _ = self.capture(original)
        if result['status'] == 'saved':
            self.assertEqual(cached.read_bytes(), original, '不能对损坏的内容寻址文件报告保存成功')
            self.assertEqual(library.check_library(self.root, local=True), [])
        else:
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(self.archive()['last_attempt']['status'], 'failed')

    def test_cache_symlink_cannot_write_external_bytes(self):
        library.materialize(self.root)
        outside = self.base / 'outside-cache'
        outside.mkdir()
        (self.root / 'sources/.local').symlink_to(outside, target_is_directory=True)
        result, _ = self.capture()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(list(outside.iterdir()), [])

    def test_archive_replace_failure_does_not_erase_previous_success(self):
        _, cached = self.saved()
        previous_archive = (self.folder() / 'archive.json').read_bytes()
        previous_bytes = cached.read_bytes()
        with patch.object(Path, 'replace', autospec=True, side_effect=OSError('模拟磁盘失败')):
            with self.assertRaises(OSError):
                self.capture(b'new data')
        self.assertEqual((self.folder() / 'archive.json').read_bytes(), previous_archive)
        self.assertEqual(cached.read_bytes(), previous_bytes)

    def test_batch_shares_same_url_and_keeps_distinct_source_identities(self):
        self.sources[1]['url'] = PUBLIC_URL + '#section'
        self.save('sources/manifest/sources.json', self.sources)
        fetcher = Mock(return_value={'body': b'shared', 'url': PUBLIC_URL, 'content_type': 'text/plain'})
        results = library.capture_all(self.root, workers=1, fetcher=fetcher)
        self.assertEqual({row['id'] for row in results}, {'paper-a', 'code-b'})
        self.assertTrue(all(row['status'] == 'saved' for row in results))
        self.assertEqual(fetcher.call_count, 1)
        for source in self.sources:
            self.assertEqual(library.read_json(self.folder(source['id']) / 'source.json'), source)
            self.assertEqual(self.archive(source['id'])['source_id'], source['id'])

    def test_batch_continues_after_network_failure(self):
        def fetcher(url):
            if url == PUBLIC_URL:
                raise TimeoutError('模拟第一来源失败')
            return {'body': b'second source', 'url': url, 'content_type': 'text/plain'}
        results = library.capture_all(self.root, workers=1, fetcher=fetcher)
        self.assertEqual({row['id']: row['status'] for row in results}, {'paper-a': 'failed', 'code-b': 'saved'})

    def test_selected_capture_only_downloads_requested_source(self):
        fetcher = Mock(return_value={'body': b'selected', 'url': self.sources[1]['url'], 'content_type': 'text/plain'})
        results = library.capture_all(self.root, ids=['code-b'], workers=1, fetcher=fetcher)
        self.assertEqual([row['id'] for row in results], ['code-b'])
        fetcher.assert_called_once_with(self.sources[1]['url'])
        self.assertEqual(self.archive()['status'], 'not_requested')


class OfflineCheckTests(SourceCase):
    def test_new_clone_without_cache_passes_default_but_fails_strict_check(self):
        _, cached = self.saved()
        cached.unlink()
        self.assertEqual(library.check_library(self.root), [])
        self.check_has_error(local=True)
        self.opener.open.assert_not_called()

    def test_strict_check_detects_wrong_hash_even_when_length_matches(self):
        _, cached = self.saved()
        cached.write_bytes(b'X' * cached.stat().st_size)
        self.check_has_error(local=True)

    def test_strict_check_detects_wrong_size(self):
        _, cached = self.saved()
        cached.write_bytes(b'x')
        self.check_has_error(local=True)

    def test_rejects_modified_declared_metadata(self):
        library.materialize(self.root)
        modified = dict(self.sources[0], version='incorrect')
        self.save('sources/library/paper-a/source.json', modified)
        self.check_has_error()

    def test_rejects_missing_source_card(self):
        library.materialize(self.root)
        (self.folder() / 'README.md').unlink()
        self.check_has_error()

    def test_rejects_extra_source_folder(self):
        library.materialize(self.root)
        self.folder('unregistered-source').mkdir()
        self.check_has_error()

    def test_rejects_missing_library_index(self):
        library.materialize(self.root)
        (self.root / 'sources/library/index.json').unlink()
        self.check_has_error()

    def test_rejects_index_with_missing_registered_source(self):
        library.materialize(self.root)
        self.save('sources/library/index.json', [])
        self.check_has_error()

    def test_rejects_unknown_source_binding(self):
        library.materialize(self.root)
        self.units[0]['source_ids'] = ['missing-source']
        self.save('knowledge/units.json', self.units)
        self.check_has_error()

    def test_rejects_unknown_topic_binding(self):
        library.materialize(self.root)
        self.units[0]['topic'] = 'missing-topic'
        self.save('knowledge/units.json', self.units)
        self.check_has_error()

    def test_malformed_archive_returns_errors_instead_of_crashing(self):
        library.materialize(self.root)
        self.store_archive([])
        self.check_has_error()

    def test_saved_state_requires_capture_records(self):
        library.materialize(self.root)
        archive = self.archive()
        archive['status'] = 'saved'
        self.store_archive(archive)
        self.check_has_error()

    def test_saved_capture_requires_retrieval_metadata(self):
        archive, _ = self.saved()
        for key in ('resolved_url', 'retrieved_at', 'content_type'):
            archive['captures'][0].pop(key)
        self.store_archive(archive)
        self.check_has_error()

    def test_cache_path_cannot_escape_content_addressed_store(self):
        archive, _ = self.saved()
        archive['captures'][0]['cache_file'] = '../outside.bin'
        self.store_archive(archive)
        self.check_has_error()

    def test_metadata_symlink_outside_repository_is_rejected(self):
        library.materialize(self.root)
        path = self.folder() / 'source.json'
        outside = self.base / 'external-source.json'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        self.check_has_error()

    def test_readme_symlink_outside_repository_is_rejected(self):
        library.materialize(self.root)
        path = self.folder() / 'README.md'
        outside = self.base / 'external-card.md'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        self.check_has_error()

    def test_cache_symlink_outside_repository_is_rejected_even_in_default_check(self):
        _, cached = self.saved()
        outside = self.base / 'external-cache.bin'
        outside.write_bytes(cached.read_bytes())
        cached.unlink()
        cached.symlink_to(outside)
        self.check_has_error()


class CliTests(SourceCase):
    def test_index_and_offline_check_use_supplied_root_without_network(self):
        code, _ = self.command('index')
        self.assertEqual(code, 0)
        code, _ = self.command('check')
        self.assertEqual(code, 0)
        self.assertTrue((self.root / 'sources/library/index.json').is_file())
        self.opener.open.assert_not_called()

    def test_local_check_failure_returns_nonzero(self):
        _, cached = self.saved()
        cached.unlink()
        self.assertEqual(self.command('check')[0], 0)
        self.assertNotEqual(self.command('check', '--local')[0], 0)

    def test_capture_cli_runs_requested_id_and_reports_real_result(self):
        self.opener.open.side_effect = [Response(b'cli public data')]
        code, output = self.command('capture', '--id', 'paper-a', '--workers', '1')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output), {'saved': 1, 'failed': []})
        self.assertEqual(self.archive()['status'], 'saved')
        self.assertEqual(self.archive('code-b')['status'], 'not_requested')
        self.assertEqual(self.opener.open.call_count, 1)


class RepairBoundaryTests(SourceCase):
    """仅补充第二轮修改影响的分支，原64例保留并共同复验。"""

    def test_different_length_corrupt_cache_is_atomically_repaired(self):
        archive, cached = self.saved()
        original = cached.read_bytes()
        cached.write_bytes(b'broken')
        replace = Path.replace
        replaced_targets = []

        def record_replace(path, target):
            replaced_targets.append(Path(target))
            return replace(path, target)

        with patch.object(Path, 'replace', autospec=True, side_effect=record_replace):
            result, _ = self.capture(original)
        self.assertEqual(result['status'], 'saved')
        self.assertEqual(cached.read_bytes(), original)
        self.assertIn(cached, replaced_targets)
        self.assertEqual(self.archive()['captures'], archive['captures'])
        self.assertEqual(library.check_library(self.root, local=True), [])

    def test_batch_shares_failed_request_and_continues_unrelated_source(self):
        self.sources[1]['url'] = PUBLIC_URL + '#different-section'
        third = dict(self.sources[0], id='paper-c', url='https://other.example.org/paper')
        self.sources.append(third)
        self.save('sources/manifest/sources.json', self.sources)

        def response(url):
            if url == PUBLIC_URL:
                raise TimeoutError('模拟共享URL超时')
            return {'body': b'other paper', 'url': url, 'content_type': 'text/plain'}

        fetcher = Mock(side_effect=response)
        results = library.capture_all(self.root, workers=1, fetcher=fetcher)
        self.assertEqual({r['id']: r['status'] for r in results},
                         {'paper-a': 'failed', 'code-b': 'failed', 'paper-c': 'saved'})
        self.assertEqual([c.args[0] for c in fetcher.call_args_list], [PUBLIC_URL, third['url']])
        for source in self.sources[:2]:
            self.assertEqual(self.archive(source['id'])['source_id'], source['id'])
            self.assertEqual(self.archive(source['id'])['last_attempt']['status'], 'failed')
            self.assertEqual(library.read_json(self.folder(source['id']) / 'source.json'), source)

    def test_arxiv_failed_fallbacks_are_shared_with_successful_landing_page(self):
        for source in self.sources:
            source['url'] = 'https://arxiv.org/abs/2401.01234v3'
        self.save('sources/manifest/sources.json', self.sources)
        fetcher = Mock(side_effect=[OSError('HTML unavailable'), ValueError('PDF exceeds limit'),
                                   {'body': b'abstract', 'url': self.sources[0]['url'], 'content_type': 'text/html'}])
        results = library.capture_all(self.root, workers=1, fetcher=fetcher)
        self.assertEqual([r['status'] for r in results], ['saved', 'saved'])
        self.assertEqual(fetcher.call_count, 3)
        for source in self.sources:
            capture = self.archive(source['id'])['captures'][0]
            self.assertEqual(capture['representation'], 'paper_landing_page')
            self.assertEqual(capture['resolved_url'], source['url'])

    def test_mixed_none_and_valid_topics_do_not_crash_directory_generation(self):
        self.claims.append({'id': 'missing-topic', 'topic': None, 'evidence': [{'source_id': 'paper-a'}]})
        self.save('knowledge/claims.json', self.claims)
        index = library.materialize(self.root)
        paper = next(r for r in index if r['id'] == 'paper-a')
        self.assertEqual(set(paper['topic_ids']), {'topic-a', 'topic-b'})
        self.check_has_error()

    def test_non_string_capture_id_is_rejected_before_network_or_write(self):
        source = dict(self.sources[0], id=42)
        fetcher = Mock()
        with self.assertRaises(ValueError):
            library.capture_one(self.root, source, fetcher=fetcher)
        fetcher.assert_not_called()
        self.assertFalse((self.root / 'sources/library').exists())

    def test_explicit_https_443_port_is_accepted(self):
        url = 'https://papers.example.org:443/article'
        self.assertEqual(library.validate_url(url, Mock(return_value=addresses('8.8.8.8'))), url)

    def test_index_duplicate_ids_are_rejected_even_with_matching_row_count(self):
        index = library.materialize(self.root)
        self.save('sources/library/index.json', [index[0], index[0]])
        self.check_has_error()

    def test_index_wrong_path_is_rejected(self):
        index = library.materialize(self.root)
        index[0]['path'] = 'sources/library/code-b/README.md'
        self.save('sources/library/index.json', index)
        self.check_has_error()

    def test_index_symlink_outside_repository_is_rejected(self):
        library.materialize(self.root)
        path = self.root / 'sources/library/index.json'
        outside = self.base / 'outside-index.json'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        self.check_has_error()

    def test_broken_archive_json_produces_located_error_and_nonzero_cli(self):
        library.materialize(self.root)
        (self.folder() / 'archive.json').write_text('{broken', encoding='utf-8')
        errors = library.check_library(self.root)
        self.assertTrue(any('paper-a' in error for error in errors))
        code, output = self.command('check')
        self.assertNotEqual(code, 0)
        self.assertIn('paper-a', output)

    def test_null_archive_produces_located_error_and_nonzero_cli(self):
        library.materialize(self.root)
        self.store_archive(None)
        errors = library.check_library(self.root)
        self.assertTrue(any('paper-a' in error for error in errors))
        self.assertNotEqual(self.command('check')[0], 0)

    def test_invalid_retrieval_timestamp_is_rejected_offline(self):
        archive, _ = self.saved()
        archive['captures'][0]['retrieved_at'] = 'not-a-date'
        self.store_archive(archive)
        self.check_has_error()
        self.dns.assert_not_called()

    def test_non_string_representation_is_rejected(self):
        archive, _ = self.saved()
        archive['captures'][0]['representation'] = []
        self.store_archive(archive)
        self.check_has_error()

    def test_non_https_resolved_url_is_rejected_offline(self):
        archive, _ = self.saved()
        archive['captures'][0]['resolved_url'] = 'http://papers.example.org/article'
        self.store_archive(archive)
        self.check_has_error()
        self.dns.assert_not_called()

    def test_empty_userinfo_in_saved_url_is_rejected_offline(self):
        archive, _ = self.saved()
        archive['captures'][0]['resolved_url'] = 'https://@papers.example.org/article'
        self.store_archive(archive)
        self.check_has_error()
        self.dns.assert_not_called()


def invalid_binding_test(kind, broken_field):
    def test(self):
        library.materialize(self.root)
        if kind == 'claims':
            row = {'id': 'claim-new', 'topic': 'topic-a', 'evidence': [{'source_id': 'paper-a'}]}
            if broken_field == 'source':
                row['evidence'][0]['source_id'] = 'missing-source'
            else:
                row['topic'] = 'missing-topic'
            self.save('knowledge/claims.json', [row])
        else:
            row = {'id': 'frontier-new', 'source_ids': ['paper-a'], 'topic_ids': ['topic-a']}
            row['source_ids' if broken_field == 'source' else 'topic_ids'] = ['missing-' + broken_field]
            self.save('knowledge/frontiers.json', [row])
        self.check_has_error()
    return test


for _kind in ('claims', 'frontiers'):
    for _field in ('source', 'topic'):
        setattr(RepairBoundaryTests, 'test_reject_' + _kind + '_unknown_' + _field,
                invalid_binding_test(_kind, _field))


def wire_response(body, headers=None):
    """真实HTTPResponse解析内存响应，避免真实socket或依赖返回预先计算的结果。"""
    fields = {'Content-Type': 'application/pdf', **(headers or {})}
    wire = b'HTTP/1.1 200 OK\r\n' + b''.join(
        (key + ': ' + value + '\r\n').encode('ascii') for key, value in fields.items()) + b'\r\n' + body

    class MemorySocket:
        def makefile(self, mode):
            return io.BytesIO(wire)

    response = http.client.HTTPResponse(MemorySocket())
    response.begin()
    return response


class TransferIntegrityTests(SourceCase):
    """第三轮契约：状态码成功不等于响应体完整。"""

    def test_matching_content_length_preserves_exact_bytes(self):
        body = b'%PDF-1.7\ncomplete fixture bytes'
        response = wire_response(body, {'Content-Length': str(len(body))})
        self.opener.open.side_effect = [response]
        result = library.fetch_public(PUBLIC_URL)
        self.assertEqual(result['body'], body)
        self.assertEqual(result['content_type'], 'application/pdf')
        self.assertTrue(response.isclosed())

    def test_declared_length_at_twenty_mib_limit_is_accepted(self):
        response = wire_response(b'x' * LIMIT, {'Content-Length': str(LIMIT)})
        self.opener.open.side_effect = [response]
        result = library.fetch_public(PUBLIC_URL)
        self.assertEqual(len(result['body']), LIMIT)
        self.assertTrue(response.isclosed())

    def test_declared_length_above_limit_is_rejected_before_body_read(self):
        response = wire_response(b'partial', {'Content-Length': str(LIMIT + 1)})
        self.opener.open.side_effect = [response]
        with patch.object(response, 'read', wraps=response.read) as read:
            with self.assertRaises(ValueError):
                library.fetch_public(PUBLIC_URL)
            read.assert_not_called()
        self.assertTrue(response.isclosed())

    def test_http_200_truncated_length_cannot_create_saved_archive(self):
        library.materialize(self.root)
        partial = b'%PDF-1.7\npartial'
        response = wire_response(partial, {'Content-Length': str(len(partial) + 100)})
        self.assertEqual(response.status, 200)
        self.opener.open.side_effect = [response]
        result = library.capture_one(self.root, self.sources[0])
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.archive()['captures'], [])
        self.assertEqual(self.archive()['last_attempt']['status'], 'failed')
        self.assertFalse((self.root / 'sources/.local/objects').exists())
        self.assertTrue(response.isclosed())

    def test_declared_length_smaller_than_returned_body_is_rejected(self):
        response = Response(b'body-longer-than-declared')
        response.headers['Content-Length'] = '4'
        self.opener.open.side_effect = [response]
        with self.assertRaises(ValueError):
            library.fetch_public(PUBLIC_URL)
        self.assertTrue(response.closed)

    def test_missing_terminal_chunk_raises_incomplete_read_and_closes_response(self):
        response = wire_response(b'4\r\ndata\r\n', {'Transfer-Encoding': 'chunked'})
        self.opener.open.side_effect = [response]
        with self.assertRaises(http.client.IncompleteRead):
            library.fetch_public(PUBLIC_URL)
        self.assertTrue(response.isclosed())

    def test_complete_chunked_response_without_content_length_is_accepted(self):
        response = wire_response(b'4\r\ndata\r\n0\r\n\r\n', {'Transfer-Encoding': 'chunked'})
        self.opener.open.side_effect = [response]
        result = library.fetch_public(PUBLIC_URL)
        self.assertEqual(result['body'], b'data')
        self.assertTrue(response.isclosed())

    def test_incomplete_read_preserves_successful_history_and_original_file(self):
        archive, cached = self.saved()
        original = cached.read_bytes()
        response = wire_response(b'4\r\ndata\r\n', {'Transfer-Encoding': 'chunked'})
        self.opener.open.side_effect = [response]
        result = library.capture_one(self.root, self.sources[0])
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['previous_capture_kept'])
        self.assertEqual(self.archive()['captures'], archive['captures'])
        self.assertEqual(self.archive()['status'], 'saved')
        self.assertEqual(self.archive()['last_attempt']['status'], 'failed')
        self.assertTrue(self.archive()['last_attempt']['errors'])
        self.assertEqual(cached.read_bytes(), original)
        self.assertEqual(list((self.root / 'sources/.local/objects').glob('*.bin')), [cached])

    def test_incomplete_read_is_shared_and_batch_continues(self):
        self.sources[1]['url'] = PUBLIC_URL + '#other'
        third = dict(self.sources[0], id='paper-c', url='https://other.example.org/paper')
        self.sources.append(third)
        self.save('sources/manifest/sources.json', self.sources)
        broken = wire_response(b'4\r\ndata\r\n', {'Transfer-Encoding': 'chunked'})
        complete = wire_response(b'complete', {'Content-Length': '8'})
        self.opener.open.side_effect = [broken, complete]
        results = library.capture_all(self.root, workers=1)
        self.assertEqual({r['id']: r['status'] for r in results},
                         {'paper-a': 'failed', 'code-b': 'failed', 'paper-c': 'saved'})
        self.assertEqual([c.args[0].full_url for c in self.opener.open.call_args_list], [PUBLIC_URL, third['url']])
        self.assertEqual(self.archive()['captures'], [])
        self.assertEqual(self.archive('code-b')['captures'], [])
        third_capture = self.archive('paper-c')['captures'][0]
        self.assertEqual((self.root / third_capture['cache_file']).read_bytes(), b'complete')

    def test_other_http_exception_is_recorded_and_batch_continues(self):
        self.opener.open.side_effect = [http.client.BadStatusLine('invalid status line'),
                                       wire_response(b'success', {'Content-Length': '7'})]
        results = library.capture_all(self.root, workers=1)
        self.assertEqual({r['id']: r['status'] for r in results}, {'paper-a': 'failed', 'code-b': 'saved'})
        self.assertEqual(self.archive()['last_attempt']['status'], 'failed')
        self.assertEqual(self.archive()['captures'], [])
        self.assertEqual(self.opener.open.call_count, 2)

    def test_incomplete_arxiv_candidate_falls_back_without_saving_partial_bytes(self):
        library.materialize(self.root)
        source = dict(self.sources[0], url='https://arxiv.org/abs/2401.01234v3')
        self.opener.open.side_effect = [wire_response(b'4\r\ndata\r\n', {'Transfer-Encoding': 'chunked'}),
                                       wire_response(b'full pdf', {'Content-Length': '8'})]
        result = library.capture_one(self.root, source)
        self.assertEqual(result['status'], 'saved')
        capture = self.archive()['captures'][0]
        self.assertEqual(capture['requested_url'], 'https://arxiv.org/pdf/2401.01234v3')
        self.assertEqual(capture['representation'], 'paper_full_text')
        self.assertEqual((self.root / capture['cache_file']).read_bytes(), b'full pdf')
        self.assertEqual(len(self.archive()['captures']), 1)
        self.assertEqual(self.opener.open.call_count, 2)

    def test_body_read_timeout_preserves_previous_success(self):
        archive, cached = self.saved()
        original = cached.read_bytes()
        response = wire_response(b'partial', {'Content-Length': '100'})
        self.opener.open.side_effect = [response]
        with patch.object(response, 'read', side_effect=TimeoutError('模拟响应体读取超时')):
            result = library.capture_one(self.root, self.sources[0])
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.archive()['captures'], archive['captures'])
        self.assertEqual(self.archive()['last_attempt']['status'], 'failed')
        self.assertEqual(cached.read_bytes(), original)
        self.assertTrue(response.isclosed())


def invalid_content_length_test(declared):
    def test(self):
        response = wire_response(b'data', {'Content-Length': declared})
        self.opener.open.side_effect = [response]
        with patch.object(response, 'read', wraps=response.read) as read:
            with self.assertRaises(ValueError):
                library.fetch_public(PUBLIC_URL)
            read.assert_not_called()
        self.assertTrue(response.isclosed())
    return test


for _label, _declared in {'negative': '-1', 'non_integer': '4bytes', 'empty': ''}.items():
    setattr(TransferIntegrityTests, 'test_invalid_content_length_' + _label,
            invalid_content_length_test(_declared))


class PublicSnapshotTests(SourceCase):
    """显式已核许可元数据的离线检查；不请求上游、不执行或发布快照。"""

    def public_fixture(self, spdx='MIT', notice=False):
        commit = 'a' * 40
        self.sources[0]['native_version'] = commit
        self.sources[0]['url'] = f'https://github.com/fixture/project/blob/{commit}/src/reader.py'
        self.save('sources/manifest/sources.json', self.sources)
        library.materialize(self.root)
        snapshot = self.folder() / 'snapshot'
        snapshot.mkdir()
        body = b'# synthetic source fixture; never executed\n'
        (snapshot / 'source.txt').write_bytes(body)
        (snapshot / 'LICENSE').write_text('MIT License\nFixture license text\n' if spdx == 'MIT'
                                         else 'Apache License\nVersion 2.0, January 2004\nFixture license text\n')
        public = {'spdx_id': spdx, 'source_commit': commit,
                  'content_file': 'sources/library/paper-a/snapshot/source.txt',
                  'license_file': 'sources/library/paper-a/snapshot/LICENSE',
                  'upstream_license_url': f'https://github.com/fixture/project/blob/{commit}/LICENSE',
                  'content_sha256': hashlib.sha256(body).hexdigest()}
        if notice:
            (snapshot / 'NOTICE').write_text('Fixture attribution notice\n')
            public['notice_file'] = 'sources/library/paper-a/snapshot/NOTICE'
        archive = self.archive()
        archive['public_snapshot'] = public
        self.store_archive(archive)
        return public, snapshot, body

    def change_public(self, key, value):
        archive = self.archive()
        archive['public_snapshot'][key] = value
        self.store_archive(archive)

    def snapshot_links(self):
        text = (self.folder() / 'README.md').read_text()
        return [href for href in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text) if href.startswith('snapshot/')]

    def test_mit_snapshot_links_real_source_and_license_without_changing_identity(self):
        public, snapshot, body = self.public_fixture()
        before = (self.root / 'sources/manifest/sources.json').read_bytes()
        library.materialize(self.root)
        self.assertEqual(set(self.snapshot_links()), {'snapshot/source.txt', 'snapshot/LICENSE'})
        for href in self.snapshot_links():
            self.assertTrue((self.folder() / href).is_file())
            self.assertTrue((self.folder() / href).resolve().is_relative_to(snapshot.resolve()))
        self.assertEqual((snapshot / 'source.txt').read_bytes(), body)
        self.assertEqual(self.archive()['public_snapshot'], public)
        self.assertEqual((self.root / 'sources/manifest/sources.json').read_bytes(), before)
        self.assertEqual(library.check_library(self.root), [])
        self.assertEqual(library.check_library(self.root, local=True), [])
        self.opener.open.assert_not_called()

    def test_apache_snapshot_keeps_optional_notice_and_links_it(self):
        public, snapshot, _ = self.public_fixture(spdx='Apache-2.0', notice=True)
        before = {name: (snapshot / name).read_bytes() for name in ('LICENSE', 'NOTICE')}
        library.materialize(self.root)
        self.assertEqual(set(self.snapshot_links()), {'snapshot/source.txt', 'snapshot/LICENSE', 'snapshot/NOTICE'})
        self.assertEqual({name: (snapshot / name).read_bytes() for name in before}, before)
        self.assertEqual(self.archive()['public_snapshot'], public)
        self.assertEqual(library.check_library(self.root), [])

    def test_private_capture_is_not_automatically_published(self):
        _, cached = self.saved()
        before = cached.read_bytes()
        library.materialize(self.root)
        self.assertNotIn('public_snapshot', self.archive())
        self.assertFalse((self.folder() / 'snapshot').exists())
        self.assertEqual(self.snapshot_links(), [])
        self.assertEqual(cached.read_bytes(), before)
        self.assertEqual(library.check_library(self.root), [])

    def test_unapproved_license_is_rejected(self):
        self.public_fixture()
        self.change_public('spdx_id', 'GPL-3.0-only')
        self.check_has_error()

    def test_snapshot_commit_must_match_native_version(self):
        self.public_fixture()
        self.change_public('source_commit', 'b' * 40)
        self.check_has_error()

    def test_snapshot_missing_commit_is_rejected(self):
        self.public_fixture()
        archive = self.archive()
        archive['public_snapshot'].pop('source_commit')
        self.store_archive(archive)
        self.check_has_error()

    def test_snapshot_must_retain_upstream_license_url(self):
        self.public_fixture()
        archive = self.archive()
        archive['public_snapshot'].pop('upstream_license_url')
        self.store_archive(archive)
        self.check_has_error()

    def test_upstream_license_url_must_reference_same_commit(self):
        self.public_fixture()
        self.change_public('upstream_license_url', 'https://github.com/fixture/project/blob/' + 'b' * 40 + '/LICENSE')
        self.check_has_error()

    def test_upstream_license_url_must_reference_source_repository(self):
        self.public_fixture()
        self.change_public('upstream_license_url', 'https://github.com/unrelated/project/blob/' + 'a' * 40 + '/LICENSE')
        self.check_has_error()

    def test_default_offline_check_detects_snapshot_hash_corruption(self):
        _, snapshot, body = self.public_fixture()
        (snapshot / 'source.txt').write_bytes(b'X' * len(body))
        self.check_has_error()
        self.dns.assert_not_called()
        self.opener.open.assert_not_called()

    def test_snapshot_record_wrong_type_returns_error(self):
        self.public_fixture()
        archive = self.archive()
        archive['public_snapshot'] = []
        self.store_archive(archive)
        self.check_has_error()

    def test_card_generation_rejects_missing_snapshot_file_without_dead_link(self):
        _, snapshot, _ = self.public_fixture()
        before = (self.folder() / 'README.md').read_bytes()
        (snapshot / 'source.txt').unlink()
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual((self.folder() / 'README.md').read_bytes(), before)

    def test_snapshot_file_cannot_reference_another_source(self):
        _, snapshot, _ = self.public_fixture()
        other = self.folder('code-b') / 'snapshot'
        other.mkdir()
        (other / 'source.txt').write_bytes((snapshot / 'source.txt').read_bytes())
        self.change_public('content_file', 'sources/library/code-b/snapshot/source.txt')
        self.check_has_error()
        with self.assertRaises(ValueError):
            library.materialize(self.root)

    def test_snapshot_file_symlink_outside_repository_is_rejected(self):
        _, snapshot, body = self.public_fixture()
        outside = self.base / 'outside-source.txt'
        outside.write_bytes(body)
        (snapshot / 'source.txt').unlink()
        (snapshot / 'source.txt').symlink_to(outside)
        self.check_has_error()
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual(outside.read_bytes(), body)

    def test_snapshot_parent_symlink_cannot_borrow_another_source_directory(self):
        _, snapshot, _ = self.public_fixture()
        other = self.folder('code-b') / 'snapshot'
        snapshot.rename(other)
        snapshot.symlink_to(other, target_is_directory=True)
        self.check_has_error()

    def test_card_generation_rejects_snapshot_parent_symlink_to_other_source(self):
        _, snapshot, _ = self.public_fixture()
        other = self.folder('code-b') / 'snapshot'
        snapshot.rename(other)
        snapshot.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            library.materialize(self.root)


def missing_public_file_test(field):
    def test(self):
        public, _, _ = self.public_fixture(notice=True)
        (self.root / public[field]).unlink()
        self.check_has_error()
    return test


for _field in ('content_file', 'license_file', 'notice_file'):
    setattr(PublicSnapshotTests, 'test_missing_' + _field + '_is_rejected', missing_public_file_test(_field))


class IdentityPathTests(SourceCase):
    """第五轮：从公开检查和写入入口验证身份匹配及路径边界。"""
    public_fixture = PublicSnapshotTests.public_fixture
    change_public = PublicSnapshotTests.change_public

    def set_source_url(self, url):
        self.sources[0]['url'] = url
        self.save('sources/manifest/sources.json', self.sources)
        self.save('sources/library/paper-a/source.json', self.sources[0])

    def test_blob_source_accepts_raw_license_same_repository_and_revision(self):
        public, _, _ = self.public_fixture()
        self.change_public('upstream_license_url', 'https://raw.githubusercontent.com/fixture/project/' + public['source_commit'] + '/LICENSE')
        self.assertEqual(library.check_library(self.root), [])

    def test_raw_source_accepts_blob_license_same_repository_and_revision(self):
        public, _, _ = self.public_fixture()
        self.set_source_url('https://raw.githubusercontent.com/fixture/project/' + public['source_commit'] + '/src/reader.py')
        self.assertEqual(library.check_library(self.root), [])

    def test_raw_source_and_raw_license_same_identity_are_accepted(self):
        public, _, _ = self.public_fixture()
        prefix = 'https://raw.githubusercontent.com/fixture/project/' + public['source_commit']
        self.set_source_url(prefix + '/src/reader.py')
        self.change_public('upstream_license_url', prefix + '/LICENSE')
        self.assertEqual(library.check_library(self.root), [])

    def test_matching_url_revisions_must_also_match_declared_native_version(self):
        self.public_fixture()
        other_revision = 'b' * 40
        self.set_source_url('https://github.com/fixture/project/blob/' + other_revision + '/src/reader.py')
        self.change_public('upstream_license_url', 'https://raw.githubusercontent.com/fixture/project/' + other_revision + '/LICENSE')
        self.check_has_error()

    def test_branch_source_url_is_rejected_even_with_fixed_license_revision(self):
        self.public_fixture()
        self.set_source_url('https://github.com/fixture/project/blob/main/src/reader.py')
        self.check_has_error()

    def test_short_revision_source_url_is_not_a_fixed_file_identity(self):
        self.public_fixture()
        self.set_source_url('https://raw.githubusercontent.com/fixture/project/aaaaaaa/src/reader.py')
        self.check_has_error()

    def test_non_github_license_host_is_rejected(self):
        public, _, _ = self.public_fixture()
        self.change_public('upstream_license_url', 'https://github.com.example.org/fixture/project/blob/' + public['source_commit'] + '/LICENSE')
        self.check_has_error()

    def test_license_url_with_userinfo_is_rejected(self):
        public, _, _ = self.public_fixture()
        self.change_public('upstream_license_url', 'https://reader@github.com/fixture/project/blob/' + public['source_commit'] + '/LICENSE')
        self.check_has_error()

    def test_commit_without_file_path_is_not_a_license_file_identity(self):
        public, _, _ = self.public_fixture()
        self.change_public('upstream_license_url', 'https://raw.githubusercontent.com/fixture/project/' + public['source_commit'])
        self.check_has_error()

    def test_absolute_snapshot_path_is_rejected_even_inside_repository(self):
        _, snapshot, _ = self.public_fixture()
        self.change_public('content_file', str(snapshot / 'source.txt'))
        self.check_has_error()
        with self.assertRaises(ValueError):
            library.materialize(self.root)

    def test_parent_alias_is_rejected_even_when_it_resolves_to_same_snapshot(self):
        self.public_fixture()
        self.change_public('content_file', 'sources/library/paper-a/snapshot/../snapshot/source.txt')
        self.check_has_error()
        with self.assertRaises(ValueError):
            library.materialize(self.root)

    def test_file_symlink_within_own_snapshot_is_rejected(self):
        _, snapshot, _ = self.public_fixture()
        (snapshot / 'source.txt').rename(snapshot / 'actual.txt')
        (snapshot / 'source.txt').symlink_to('actual.txt')
        self.check_has_error()
        with self.assertRaises(ValueError):
            library.materialize(self.root)

    def test_symlink_loop_is_reported_and_generation_raises_value_error(self):
        _, snapshot, _ = self.public_fixture()
        (snapshot / 'source.txt').unlink()
        (snapshot / 'source.txt').symlink_to('source.txt')
        self.check_has_error()
        with self.assertRaises(ValueError):
            library.materialize(self.root)

    def test_cache_parent_alias_inside_repository_cannot_receive_download(self):
        library.materialize(self.root)
        alternate = self.root / 'other-cache'
        alternate.mkdir()
        (self.root / 'sources/.local').symlink_to(alternate, target_is_directory=True)
        result, _ = self.capture()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(list(alternate.iterdir()), [])
        self.assertEqual(self.archive()['captures'], [])

    def test_index_symlink_inside_repository_cannot_overwrite_aliased_file(self):
        library.materialize(self.root)
        target = self.root / 'knowledge/other-index.json'
        target.write_text('untouched sentinel')
        index = self.root / 'sources/library/index.json'
        index.unlink()
        index.symlink_to(target)
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual(target.read_text(), 'untouched sentinel')

    def test_card_symlink_inside_repository_cannot_overwrite_aliased_file(self):
        library.materialize(self.root)
        target = self.root / 'knowledge/other-card.md'
        target.write_text('untouched card')
        card = self.folder() / 'README.md'
        card.unlink()
        card.symlink_to(target)
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual(target.read_text(), 'untouched card')

    def test_source_directory_alias_inside_repository_rejected_before_write(self):
        library.materialize(self.root)
        alias_target = self.root / 'sources/other-source'
        self.folder().rename(alias_target)
        self.folder().symlink_to(alias_target, target_is_directory=True)
        previous = {p.name: p.read_bytes() for p in alias_target.iterdir() if p.is_file()}
        with self.assertRaises(ValueError):
            library.materialize(self.root)
        self.assertEqual({p.name: p.read_bytes() for p in alias_target.iterdir() if p.is_file()}, previous)

    def test_out_of_scope_snapshot_stops_before_content_read_and_checks_next_source(self):
        _, _, body = self.public_fixture()
        outside_scope = self.folder('code-b') / 'snapshot'
        outside_scope.mkdir()
        borrowed = outside_scope / 'source.txt'
        borrowed.write_bytes(body)
        self.change_public('content_file', 'sources/library/code-b/snapshot/source.txt')
        (self.folder('code-b') / 'README.md').unlink()
        original_read = Path.read_bytes
        reads = []

        def record_read(path):
            reads.append(path)
            return original_read(path)

        with patch.object(Path, 'read_bytes', autospec=True, side_effect=record_read):
            errors = library.check_library(self.root)
        self.assertTrue(any('paper-a' in error for error in errors))
        self.assertTrue(any('code-b' in error for error in errors))
        self.assertNotIn(borrowed, reads)
