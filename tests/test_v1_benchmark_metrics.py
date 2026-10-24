"""统计教学契约测试；期望取自手算、检验不等式与配对不变量。

依据：wiki/topics/评测指标与统计推断.md 三个知识点。
不执行模型或第三方代码，不把重采样分布当作置信区间或胜负结论。
"""
import copy
import importlib.util
import io
import json
import math
from contextlib import redirect_stdout
from pathlib import Path
import random
import socket
from statistics import NormalDist
import unittest
from unittest.mock import Mock, call, patch


EXAMPLE_PATH = (Path(__file__).resolve().parents[1]
                / 'examples/benchmark/benchmark-metrics.py')
SPEC = importlib.util.spec_from_file_location('benchmark_metrics_example', EXAMPLE_PATH)
example = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example)


class GroupedAccuracyTests(unittest.TestCase):
    def test_unequal_groups_have_micro_082_and_macro_05(self):
        # 独立手算：82/100，(9/10 + 1/10)/2。
        groups = {'A': [1] * 81 + [0] * 9, 'B': [1] + [0] * 9}
        self.assertEqual(example.grouped_accuracy(groups), {
            'micro': 0.82, 'macro': 0.5, 'by_group': {'A': 0.9, 'B': 0.1}, 'n': 100,
        })

    def test_single_group_and_boolean_binary_outcomes(self):
        self.assertEqual(example.grouped_accuracy({'甲': [True, False, 1, 0]}), {
            'micro': 0.5, 'macro': 0.5, 'by_group': {'甲': 0.5}, 'n': 4,
        })

    def test_all_wrong_and_all_correct_probability_boundaries(self):
        self.assertEqual(example.grouped_accuracy({'wrong': [0, 0]})['micro'], 0.0)
        self.assertEqual(example.grouped_accuracy({'wrong': [0, 0]})['macro'], 0.0)
        self.assertEqual(example.grouped_accuracy({'right': [1]})['micro'], 1.0)
        self.assertEqual(example.grouped_accuracy({'right': [1]})['macro'], 1.0)

    def test_repeating_one_group_changes_micro_but_not_macro(self):
        first = example.grouped_accuracy({'a': [1], 'b': [0]})
        expanded = example.grouped_accuracy({'a': [1, 1, 1], 'b': [0]})
        self.assertEqual(first['micro'], 0.5)
        self.assertEqual(expanded['micro'], 0.75)
        self.assertEqual(first['macro'], expanded['macro'])
        self.assertEqual(expanded['by_group'], {'a': 1.0, 'b': 0.0})
        self.assertEqual(expanded['n'], 4)

    def test_group_and_sample_order_do_not_mutate_or_change_metrics(self):
        groups = {'z': [1, 0, 1], 'a': [0, 1]}
        before = copy.deepcopy(groups)
        reverse = {name: list(reversed(values)) for name, values in reversed(list(groups.items()))}
        self.assertEqual(example.grouped_accuracy(groups), example.grouped_accuracy(reverse))
        self.assertEqual(groups, before)

    def test_empty_or_non_mapping_groups_are_rejected(self):
        for groups in ({}, None, [], [('a', [1])]):
            with self.assertRaises(ValueError, msg=repr(groups)):
                example.grouped_accuracy(groups)

    def test_empty_group_is_not_given_zero_weight_or_score(self):
        with self.assertRaises(ValueError):
            example.grouped_accuracy({'valid': [1, 0], 'empty': []})

    def test_non_string_group_name_is_rejected(self):
        with self.assertRaises(ValueError):
            example.grouped_accuracy({1: [1, 0]})

    def test_non_list_group_values_are_rejected(self):
        for values in ('10', (1, 0), {1, 0}, None):
            with self.assertRaises(ValueError, msg=repr(values)):
                example.grouped_accuracy({'a': values})

    def test_non_binary_and_truthy_objects_are_rejected(self):
        for value in (-1, 2, 0.5, '错误', '1', None, [], {}, float('nan')):
            with self.assertRaises(ValueError, msg=repr(value)):
                example.grouped_accuracy({'valid': [1], 'invalid': [0, value]})


