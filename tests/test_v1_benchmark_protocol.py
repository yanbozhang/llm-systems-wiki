"""评测协议教学契约测试，不执行模型或第三方评测工具。

依据：wiki/topics/评测协议与可复现性.md 的三个知识点及本轮单元契约。
指纹使用独立手写的规范字节；交集与评分使用可手算的小输入。
"""
import copy
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import socket
import unittest
from unittest.mock import patch


EXAMPLE_PATH = (Path(__file__).resolve().parents[1]
                / 'examples/benchmark/benchmark-protocol.py')
SPEC = importlib.util.spec_from_file_location('benchmark_protocol_example', EXAMPLE_PATH)
example = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example)


class ProtocolFingerprintTests(unittest.TestCase):
    def test_canonical_utf8_bytes_match_sha256(self):
        # 知识点一：键排序、无空白分隔符、UTF-8；不调用目标生成期望。
        protocol = {'z': '中文', 'a': {'seed': 7, 'b': [True, None, 2]}}
        canonical = '{"a":{"b":[true,null,2],"seed":7},"z":"中文"}'.encode('utf-8')
        self.assertEqual(example.protocol_fingerprint(protocol),
                         hashlib.sha256(canonical).hexdigest())

    def test_nested_key_order_does_not_change_identity(self):
        first = {'z': 2, 'a': {'seed': 7, 'template': '中文'}}
        second = {'a': {'template': '中文', 'seed': 7}, 'z': 2}
        self.assertEqual(example.protocol_fingerprint(first),
                         example.protocol_fingerprint(second))

    def test_array_order_remains_part_of_protocol(self):
        self.assertNotEqual(example.protocol_fingerprint({'shots': ['a', 'b']}),
                            example.protocol_fingerprint({'shots': ['b', 'a']}))

    def test_each_declared_condition_changes_identity(self):
        protocol = {'model': 'm1', 'data': 'd1', 'template': 't1',
                    'scorer': 's1', 'seed': 7, 'budget': 1}
        baseline = example.protocol_fingerprint(protocol)
        for field, value in [('model', 'm2'), ('data', 'd2'), ('template', 't2'),
                             ('scorer', 's2'), ('seed', 8), ('budget', 2)]:
            changed = dict(protocol, **{field: value})
            self.assertNotEqual(example.protocol_fingerprint(changed), baseline, field)

    def test_additional_field_is_retained(self):
        self.assertNotEqual(example.protocol_fingerprint({'seed': 7}),
                            example.protocol_fingerprint({'seed': 7, 'scorer': 'v2'}))

    def test_minimal_protocol_and_input_are_preserved(self):
        protocol = {'seed': 0}
        before = copy.deepcopy(protocol)
        self.assertEqual(example.protocol_fingerprint(protocol),
                         hashlib.sha256(b'{"seed":0}').hexdigest())
        self.assertEqual(protocol, before)

    def test_empty_protocol_is_rejected(self):
        with self.assertRaises(ValueError):
            example.protocol_fingerprint({})

    def test_non_object_protocol_is_rejected(self):
        for protocol in (None, [], ['seed', 7], 'seed', 7, False):
            with self.assertRaises(ValueError, msg=repr(protocol)):
                example.protocol_fingerprint(protocol)

    def test_nan_is_rejected(self):
        with self.assertRaises(ValueError):
            example.protocol_fingerprint({'temperature': float('nan')})

    def test_nested_nan_is_rejected(self):
        with self.assertRaises(ValueError):
            example.protocol_fingerprint({'settings': [{'temperature': float('nan')}]})

    def test_non_json_values_are_rejected(self):
        for value in ({'a', 'b'}, b'bytes'):
            with self.assertRaises((TypeError, ValueError), msg=repr(value)):
                example.protocol_fingerprint({'invalid': value})


