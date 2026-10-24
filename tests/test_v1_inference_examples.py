"""推理教学模型的时间、容量、预算与统计契约；不运行服务或框架。"""
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import random
import unittest
from unittest.mock import Mock, call, patch


def load_example(name):
    path = Path(__file__).resolve().parents[1] / 'examples/inference' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prefill = load_example('prefill-decode')
cache = load_example('kv-cache')
scheduling = load_example('cache-scheduling')
frameworks = load_example('inference-frameworks')


class InferenceCase(unittest.TestCase):
    def assert_numbers(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=10)

    def run_demo(self, module, functions):
        from contextlib import ExitStack
        from socket import socket
        calls = {name: 0 for name in functions}

        def observe(name):
            real = getattr(module, name)

            def invoke(*args, **kwargs):
                calls[name] += 1
                return real(*args, **kwargs)
            return invoke

        with ExitStack() as stack:
            for name in functions:
                stack.enter_context(patch.object(module, name, wraps=observe(name)))
            stack.enter_context(patch.object(socket, 'connect', side_effect=AssertionError('禁止联网')))
            result = module.demo()
        self.assertTrue(all(value > 0 for value in calls.values()), calls)
        return result


class PrefillDecodeTests(InferenceCase):
    def test_request_timing_uses_output_intervals_not_total_latency(self):
        result = prefill.request_metrics(10, [10.8, 10.9, 11.0, 11.1, 11.2])
        self.assert_numbers([result['ttft_s'], result['e2e_s'], result['tpot_s']], [0.8, 1.2, 0.1])
        self.assert_numbers(result['itl_s'], [0.1] * 4)
        burst = prefill.request_metrics(0, [0.8, 0.81, 0.82, 0.83, 1.2])
        self.assertAlmostEqual(burst['tpot_s'], 0.1)
        self.assertAlmostEqual(max(burst['itl_s']), 0.37)

    def test_single_token_and_equal_timestamps(self):
        self.assertEqual(prefill.request_metrics(2, [2.5]), {
            'ttft_s': 0.5, 'e2e_s': 0.5, 'itl_s': [], 'tpot_s': None,
        })
        self.assertEqual(prefill.request_metrics(0, [0, 0])['tpot_s'], 0)

    def test_invalid_timestamp_sequence_is_rejected(self):
        for arrival, times in ((0, []), (1, [0]), (0, [1, 0.5]), (0, [float('inf')]), (float('nan'), [1])):
            with self.assertRaises(ValueError):
                prefill.request_metrics(arrival, times)

    def test_attention_work_matches_explicit_small_position_pairs(self):
        prompt_pairs = [(i, j) for i in range(3) for j in range(i + 1)]
        decode_pairs = [(i, j) for i in (3, 4) for j in range(i + 1)]
        self.assertEqual(prefill.attention_work(3, 2, 2, 3), {
            'prefill_pairs': len(prompt_pairs), 'decode_pairs': len(decode_pairs), 'attention_flops': 360,
        })
        self.assertEqual(prefill.attention_work(1, 0), {
            'prefill_pairs': 1, 'decode_pairs': 0, 'attention_flops': 4,
        })

    def test_attention_work_rejects_invalid_lengths_and_dimensions(self):
        for args in ((0, 1), (1, -1), (1.5, 1), (1, 1, 0), (1, 1, 1, 0)):
            with self.assertRaises(ValueError):
                prefill.attention_work(*args)

    def test_schedule_caps_each_request_and_preserves_input(self):
        rows = [('D', 101, 100), ('P', 12, 0)]
        before = copy.deepcopy(rows)
        self.assertEqual(prefill.schedule_tokens(rows, 5, 4), {'requests': [
            {'id': 'D', 'scheduled': 1, 'computed_after': 101},
            {'id': 'P', 'scheduled': 4, 'computed_after': 4}], 'remaining_budget': 0})
        self.assertEqual(rows, before)
        next_round = prefill.schedule_tokens([('D', 102, 101), ('P', 12, 4)], 3, 4)
        self.assertEqual([row['scheduled'] for row in next_round['requests']], [1, 2])
        self.assertEqual(next_round['requests'][1]['computed_after'], 6)

    def test_schedule_zero_budget_finished_target_and_surplus(self):
        rows = [('a', 4, 4), ('b', 2, 0)]
        zero = prefill.schedule_tokens(rows, 0, 4)
        self.assertEqual([r['scheduled'] for r in zero['requests']], [0, 0])
        spare = prefill.schedule_tokens(rows, 8, 4)
        self.assertEqual([r['scheduled'] for r in spare['requests']], [0, 2])
        self.assertEqual(spare['remaining_budget'], 6)

    def test_schedule_rejects_duplicate_ids_and_invalid_counts(self):
        for rows in ([('a', 1, 0), ('a', 2, 0)], [('a', 1, 2)], [('a', 2, -1)]):
            before = copy.deepcopy(rows)
            with self.assertRaises(ValueError):
                prefill.schedule_tokens(rows, 2, 1)
            self.assertEqual(rows, before)

    def test_demo_executes_all_prefill_functions(self):
        result = self.run_demo(prefill, ('request_metrics', 'attention_work', 'schedule_tokens'))
        self.assertEqual(result['work'], {'prefill_pairs': 10, 'decode_pairs': 11, 'attention_flops': 1344})
        self.assertAlmostEqual(result['timing']['tpot_s'], 0.1)
        self.assertEqual([r['scheduled'] for r in result['batch']['requests']], [1, 4])