class WilsonIntervalTests(unittest.TestCase):
    def test_90_of_100_matches_documented_interval(self):
        lower, upper = example.wilson_interval(90, 100)
        self.assertAlmostEqual(lower, 0.826, delta=0.0005)
        self.assertAlmostEqual(upper, 0.945, delta=0.0005)

    def test_endpoints_solve_original_score_inequality(self):
        # 不重复中心/半径实现。边界满足 n*(k/n-p)^2 = z^2*p*(1-p)。
        k, n, z = 3, 7, 1.5
        lower, upper = example.wilson_interval(k, n, z)

        def residual(p):
            return n * (k / n - p) ** 2 - z ** 2 * p * (1 - p)

        self.assertAlmostEqual(residual(lower), 0.0, delta=1e-12)
        self.assertAlmostEqual(residual(upper), 0.0, delta=1e-12)
        self.assertLess(residual((lower + upper) / 2), 0)
        self.assertGreater(residual(lower - 0.001), 0)
        self.assertGreater(residual(upper + 0.001), 0)

    def test_default_is_two_sided_95_percent_critical_value(self):
        z = NormalDist().inv_cdf(0.975)
        lower, upper = example.wilson_interval(4, 9)
        for bound in (lower, upper):
            self.assertAlmostEqual(9 * (4 / 9 - bound) ** 2,
                                   z * z * bound * (1 - bound), delta=1e-12)

    def test_zero_success_has_positive_upper_bound(self):
        # k=0, n=3, z=1：不等式化简为 p*(4*p-1)<=0。
        lower, upper = example.wilson_interval(0, 3, z=1)
        self.assertEqual(lower, 0.0)
        self.assertAlmostEqual(upper, 0.25)

    def test_all_success_has_lower_bound_below_one(self):
        lower, upper = example.wilson_interval(3, 3, z=1)
        self.assertAlmostEqual(lower, 0.75)
        self.assertEqual(upper, 1.0)

    def test_single_trial_and_all_small_counts_stay_in_probability_range(self):
        for total in (1, 2, 10):
            for successes in range(total + 1):
                lower, upper = example.wilson_interval(successes, total)
                self.assertTrue(math.isfinite(lower) and math.isfinite(upper))
                self.assertLessEqual(0, lower)
                # 端点计算允许一个浮点舍入误差；[0,1]范围仍严格检查。
                self.assertLessEqual(lower, successes / total + 1e-12)
                self.assertLessEqual(successes / total, upper + 1e-12)
                self.assertLessEqual(upper, 1)

    def test_success_failure_complement_reflects_interval(self):
        low_a, high_a = example.wilson_interval(2, 10, z=2)
        low_b, high_b = example.wilson_interval(8, 10, z=2)
        self.assertAlmostEqual(low_a, 1 - high_b)
        self.assertAlmostEqual(high_a, 1 - low_b)

    def test_larger_positive_z_widens_interval(self):
        narrow = example.wilson_interval(4, 10, z=1)
        wide = example.wilson_interval(4, 10, z=2)
        self.assertLess(wide[0], narrow[0])
        self.assertGreater(wide[1], narrow[1])

    def test_non_integer_counts_are_rejected(self):
        for successes, total in ((1.0, 2), (1, 2.0), ('1', 2), (1, '2'),
                                  (None, 2), (True, 2), (0, False)):
            with self.assertRaises(ValueError, msg=repr((successes, total))):
                example.wilson_interval(successes, total)

    def test_invalid_count_bounds_are_rejected(self):
        for successes, total in ((0, 0), (0, -1), (-1, 2), (3, 2)):
            with self.assertRaises(ValueError, msg=repr((successes, total))):
                example.wilson_interval(successes, total)

    def test_nonpositive_nonfinite_or_nonnumeric_z_is_rejected(self):
        # bool类型的z契约未知，特意不从其当前行为推导测试要求。
        for z in (0, -1, float('nan'), float('inf'), -float('inf'), '1.96', None):
            with self.assertRaises(ValueError, msg=repr(z)):
                example.wilson_interval(1, 2, z=z)


