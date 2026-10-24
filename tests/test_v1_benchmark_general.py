"""选择题教学评分：独立数值、显式答案标记及未知状态验证。"""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / 'examples/benchmark/benchmark-general.py'
spec = importlib.util.spec_from_file_location('benchmark_general_example', path)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class ChoicePredictionTests(unittest.TestCase):
    def test_raw_and_explicit_length_normalization_select_different_choices(self):
        scores, lengths = [-2, -3], [1, 4]
        before = copy.deepcopy((scores, lengths))
        self.assertEqual(example.choice_prediction(scores, lengths), 0)
        self.assertEqual(example.choice_prediction(scores, lengths, normalize=True), 1)
        self.assertEqual((scores, lengths), before)

    def test_argmax_and_both_tie_rules_choose_first(self):
        self.assertEqual(example.choice_prediction([-5, -1, -3], [1, 1, 1]), 1)
        self.assertEqual(example.choice_prediction([-2, -2], [1, 4]), 0)
        self.assertEqual(example.choice_prediction([-2, -4], [1, 2], normalize=True), 0)
        self.assertEqual(example.choice_prediction([0], [1]), 0)

    def test_score_and_length_shapes_are_checked_even_without_normalizing(self):
        for scores, lengths in (([], []), ([-1], []), ([-1], [1, 2]), ((-1,), [1]), ([-1], (1,))):
            with self.assertRaises(ValueError):
                example.choice_prediction(scores, lengths)

    def test_nonfinite_scores_and_nonpositive_or_noninteger_lengths_are_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf'), '-1'):
            with self.assertRaises(ValueError):
                example.choice_prediction([value], [1])
        for length in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                example.choice_prediction([-1], [length])


class ChanceAdjustmentTests(unittest.TestCase):
    def test_heterogeneous_choices_average_reciprocals(self):
        result = example.chance_adjusted_accuracy(0.5, [4, 10])
        self.assertAlmostEqual(result['chance'], 0.175)
        self.assertAlmostEqual(result['adjusted'], 13 / 33)
        self.assertNotAlmostEqual(result['chance'], 1 / 7)

    def test_random_zero_adjustment_perfect_one_and_negative_below_random(self):
        self.assertAlmostEqual(example.chance_adjusted_accuracy(0.175, [4, 10])['adjusted'], 0)
        self.assertEqual(example.chance_adjusted_accuracy(1, [4, 10])['adjusted'], 1)
        self.assertAlmostEqual(example.chance_adjusted_accuracy(0, [4, 10])['adjusted'], -7 / 33)
        self.assertEqual(example.chance_adjusted_accuracy(0.5, [2]), {'chance': 0.5, 'adjusted': 0})

    def test_invalid_accuracy_and_option_counts_are_rejected(self):
        for accuracy in (-0.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                example.chance_adjusted_accuracy(accuracy, [4])
        for counts in ([], None, [1], [0], [-2], [2.0], [True]):
            with self.assertRaises(ValueError):
                example.chance_adjusted_accuracy(0.5, counts)


class ParseChoiceTests(unittest.TestCase):
    def test_declared_markers_case_parentheses_and_final_prefix(self):
        for text, index in (('Answer is A', 0), ('FINAL ANSWER: (b)', 1),
                            ('推导结束。\nFinal answer is (D).', 3), ('AnSwEr : c', 2)):
            self.assertEqual(example.parse_choice(text, 4), index, text)

    def test_option_domain_endpoints(self):
        self.assertEqual(example.parse_choice('Answer: B', 2), 1)
        self.assertEqual(example.parse_choice('Answer: Z', 26), 25)
        self.assertIsNone(example.parse_choice('Answer: C', 2))
        self.assertIsNone(example.parse_choice('Answer: Z', 4))

    def test_repeated_identical_answer_is_not_ambiguous(self):
        self.assertEqual(example.parse_choice('Answer: B. Final answer is (b).', 4), 1)

    def test_different_answers_and_mixed_valid_invalid_are_ambiguous(self):
        self.assertIsNone(example.parse_choice('Answer: A. Answer: B.', 4))
        self.assertIsNone(example.parse_choice('Answer: A. Answer: Z.', 4))

    def test_absent_markers_or_words_do_not_become_random_choices(self):
        for text in ('', 'B', 'I choose B', 'The answer could be B', 'Answer: Beta'):
            self.assertIsNone(example.parse_choice(text, 4), text)

    def test_invalid_parser_arguments_are_rejected(self):
        for count in (1, 27, 4.0, True):
            with self.assertRaises(ValueError):
                example.parse_choice('Answer: A', count)
        with self.assertRaises(ValueError):
            example.parse_choice(None, 4)


class GeneralDemoTests(unittest.TestCase):
    def test_demo_calls_all_real_functions_and_retains_ambiguous_none(self):
        with patch.object(example, 'choice_prediction', wraps=example.choice_prediction) as choice, \
             patch.object(example, 'chance_adjusted_accuracy', wraps=example.chance_adjusted_accuracy) as chance, \
             patch.object(example, 'parse_choice', wraps=example.parse_choice) as parse:
            result = example.demo()
        self.assertEqual(choice.call_count, 2)
        chance.assert_called_once()
        self.assertEqual(parse.call_count, 2)
        self.assertEqual(result['raw_prediction'], 0)
        self.assertEqual(result['normalized_prediction'], 1)
        self.assertAlmostEqual(result['chance']['chance'], 0.175)
        self.assertAlmostEqual(result['chance']['adjusted'], 13 / 33)
        self.assertEqual(result['parsed'], 1)
        self.assertIsNone(result['ambiguous'])

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_benchmark_general_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-general.py')

    def test_benchmark_general_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-general.py')