class KvCacheTests(InferenceCase):
    def setUp(self):
        self.identity = {'model': 'm', 'adapter': 'a', 'tokenizer': 't', 'position': 'p', 'dtype': 'd', 'salt': 's'}

    def test_layout_distinguishes_effective_padding_and_page_rounding(self):
        self.assertEqual(cache.kv_layout([1, 4, 5], 2, 3, 4, 2, 4), {
            'bytes_per_token': 96, 'effective_bytes': 960, 'padded_bytes': 1440,
            'paged_bytes': 1536, 'blocks': 4, 'tail_waste_tokens': 6,
        })

    def test_layout_empty_zero_and_exact_page_boundaries(self):
        self.assertEqual(cache.kv_layout([], 1, 1, 1, 1, 4), {
            'bytes_per_token': 2, 'effective_bytes': 0, 'padded_bytes': 0,
            'paged_bytes': 0, 'blocks': 0, 'tail_waste_tokens': 0,
        })
        result = cache.kv_layout([0, 4], 1, 1, 1, 1, 4)
        self.assertEqual(result['blocks'], 1)
        self.assertEqual(result['tail_waste_tokens'], 0)
        self.assertEqual(result['padded_bytes'], 16)

    def test_layout_rejects_negative_lengths_and_zero_dimensions(self):
        with self.assertRaises(ValueError):
            cache.kv_layout([-1], 1, 1, 1, 1, 4)
        with self.assertRaises(ValueError):
            cache.kv_layout([1], 0, 1, 1, 1, 4)

    def test_cached_attention_reads_old_values_and_appends_without_aliasing(self):
        old_keys, old_values = [[1]], [[2]]
        result = cache.cached_attention([0], old_keys, old_values, [3], [4])
        self.assertEqual(result, {'output': [3], 'weights': [0.5, 0.5], 'keys': [[1], [3]], 'values': [[2], [4]]})
        result['keys'][0][0] = 99
        result['values'][0][0] = 99
        self.assertEqual(old_keys, [[1]])
        self.assertEqual(old_values, [[2]])

    def test_cached_attention_scaled_scores_and_first_token(self):
        result = cache.cached_attention([1, 0], [[math.sqrt(2) * math.log(3), 0]], [[2, 4]], [0, 0], [6, 8])
        self.assert_numbers(result['weights'], [0.75, 0.25])
        self.assert_numbers(result['output'], [3, 5])
        self.assertEqual(cache.cached_attention([1], [], [], [1000], [8])['output'], [8])

    def test_cached_attention_stable_scores_and_pairwise_permutation(self):
        first = cache.cached_attention([1], [[1000]], [[2]], [1000 + math.log(3)], [6])
        second = cache.cached_attention([1], [[1000 + math.log(3)]], [[6]], [1000], [2])
        self.assert_numbers(first['output'], [5])
        self.assert_numbers(first['output'], second['output'])

    def test_cached_attention_rejects_mismatched_cache(self):
        for args in (([1], [[1]], [], [2], [3]), ([1, 0], [], [], [1], [2]),
                     ([1], [], [], [float('nan')], [2])):
            with self.assertRaises(ValueError):
                cache.cached_attention(*args)

    def test_prefix_hash_uses_canonical_identity_and_complete_blocks(self):
        canonical = '["",[1,2],{"adapter":"a","dtype":"d","model":"m","position":"p","salt":"s","tokenizer":"t"}]'
        actual = cache.prefix_block_hashes([1, 2, 3, 4], 2, self.identity)
        self.assertEqual(actual[0], hashlib.sha256(canonical.encode('utf-8')).hexdigest())
        self.assertEqual(len(actual), 2)
        self.assertEqual(actual, cache.prefix_block_hashes([1, 2, 3, 4, 5], 2, dict(reversed(list(self.identity.items())))))
        self.assertEqual(cache.prefix_block_hashes([1], 2, self.identity), [])

    def test_prefix_and_each_computation_identity_invalidate_later_hash(self):
        baseline = cache.prefix_block_hashes([1, 2, 3, 4], 2, self.identity)
        changed = cache.prefix_block_hashes([9, 2, 3, 4], 2, self.identity)
        self.assertNotEqual(baseline[0], changed[0])
        self.assertNotEqual(baseline[1], changed[1])
        for field in self.identity:
            different = dict(self.identity, **{field: 'changed'})
            result = cache.prefix_block_hashes([1, 2, 3, 4], 2, different)
            self.assertTrue(all(a != b for a, b in zip(baseline, result)), field)

    def test_hash_rejects_invalid_tokens_blocks_or_identity(self):
        for tokens, block, identity in (([-1], 1, self.identity), ([1], 0, self.identity),
                                        ([1], 1, {}), ([1], 1, dict(self.identity, salt=1))):
            with self.assertRaises(ValueError):
                cache.prefix_block_hashes(tokens, block, identity)

    def test_demo_executes_three_kv_functions(self):
        result = self.run_demo(cache, ('kv_layout', 'cached_attention', 'prefix_block_hashes'))
        self.assertEqual(result['layout']['bytes_per_token'], 131072)
        self.assertEqual(result['layout']['effective_bytes'], 512 * 2**20)
        self.assertEqual(result['layout']['padded_bytes'], 768 * 2**20)
        self.assertEqual(result['attention']['output'], [3])
        self.assertEqual(len(result['hashes']), 2)