class PairedBootstrapTests(unittest.TestCase):
    def test_documented_shared_indices_produce_hand_computed_means(self):
        # 文档差值[0,1,0,0]，索引两轮分别给出[1,1,0,0]和[0,0,0,0]。
        rng = Mock(spec=['randrange'])
        rng.randrange.side_effect = [1, 1, 0, 2, 0, 2, 3, 0]
        with patch.object(example.random, 'Random', return_value=rng) as factory:
            result = example.paired_bootstrap([1, 1, 0, 1], [1, 0, 0, 1], draws=2, seed=23)
        self.assertEqual(result, {'observed': 0.25, 'replicates': [0.5, 0.0]})
        factory.assert_called_once_with(23)
        self.assertEqual(rng.randrange.call_args_list, [call(4)] * 8)

    def test_identical_nonconstant_scores_have_zero_difference(self):
        scores = [0, 1, 0.25, 0.75]
        self.assertEqual(example.paired_bootstrap(scores, scores, draws=20, seed=9),
                         {'observed': 0.0, 'replicates': [0.0] * 20})

    def test_constant_paired_difference_survives_real_resampling(self):
        result = example.paired_bootstrap([0.25, 0.75, 1], [0, 0.5, 0.75], draws=20)
        self.assertEqual(result, {'observed': 0.25, 'replicates': [0.25] * 20})

    def test_single_pair_and_single_draw_are_valid(self):
        self.assertEqual(example.paired_bootstrap([0.25], [0.75], draws=1, seed=-2),
                         {'observed': -0.5, 'replicates': [-0.5]})

    def test_same_seed_repeats_without_mutating_inputs_or_global_random(self):
        a, b = [0, 1, 0.25, 1], [1, 0, 0.75, 1]
        before = copy.deepcopy((a, b))
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        first = example.paired_bootstrap(a, b, draws=25, seed=11)
        second = example.paired_bootstrap(a, b, draws=25, seed=11)
        self.assertEqual(first, second)
        self.assertEqual((a, b), before)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(first['observed'], -0.125)
        self.assertEqual(len(first['replicates']), 25)

    def test_swapping_systems_negates_every_paired_replicate(self):
        a, b = [1, 0.25, 0], [0, 0.75, 0.5]
        forward = example.paired_bootstrap(a, b, draws=13, seed=5)
        reverse = example.paired_bootstrap(b, a, draws=13, seed=5)
        self.assertEqual(forward['observed'], -reverse['observed'])
        self.assertEqual(forward['replicates'], [-x for x in reverse['replicates']])

    def test_real_replicates_have_requested_count_and_empirical_support(self):
        result = example.paired_bootstrap([1, 0], [0, 1], draws=17, seed=3)
        self.assertEqual(result['observed'], 0.0)
        self.assertEqual(len(result['replicates']), 17)
        self.assertTrue(all(value in (-1, 0, 1) for value in result['replicates']))

    def test_empty_and_misaligned_scores_are_rejected(self):
        for a, b in (([], []), ([], [1]), ([1], []), ([1, 0], [1])):
            with self.assertRaises(ValueError, msg=repr((a, b))):
                example.paired_bootstrap(a, b, draws=2)

    def test_both_inputs_require_lists(self):
        for a, b in ((None, [1]), ([1], None), ((1,), [1]), ([1], (1,)), ('1', [1])):
            with self.assertRaises(ValueError, msg=repr((a, b))):
                example.paired_bootstrap(a, b, draws=2)

    def test_invalid_score_on_either_side_is_rejected(self):
        for invalid in (-0.01, 1.01, float('nan'), float('inf'), -float('inf'),
                        '1', None, True, [], {}):
            for a, b in (([0, invalid], [0, 1]), ([0, 1], [0, invalid])):
                with self.assertRaises(ValueError, msg=repr((a, b))):
                    example.paired_bootstrap(a, b, draws=2)

    def test_draws_must_be_a_positive_integer(self):
        for draws in (0, -1, 1.5, '2', None, True):
            with self.assertRaises(ValueError, msg=repr(draws)):
                example.paired_bootstrap([1], [0], draws=draws)

    def test_seed_must_be_an_integer(self):
        for seed in (1.5, '7', None, True):
            with self.assertRaises(ValueError, msg=repr(seed)):
                example.paired_bootstrap([1], [0], draws=2, seed=seed)


class MetricsDemoTests(unittest.TestCase):
    def test_demo_runs_real_statistics_and_returns_serializable_results(self):
        observed = {}

        def observe(name):
            real_function = getattr(example, name)

            def invoke(*args, **kwargs):
                value = real_function(*args, **kwargs)
                observed[name] = copy.deepcopy(value)
                return value
            return invoke

        output = io.StringIO()
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        with patch.object(example, 'grouped_accuracy', wraps=observe('grouped_accuracy')) as groups, \
             patch.object(example, 'wilson_interval', wraps=observe('wilson_interval')) as wilson, \
             patch.object(example, 'paired_bootstrap', wraps=observe('paired_bootstrap')) as paired, \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('禁止联网')) as connect, \
             redirect_stdout(output):
            result = example.demo()
        groups.assert_called_once()
        wilson.assert_called_once()
        paired.assert_called_once()
        connect.assert_not_called()
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(random.getstate(), state)
        self.assertEqual(set(result), {'accuracy', 'wilson_90_of_100', 'paired_example'})
        self.assertEqual(result['accuracy'], observed['grouped_accuracy'])
        self.assertEqual(result['wilson_90_of_100'], observed['wilson_interval'])
        self.assertEqual(result['paired_example'], observed['paired_bootstrap'])
        self.assertEqual(result['accuracy']['micro'], 0.82)
        self.assertEqual(result['accuracy']['macro'], 0.5)
        self.assertAlmostEqual(result['wilson_90_of_100'][0], 0.826, delta=0.0005)
        self.assertAlmostEqual(result['wilson_90_of_100'][1], 0.945, delta=0.0005)
        self.assertEqual(result['paired_example']['observed'], 0.25)
        self.assertEqual(len(result['paired_example']['replicates']), 8)
        serialized = json.loads(json.dumps(result, allow_nan=False))
        self.assertEqual(serialized['accuracy'], result['accuracy'])
        self.assertEqual(serialized['wilson_90_of_100'], list(result['wilson_90_of_100']))
        self.assertEqual(serialized['paired_example'], result['paired_example'])

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_benchmark_metrics_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-metrics.py')

    def test_benchmark_metrics_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-metrics.py')