class SplitOverlapTests(unittest.TestCase):
    def test_hand_computed_train_dev_test_intersection(self):
        # 知识点二的手算例子，返回名称也必须按排序定位同一对切分。
        splits = {'train': ['a', 'b'], 'dev': ['c'], 'test': ['b', 'd']}
        self.assertEqual(example.split_overlap(splits), {('test', 'train'): ['b']})

    def test_all_pairs_and_intersection_ids_are_sorted(self):
        splits = {'z': ['s', 'p', 'r'], 'm': ['s', 'q', 'r'],
                  'a': ['r', 'q', 'p', 'r'], 'empty': []}
        self.assertEqual(list(example.split_overlap(splits).items()), [
            (('a', 'm'), ['q', 'r']),
            (('a', 'z'), ['p', 'r']),
            (('m', 'z'), ['r', 's']),
        ])

    def test_repeated_ids_within_split_are_collapsed(self):
        self.assertEqual(example.split_overlap({'a': ['x', 'x'], 'b': ['x', 'x']}),
                         {('a', 'b'): ['x']})

    def test_distinct_ids_do_not_imply_content_detection(self):
        # 接口只接收ID；同正文重新命名的样本也只能得到空交集。
        self.assertEqual(example.split_overlap({'train': ['original'],
                                                'test': ['renamed']}), {})

    def test_empty_or_single_split_has_no_pair(self):
        for splits in ({}, {'one': []}, {'one': ['x', 'x']}, {'a': [], 'b': []}):
            self.assertEqual(example.split_overlap(splits), {})

    def test_input_order_does_not_change_output_or_mutate_inputs(self):
        splits = {'z': ['b', 'a'], 'a': ['a', 'b', 'a'], 'm': ['a']}
        before = copy.deepcopy(splits)
        reordered = {key: list(reversed(value)) for key, value in reversed(list(splits.items()))}
        self.assertEqual(list(example.split_overlap(splits).items()),
                         list(example.split_overlap(reordered).items()))
        self.assertEqual(splits, before)

    def test_non_mapping_splits_are_rejected(self):
        for splits in (None, [], [('train', ['a'])], 'train'):
            with self.assertRaises(ValueError, msg=repr(splits)):
                example.split_overlap(splits)

    def test_non_string_split_name_is_rejected(self):
        for name in (1, None, False):
            with self.assertRaises(ValueError, msg=repr(name)):
                example.split_overlap({name: ['a'], 'valid': ['a']})

    def test_non_list_id_collection_is_rejected(self):
        for ids in (None, 'a', ('a',), {'a'}, {'id': 'a'}):
            with self.assertRaises(ValueError, msg=repr(ids)):
                example.split_overlap({'train': ids, 'test': ['a']})

    def test_empty_id_is_rejected_even_without_other_splits(self):
        with self.assertRaises(ValueError):
            example.split_overlap({'train': ['valid', '']})

    def test_non_string_id_is_rejected_before_set_comparison(self):
        for invalid in (1, None, False, [], {}):
            with self.assertRaises(ValueError, msg=repr(invalid)):
                example.split_overlap({'train': ['valid', invalid], 'test': ['valid']})