class CacheSchedulingTests(InferenceCase):
    def test_page_address_follows_unsorted_physical_table(self):
        self.assertEqual(scheduling.page_address([7, 1, 3], 9, 4), {'logical_block': 2, 'physical_block': 3, 'offset': 1})
        self.assertEqual(scheduling.page_address([7, 1, 3], 3, 4), {'logical_block': 0, 'physical_block': 7, 'offset': 3})
        self.assertEqual(scheduling.page_address([7, 1, 3], 4, 4), {'logical_block': 1, 'physical_block': 1, 'offset': 0})

    def test_page_address_explicit_bounds(self):
        with self.assertRaises(IndexError):
            scheduling.page_address([7], 4, 4)
        for table, point, size in (([7], -1, 4), ([7], 0, 0), ([-1], 0, 4)):
            with self.assertRaises(ValueError):
                scheduling.page_address(table, point, size)

    def test_iteration_releases_finished_then_admits_and_conserves_blocks(self):
        rows = [{'id': 'decode', 'computed': 4, 'target': 5, 'blocks': 1},
                {'id': 'prompt', 'computed': 0, 'target': 6, 'blocks': 0},
                {'id': 'done', 'computed': 4, 'target': 4, 'blocks': 1, 'finished': True}]
        before = copy.deepcopy(rows)
        result = scheduling.continuous_step(rows, 1, 5, 4)
        self.assertEqual([r['id'] for r in result['requests']], ['decode', 'prompt'])
        self.assertEqual([r['scheduled'] for r in result['requests']], [1, 4])
        self.assertEqual([r['computed'] for r in result['requests']], [5, 4])
        self.assertEqual([r['blocks'] for r in result['requests']], [2, 1])
        self.assertEqual(result['free_blocks'], 0)
        self.assertEqual(result['token_budget'], 0)
        self.assertEqual(sum(r['blocks'] for r in result['requests']) + result['free_blocks'],
                         sum(r['blocks'] for r in rows) + 1)
        self.assertEqual(rows, before)

    def test_insufficient_blocks_skip_without_consuming_tokens_or_preemption(self):
        rows = [{'id': 'large', 'computed': 0, 'target': 9, 'blocks': 0},
                {'id': 'small', 'computed': 0, 'target': 1, 'blocks': 0}]
        result = scheduling.continuous_step(rows, 1, 9, 4)
        self.assertEqual([r['scheduled'] for r in result['requests']], [0, 1])
        self.assertEqual(result['token_budget'], 8)
        self.assertEqual(result['free_blocks'], 0)
        self.assertEqual(result['requests'][0]['computed'], 0)

    def test_current_target_is_not_finished_and_allocated_space_can_be_used(self):
        rows = [{'id': 'caught_up', 'computed': 4, 'target': 4, 'blocks': 1},
                {'id': 'room', 'computed': 1, 'target': 4, 'blocks': 1}]
        result = scheduling.continuous_step(rows, 0, 3, 4)
        self.assertEqual([r['scheduled'] for r in result['requests']], [0, 3])
        self.assertEqual(len(result['requests']), 2)
        self.assertEqual(result['free_blocks'], 0)
        zero = scheduling.continuous_step(rows, 0, 0, 4)
        self.assertEqual([r['scheduled'] for r in zero['requests']], [0, 0])

    def test_iteration_rejects_invalid_capacity_or_duplicate_ids(self):
        for rows in ([{'id': 'a', 'computed': 5, 'target': 6, 'blocks': 1}],
                     [{'id': 'a', 'computed': 2, 'target': 1, 'blocks': 1}],
                     [{'id': 'a', 'computed': 0, 'target': 1, 'blocks': 0}] * 2):
            with self.assertRaises(ValueError):
                scheduling.continuous_step(rows, 1, 5, 4)

    def test_radix_split_preserves_suffixes_and_path_lock(self):
        self.assertEqual(scheduling.radix_split([1, 2, 3, 4], [1, 2, 9], 1, 2), {
            'matched_tokens': 2, 'prefix': [1, 2], 'old_suffix': [3, 4],
            'new_suffix': [9], 'prefix_lock_ref': 2,
        })
        aligned = scheduling.radix_split([1, 2, 3, 4], [1, 2, 9], 4, 2)
        self.assertEqual(aligned['matched_tokens'], 0)
        self.assertEqual(aligned['old_suffix'], [1, 2, 3, 4])
        self.assertEqual(aligned['new_suffix'], [1, 2, 9])

    def test_radix_prefix_empty_and_equal_inputs(self):
        self.assertEqual(scheduling.radix_split([1, 2, 3], [1, 2])['new_suffix'], [])
        self.assertEqual(scheduling.radix_split([1, 2], [1, 2])['matched_tokens'], 2)
        self.assertEqual(scheduling.radix_split([1], [9])['prefix'], [])
        self.assertEqual(scheduling.radix_split([], [1])['new_suffix'], [1])
        with self.assertRaises(ValueError):
            scheduling.radix_split([1], [1], lock_ref=-1)

    def test_demo_covers_address_iteration_and_radix_functions(self):
        result = self.run_demo(scheduling, ('page_address', 'continuous_step', 'radix_split'))
        self.assertEqual(result['address'], {'logical_block': 2, 'physical_block': 3, 'offset': 1})
        self.assertEqual([r['scheduled'] for r in result['step']['requests']], [1, 4])
        self.assertEqual(result['split']['prefix'], [1, 2])


