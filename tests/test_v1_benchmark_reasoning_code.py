"""精确有理数、采样池子集概率与执行记录汇总，不执行生成代码。"""
import copy
import importlib.util
import itertools
from pathlib import Path
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / 'examples/benchmark/benchmark-reasoning-code.py'
spec = importlib.util.spec_from_file_location('benchmark_reasoning_code_example', path)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class NumericEquivalenceTests(unittest.TestCase):
    def test_exact_decimal_fraction_sign_and_no_float_tolerance(self):
        self.assertIs(example.numeric_equivalence('0.5', '1/2'), True)
        self.assertIs(example.numeric_equivalence(' -2/4 ', '-0.5'), True)
        self.assertIs(example.numeric_equivalence('0.5001', '1/2'), False)
        self.assertIs(example.numeric_equivalence('0.1000000000000000000001', '1/10'), False)
        self.assertIs(example.numeric_equivalence('1e-3', '1/1000'), True)

    def test_unparseable_predictions_are_unknown_not_false(self):
        for prediction in ('大约一半', '100厘米', '', '1/0', 'NaN', None, 0.5):
            self.assertIsNone(example.numeric_equivalence(prediction, '1/2'))

    def test_invalid_reference_is_data_error_before_prediction_parsing(self):
        for reference in ('', ' ', '一半', '1/0', 'inf', None, 0.5):
            with self.assertRaises(ValueError):
                example.numeric_equivalence(None, reference)

    def test_arithmetic_expression_is_not_evaluated(self):
        with patch('builtins.eval', side_effect=AssertionError('禁止执行表达式')) as evaluate:
            self.assertIsNone(example.numeric_equivalence('1 + 1', '2'))
            self.assertIs(example.numeric_equivalence('2/1', '2'), True)
        evaluate.assert_not_called()


class PassAtKTests(unittest.TestCase):
    def test_five_samples_two_correct_two_draws_is_seven_of_ten(self):
        self.assertAlmostEqual(example.pass_at_k(5, 2, 2), 0.7)
        self.assertNotAlmostEqual(example.pass_at_k(5, 2, 2), 0.64)
        self.assertAlmostEqual(example.pass_at_k(5, 2, 1), 0.4)
        self.assertEqual(example.pass_at_k(5, 0, 5), 0)
        self.assertEqual(example.pass_at_k(5, 2, 4), 1)
        self.assertEqual(example.pass_at_k(1, 1, 1), 1)

    def test_small_sample_pools_match_explicit_subset_enumeration(self):
        for n in range(1, 7):
            for correct in range(n + 1):
                successes = set(range(correct))
                previous = 0
                for k in range(1, n + 1):
                    subsets = list(itertools.combinations(range(n), k))
                    expected = sum(bool(successes.intersection(subset)) for subset in subsets) / len(subsets)
                    actual = example.pass_at_k(n, correct, k)
                    self.assertAlmostEqual(actual, expected, msg=repr((n, correct, k)))
                    self.assertGreaterEqual(actual + 1e-15, previous)
                    previous = actual

    def test_invalid_counts_and_nonintegers_are_rejected(self):
        for args in ((0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, 0), (5, 2, 6),
                     (5.0, 2, 1), (5, 2.0, 1), (5, 2, 1.0), (True, 0, 1)):
            with self.assertRaises(ValueError, msg=repr(args)):
                example.pass_at_k(*args)


class ExecutionSummaryTests(unittest.TestCase):
    def test_three_record_plan_and_attempted_denominators(self):
        records = [{'sample_id': 'a', 'status': 'passed'}, {'sample_id': 'b', 'status': 'timeout'},
                   {'sample_id': 'c', 'status': 'not_run'}]
        before = copy.deepcopy(records)
        self.assertEqual(example.execution_summary(records), {
            'counts': {'passed': 1, 'assertion_failed': 0, 'timeout': 1, 'runtime_error': 0, 'not_run': 1},
            'planned': 3, 'attempted': 2, 'coverage': 2 / 3,
            'success_rate': 1 / 3, 'attempted_success_rate': 0.5})
        self.assertEqual(records, before)

    def test_all_five_statuses_remain_distinct(self):
        states = ['passed'] * 2 + ['assertion_failed'] + ['timeout'] * 3 + ['runtime_error'] + ['not_run'] * 2
        records = [{'sample_id': str(i), 'status': state} for i, state in enumerate(states)]
        self.assertEqual(example.execution_summary(records), {
            'counts': {'passed': 2, 'assertion_failed': 1, 'timeout': 3, 'runtime_error': 1, 'not_run': 2},
            'planned': 9, 'attempted': 7, 'coverage': 7 / 9,
            'success_rate': 2 / 9, 'attempted_success_rate': 2 / 7})

    def test_not_run_only_is_undefined_conditionally_and_passed_singleton_is_one(self):
        result = example.execution_summary([{'sample_id': 'a', 'status': 'not_run'}])
        self.assertEqual(result['coverage'], 0)
        self.assertEqual(result['success_rate'], 0)
        self.assertIsNone(result['attempted_success_rate'])
        result = example.execution_summary([{'sample_id': 'a', 'status': 'passed'}])
        self.assertEqual([result['coverage'], result['success_rate'], result['attempted_success_rate']], [1, 1, 1])

    def test_empty_or_invalid_record_shapes_and_ids_are_rejected(self):
        for records in ([], None, {}, [None], [{'status': 'passed'}],
                         [{'sample_id': '', 'status': 'passed'}], [{'sample_id': 1, 'status': 'passed'}]):
            with self.assertRaises(ValueError):
                example.execution_summary(records)
        with self.assertRaises(ValueError):
            example.execution_summary([{'sample_id': 'same', 'status': 'passed'},
                                       {'sample_id': 'same', 'status': 'timeout'}])

    def test_undeclared_status_or_missing_status_is_rejected(self):
        for state in ('failed', 'success', '', None, [], True):
            with self.assertRaises(ValueError):
                example.execution_summary([{'sample_id': 'a', 'status': state}])
        with self.assertRaises(ValueError):
            example.execution_summary([{'sample_id': 'a'}])


class ReasoningCodeDemoTests(unittest.TestCase):
    def test_demo_calls_real_functions_without_external_execution(self):
        with patch.object(example, 'numeric_equivalence', wraps=example.numeric_equivalence) as numeric, \
             patch.object(example, 'pass_at_k', wraps=example.pass_at_k) as passk, \
             patch.object(example, 'execution_summary', wraps=example.execution_summary) as summary:
            result = example.demo()
        self.assertEqual(numeric.call_count, 2)
        passk.assert_called_once()
        summary.assert_called_once()
        self.assertIs(result['half'], True)
        self.assertIsNone(result['unparsed'])
        self.assertAlmostEqual(result['pass_at_2'], 0.7)
        self.assertEqual(result['execution']['coverage'], 2 / 3)
        self.assertEqual(result['execution']['success_rate'], 1 / 3)

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_benchmark_reasoning_code_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-reasoning-code.py')

    def test_benchmark_reasoning_code_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-reasoning-code.py')