class ScoreRunTests(unittest.TestCase):
    def test_three_states_use_their_distinct_denominators(self):
        # 知识点三：1 pass + 1 fail + 1 error -> 1/3, 1/3, 1/2。
        records = [{'id': 'a', 'status': 'passed'}, {'id': 'b', 'status': 'failed'},
                   {'id': 'c', 'status': 'error'}]
        self.assertEqual(example.score_run(records), {
            'n': 3, 'counts': {'passed': 1, 'failed': 1, 'error': 1},
            'success_rate': 1 / 3, 'error_rate': 1 / 3, 'scored_accuracy': 1 / 2,
        })

    def test_unequal_counts_distinguish_state_mapping_and_denominators(self):
        records = [{'id': str(i), 'status': state} for i, state in enumerate(
            ('error', 'passed', 'failed', 'error', 'passed', 'error'))]
        result = example.score_run(records)
        self.assertEqual(result['n'], 6)
        self.assertEqual(result['counts'], {'passed': 2, 'failed': 1, 'error': 3})
        self.assertEqual(sum(result['counts'].values()), result['n'])
        self.assertAlmostEqual(result['success_rate'], 1 / 3)
        self.assertEqual(result['error_rate'], 1 / 2)
        self.assertAlmostEqual(result['scored_accuracy'], 2 / 3)

    def test_all_passed(self):
        self.assertEqual(example.score_run([{'id': 'a', 'status': 'passed'}]), {
            'n': 1, 'counts': {'passed': 1, 'failed': 0, 'error': 0},
            'success_rate': 1.0, 'error_rate': 0.0, 'scored_accuracy': 1.0,
        })

    def test_all_failed(self):
        self.assertEqual(example.score_run([{'id': 'a', 'status': 'failed'}]), {
            'n': 1, 'counts': {'passed': 0, 'failed': 1, 'error': 0},
            'success_rate': 0.0, 'error_rate': 0.0, 'scored_accuracy': 0.0,
        })

    def test_all_errors_leave_scored_accuracy_undefined(self):
        self.assertEqual(example.score_run([{'id': 'a', 'status': 'error'},
                                           {'id': 'b', 'status': 'error'}]), {
            'n': 2, 'counts': {'passed': 0, 'failed': 0, 'error': 2},
            'success_rate': 0.0, 'error_rate': 1.0, 'scored_accuracy': None,
        })

    def test_order_independence_and_pure_inputs(self):
        records = [{'id': '甲', 'status': 'passed'}, {'id': '乙', 'status': 'failed'}]
        before = copy.deepcopy(records)
        self.assertEqual(example.score_run(records), example.score_run(list(reversed(records))))
        self.assertEqual(records, before)

    def test_empty_or_non_list_records_are_rejected(self):
        for records in ([], None, {}, {'id': 'a', 'status': 'passed'},
                        ({'id': 'a', 'status': 'passed'},)):
            with self.assertRaises(ValueError, msg=repr(records)):
                example.score_run(records)

    def test_non_object_record_is_not_silently_skipped(self):
        for row in (None, 'a', 1, [], False):
            with self.assertRaises(ValueError, msg=repr(row)):
                example.score_run([{'id': 'valid', 'status': 'passed'}, row])

    def test_missing_id_is_rejected(self):
        with self.assertRaises(ValueError):
            example.score_run([{'id': 'valid', 'status': 'passed'}, {'status': 'failed'}])

    def test_empty_id_is_rejected(self):
        with self.assertRaises(ValueError):
            example.score_run([{'id': '', 'status': 'passed'}])

    def test_non_string_id_is_rejected(self):
        for key in (None, 0, False, [], {}):
            with self.assertRaises(ValueError, msg=repr(key)):
                example.score_run([{'id': key, 'status': 'passed'}])

    def test_repeated_same_state_cannot_reweight_sample(self):
        with self.assertRaises(ValueError):
            example.score_run([{'id': 'a', 'status': 'passed'},
                               {'id': 'b', 'status': 'failed'},
                               {'id': 'a', 'status': 'passed'}])

    def test_conflicting_attempts_are_not_merged(self):
        with self.assertRaises(ValueError):
            example.score_run([{'id': 'a', 'status': 'error'},
                               {'id': 'a', 'status': 'passed'}])

    def test_missing_status_is_rejected(self):
        with self.assertRaises(ValueError):
            example.score_run([{'id': 'valid', 'status': 'passed'}, {'id': 'invalid'}])

    def test_unknown_status_is_rejected(self):
        for status in ('', 'skipped', 'PASS', 'Passed', 'pending'):
            with self.assertRaises(ValueError, msg=repr(status)):
                example.score_run([{'id': 'valid', 'status': 'passed'},
                                   {'id': 'invalid', 'status': status}])

    def test_non_string_status_is_rejected(self):
        for status in (None, 1, False, [], {}):
            with self.assertRaises(ValueError, msg=repr(status)):
                example.score_run([{'id': 'a', 'status': status}])


class DemoTests(unittest.TestCase):
    def test_demo_executes_real_functions_and_returns_offline_results(self):
        # wraps 保留真实计算；只观察演示是否调用三个被测入口。
        output = io.StringIO()
        observed = {}

        def observe(name):
            real_function = getattr(example, name)

            def call(*args, **kwargs):
                value = real_function(*args, **kwargs)
                observed[name] = copy.deepcopy(value)
                return value
            return call

        with patch.object(example, 'protocol_fingerprint', wraps=observe('protocol_fingerprint')) as fingerprint, \
             patch.object(example, 'split_overlap', wraps=observe('split_overlap')) as overlap, \
             patch.object(example, 'score_run', wraps=observe('score_run')) as score, \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('禁止联网')) as connect, \
             patch.object(socket, 'create_connection', side_effect=AssertionError('禁止联网')) as create, \
             redirect_stdout(output):
            result = example.demo()
        fingerprint.assert_called_once()
        overlap.assert_called_once()
        score.assert_called_once()
        connect.assert_not_called()
        create.assert_not_called()
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(set(result), {'protocol', 'overlap', 'result'})
        self.assertRegex(result['protocol'], r'^[0-9a-f]{64}$')
        self.assertEqual(result['protocol'], observed['protocol_fingerprint'])
        self.assertEqual(result['overlap'], [['b']])
        self.assertEqual(result['overlap'], list(observed['split_overlap'].values()))
        self.assertEqual(result['result'], observed['score_run'])
        self.assertEqual(result['result'], {
            'n': 3, 'counts': {'passed': 1, 'failed': 1, 'error': 1},
            'success_rate': 1 / 3, 'error_rate': 1 / 3, 'scored_accuracy': 1 / 2,
        })
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_benchmark_protocol_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-protocol.py')

    def test_benchmark_protocol_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-protocol.py')