class InferenceFrameworkTests(InferenceCase):
    def test_gamma_arrivals_use_theoretical_parameters_and_n_minus_one_intervals(self):
        rng = Mock(spec=['gammavariate'])
        rng.gammavariate.side_effect = [0.25, 0.75, 0.5]
        with patch.object(frameworks.random, 'Random', return_value=rng) as factory:
            result = frameworks.arrival_schedule(4, 2, burstiness=4, seed=7)
        self.assertEqual(result, [0, 0.25, 1, 1.5])
        factory.assert_called_once_with(7)
        self.assertEqual(rng.gammavariate.call_args_list, [call(4, 0.125)] * 3)
        shape, scale = rng.gammavariate.call_args.args
        self.assertEqual(shape * scale, 0.5)
        self.assertEqual(shape * scale**2, 0.0625)

    def test_real_gamma_repeats_locally_and_accepts_zero_or_one_request(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        first = frameworks.arrival_schedule(8, 2, 0.5, seed=9)
        self.assertEqual(first, frameworks.arrival_schedule(8, 2, 0.5, seed=9))
        self.assertEqual(random.getstate(), state)
        self.assertEqual(first[0], 0)
        self.assertTrue(all(b > a for a, b in zip(first, first[1:])))
        self.assertEqual(frameworks.arrival_schedule(0, 1), [])
        self.assertEqual(frameworks.arrival_schedule(1, 1), [0])

    def test_arrival_parameters_reject_documented_invalid_values(self):
        for args in ((-1, 1), (1, 0), (1, 1, 0), (1, float('nan')), (1, 1, float('inf'))):
            with self.assertRaises(ValueError):
                frameworks.arrival_schedule(*args)

    def test_joint_slo_quality_and_failure_denominators(self):
        rows = [
            {'success': True, 'quality_ok': True, 'ttft': 0.5, 'latency': 1.5, 'output_tokens': 3},
            {'success': True, 'quality_ok': True, 'ttft': 0.75, 'latency': 0.875, 'output_tokens': 2},
            {'success': True, 'quality_ok': True, 'ttft': 0.25, 'latency': 1.75, 'output_tokens': 3},
            {'success': True, 'quality_ok': False, 'ttft': 0.25, 'latency': 0.25, 'output_tokens': 1},
            {'success': False},
        ]
        before = copy.deepcopy(rows)
        self.assertEqual(frameworks.qualified_metrics(rows, 2, 0.5, 0.5), {
            'offered': 5, 'completed': 4, 'qualified': 1, 'attainment': 0.2,
            'completion_rate': 0.8, 'request_rps': 2, 'qualified_rps': 0.5, 'output_tokens_per_s': 4.5,
        })
        self.assertEqual(rows, before)

    def test_single_token_tpot_is_not_applicable(self):
        row = {'success': True, 'quality_ok': True, 'ttft': 0.5, 'latency': 10, 'output_tokens': 1}
        result = frameworks.qualified_metrics([row], 10, 0.5, 0)
        self.assertEqual(result['qualified'], 1)
        self.assertEqual(result['attainment'], 1)

    def test_failed_only_and_empty_offered_sets_differ(self):
        empty = frameworks.qualified_metrics([], 2, 1, 1)
        failed = frameworks.qualified_metrics([{'success': False}], 2, 1, 1)
        self.assertIsNone(empty['attainment'])
        self.assertIsNone(empty['completion_rate'])
        self.assertEqual(failed['attainment'], 0)
        self.assertEqual(failed['completion_rate'], 0)
        self.assertEqual(failed['output_tokens_per_s'], 0)

    def test_success_rows_need_valid_timing_and_positive_token_count(self):
        base = {'success': True, 'quality_ok': True, 'ttft': 1, 'latency': 2, 'output_tokens': 2}
        for changes in ({'ttft': -1}, {'latency': 0.5}, {'output_tokens': 0}, {'latency': float('inf')}):
            with self.assertRaises(ValueError):
                frameworks.qualified_metrics([dict(base, **changes)], 2, 1, 1)
        with self.assertRaises(ValueError):
            frameworks.qualified_metrics([], 0, 1, 1)

    def test_nearest_rank_tail_differs_at_equal_mean(self):
        self.assertEqual(frameworks.latency_summary([1, 1, 1, 1, 6]), {'count': 5, 'mean': 2, 'percentile': 6})
        self.assertEqual(frameworks.latency_summary([2] * 5)['percentile'], 2)
        values = [8, 1, 4, 2]
        self.assertEqual(frameworks.latency_summary(values, 0.5), {'count': 4, 'mean': 3.75, 'percentile': 2})
        self.assertEqual(values, [8, 1, 4, 2])

    def test_empty_single_and_percentile_endpoints(self):
        self.assertEqual(frameworks.latency_summary([]), {'count': 0, 'mean': None, 'percentile': None})
        self.assertEqual(frameworks.latency_summary([0]), {'count': 1, 'mean': 0, 'percentile': 0})
        self.assertEqual(frameworks.latency_summary([1, 2, 4], 1)['percentile'], 4)
        self.assertEqual(frameworks.latency_summary([1, 2, 4], 0.01)['percentile'], 1)
        for values, p in (([-1], 0.5), ([float('nan')], 0.5), ([1], 0), ([1], 1.1)):
            with self.assertRaises(ValueError):
                frameworks.latency_summary(values, p)

    def test_demo_covers_arrival_joint_metrics_and_tail(self):
        result = self.run_demo(frameworks, ('arrival_schedule', 'qualified_metrics', 'latency_summary'))
        self.assertEqual(len(result['arrivals']), 4)
        self.assertEqual(result['arrivals'][0], 0)
        self.assertEqual(result['metrics']['qualified_rps'], 0.5)
        self.assertEqual(result['metrics']['attainment'], 1 / 3)
        self.assertEqual(result['tail'], {'count': 5, 'mean': 2, 'percentile': 6})

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_prefill_decode_cli(self):
        assert_cli_matches_demo(self, 'examples/inference/prefill-decode.py')

    def test_prefill_decode_quiet_import(self):
        assert_quiet_import(self, 'examples/inference/prefill-decode.py')

    def test_kv_cache_cli(self):
        assert_cli_matches_demo(self, 'examples/inference/kv-cache.py')

    def test_kv_cache_quiet_import(self):
        assert_quiet_import(self, 'examples/inference/kv-cache.py')

    def test_cache_scheduling_cli(self):
        assert_cli_matches_demo(self, 'examples/inference/cache-scheduling.py')

    def test_cache_scheduling_quiet_import(self):
        assert_quiet_import(self, 'examples/inference/cache-scheduling.py')

    def test_inference_frameworks_cli(self):
        assert_cli_matches_demo(self, 'examples/inference/inference-frameworks.py')

    def test_inference_frameworks_quiet_import(self):
        assert_quiet_import(self, 'examples/inference/inference-frameworks.py')
