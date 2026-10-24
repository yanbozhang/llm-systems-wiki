"""训练教学局部公式验证；不训练模型，不运行第三方框架。"""
import copy
import importlib.util
import math
from pathlib import Path
import unittest


def load_example(name):
    p = Path(__file__).resolve().parents[1] / 'examples/training' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pre = load_example('pretraining')
sft = load_example('sft')
dpo = load_example('preference')
grpo = load_example('policy-optimization')


class TrainingCase(unittest.TestCase):
    def assert_values(self, actual, expected):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for k in expected:
                self.assert_values(actual[k], expected[k])
        elif isinstance(expected, (list, tuple)):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.assert_values(a, b)
        elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
            self.assertAlmostEqual(actual, expected, places=8)
        else:
            self.assertEqual(actual, expected)


class PretrainingTests(TrainingCase):
    def test_shift_once_and_target_position_mask_not_token_identity(self):
        self.assertEqual(pre.shift_targets([10, 0, 12, 0], [False, True, True, False]),
                         {'input_ids': [10, 0, 12], 'labels': [0, 12, -100]})
        self.assertEqual(pre.shift_targets([1, 2], [True, False], ignore_index=-1),
                         {'input_ids': [1], 'labels': [-1]})
        self.assertEqual(pre.shift_targets([1, 2, 3])['labels'], [2, 3])

    def test_shift_rejects_missing_pair_or_misaligned_mask(self):
        with self.assertRaises(ValueError):
            pre.shift_targets([1])
        with self.assertRaises(ValueError):
            pre.shift_targets([1, 2], [True])

    def test_token_loss_hand_computed_probabilities_and_ignored_gradient(self):
        rows = [[math.log(p), math.log(1 - p)] for p in (0.5, 0.25, 0.125)]
        result = pre.token_loss(rows, [0, 0, 0])
        self.assert_values([result['loss_sum'], result['mean_loss'], result['perplexity']],
                           [math.log(64), math.log(4), 4])
        masked = pre.token_loss(rows, [0, 0, -100])
        self.assertEqual(masked['valid_tokens'], 2)
        self.assert_values(masked['gradients'], [[-0.25, 0.25], [-0.375, 0.375], [0, 0]])
        self.assert_values(masked['token_losses'], [math.log(2), math.log(4), 0])
        self.assertAlmostEqual(masked['perplexity'], math.sqrt(8))
        for row in masked['gradients']:
            self.assertAlmostEqual(sum(row), 0)

    def test_token_weighting_is_not_mean_of_microbatch_means(self):
        probabilities = [math.exp(-1)] + [math.exp(-3)] * 3
        rows = [[math.log(p), math.log(1 - p)] for p in probabilities]
        result = pre.token_loss(rows, [0] * 4)
        self.assertAlmostEqual(result['mean_loss'], 2.5)
        self.assertNotAlmostEqual(result['mean_loss'], 2.0)
        stable = pre.token_loss([[1000, 1000 + math.log(3)]], [0])
        self.assertAlmostEqual(stable['mean_loss'], math.log(4))

    def test_ce_gradients_match_independent_finite_difference(self):
        rows, targets = [[0.2, -0.3], [1.0, 0.4]], [1, 0]
        result = pre.token_loss(rows, targets)
        for i in range(2):
            for j in range(2):
                plus, minus = copy.deepcopy(rows), copy.deepcopy(rows)
                plus[i][j] += 1e-5
                minus[i][j] -= 1e-5
                derivative = (pre.token_loss(plus, targets)['mean_loss'] - pre.token_loss(minus, targets)['mean_loss']) / 2e-5
                self.assertAlmostEqual(derivative, result['gradients'][i][j], places=8)

    def test_loss_rejects_all_ignore_bad_target_and_nonfinite_logits(self):
        for rows, labels in (([[0, 1]], [-100]), ([[0, 1]], [2]), ([[0, float('nan')]], [0]),
                             ([[0, 1], [0]], [0, 0])):
            with self.assertRaises(ValueError):
                pre.token_loss(rows, labels)

    def test_split_audit_reports_exact_and_threshold_candidates_once_per_document(self):
        result = pre.audit_split(['a b c d', 'a b c d'], ['A B C D', 'a b c x', 'other words'], threshold=0.5)
        self.assertEqual(result['flagged_validation'], 2)
        self.assertEqual(result['flagged_fraction'], 2 / 3)
        self.assertEqual(result['pairs'], [
            {'train': 0, 'validation': 0, 'jaccard': 1, 'exact': True},
            {'train': 0, 'validation': 1, 'jaccard': 0.5, 'exact': False},
            {'train': 1, 'validation': 0, 'jaccard': 1, 'exact': True},
            {'train': 1, 'validation': 1, 'jaccard': 0.5, 'exact': False}])
        self.assertEqual(pre.audit_split(['a b'], [])['flagged_fraction'], 0)
        with self.assertRaises(ValueError):
            pre.audit_split([''], ['a'])

    def test_demo_all_pretraining_outputs(self):
        result = pre.demo()
        self.assertEqual(result['shift']['labels'], [11, 12, -100])
        self.assertAlmostEqual(result['loss']['perplexity'], 4)
        self.assertEqual(result['data']['flagged_validation'], 2)


class SftLoraTests(TrainingCase):
    def test_sft_masks_intersect_without_early_shift(self):
        result = sft.build_sft_labels([10, 20, 30, 0, 0], [1, 0, 1, 1, 1],
                                     completion_mask=[0, 1, 0, 1, 1], attention_mask=[1, 1, 1, 1, 0])
        self.assertEqual(result, {'labels': [-100, -100, -100, 0, -100],
                                  'target_positions': [3], 'prediction_pairs': [(2, 0)]})
        self.assertEqual(sft.build_sft_labels([1], [1]), {'labels': [1], 'target_positions': [], 'prediction_pairs': []})
        self.assertEqual(sft.build_sft_labels([1, 2], [0, 0])['target_positions'], [])

    def test_invalid_sft_masks_are_rejected(self):
        for mask in ([1], [1, 2]):
            with self.assertRaises(ValueError):
                sft.build_sft_labels([1, 2], mask)

    def test_zero_b_and_double_zero_initial_gradients(self):
        result = sft.lora_gradients([1, 2], [[1, -1]], [[0], [0]], [1, -1], alpha=2)
        self.assert_values(result, {'grad_a': [[0, 0]], 'grad_b': [[-2], [2]],
                                    'delta_output': [0, 0], 'trainable_parameters': 4, 'scale': 2})
        both = sft.lora_gradients([1, 2], [[0, 0]], [[0], [0]], [1, -1], alpha=2)
        self.assert_values(both['grad_a'], [[0, 0]])
        self.assert_values(both['grad_b'], [[0], [0]])

    def test_rank_two_gradients_and_alpha_over_rank_scaling(self):
        args = ([1, 2], [[1, 2], [-1, 1]], [[2, -1], [1, 3]], [2, -1])
        before = copy.deepcopy(args)
        self.assert_values(sft.lora_gradients(*args, alpha=4), {
            'grad_a': [[6, 12], [-10, -20]], 'grad_b': [[20, 4], [-10, -2]],
            'delta_output': [18, 16], 'trainable_parameters': 8, 'scale': 2})
        self.assertEqual(args, before)

    def test_merge_explicit_noncommuting_matrices_and_pure_inputs(self):
        args = ([[1, 0], [0, 1]], [[1, 2], [-1, 1]], [[2, -1], [1, 3]], [1, 2])
        before = copy.deepcopy(args)
        self.assert_values(sft.lora_merge_equivalence(*args, alpha=4), {
            'delta_weight': [[6, 6], [-4, 10]], 'merged_weight': [[7, 6], [-4, 11]],
            'separate': [19, 18], 'combined': [19, 18], 'max_error': 0})
        self.assertEqual(args, before)

    def test_lora_dimension_errors_are_explicit(self):
        with self.assertRaises(ValueError):
            sft.lora_gradients([1, 2], [[1]], [[1]], [1])
        with self.assertRaises(ValueError):
            sft.lora_gradients([1], [[1]], [[1]], [1, 2])
        with self.assertRaises(ValueError):
            sft.lora_merge_equivalence([[1, 2]], [[1]], [[1]], [1])

    def test_demo_all_sft_lora_outputs(self):
        result = sft.demo()
        self.assertEqual(result['labels']['prediction_pairs'], [(1, 30), (2, 31)])
        self.assert_values(result['gradients']['grad_b'], [[-2], [2]])
        self.assert_values(result['merge']['combined'], [0, 3])


class PreferenceTests(TrainingCase):
    def test_optimal_policy_partition_and_reward_offset_invariance(self):
        result = dpo.optimal_policy([0.5, 0.5], [math.log(3), 0])
        self.assert_values(result, {'policy': [0.75, 0.25], 'log_partition': math.log(2)})
        shifted = dpo.optimal_policy([0.5, 0.5], [7 + math.log(3), 7])
        self.assert_values(shifted['policy'], result['policy'])
        self.assertAlmostEqual(shifted['log_partition'] - result['log_partition'], 7)
        self.assert_values(dpo.optimal_policy([0.25, 0.75], [0, 0])['policy'], [0.25, 0.75])

    def test_optimal_policy_requires_positive_reference_and_beta(self):
        for reference, rewards, beta in (([0, 1], [0, 0], 1), ([0.2, 0.2], [0, 0], 1),
                                          ([0.5, 0.5], [0, 0], 0), ([1], [float('inf')], 1)):
            with self.assertRaises(ValueError):
                dpo.optimal_policy(reference, rewards, beta)

    def test_dpo_zero_and_log_three_margins_have_exact_loss_and_gradient(self):
        self.assert_values(dpo.dpo_loss(-2, -3, -2, -3), {
            'relative_delta': 0, 'margin': 0, 'loss': math.log(2),
            'grad_chosen_logp': -0.05, 'grad_rejected_logp': 0.05})
        result = dpo.dpo_loss(math.log(0.75), math.log(0.25), math.log(0.5), math.log(0.5), beta=1)
        self.assert_values([result['margin'], result['loss'], result['grad_chosen_logp'], result['grad_rejected_logp']],
                           [math.log(3), math.log(4 / 3), -0.25, 0.25])

    def test_dpo_relative_improvement_can_lower_chosen_probability(self):
        baseline = dpo.dpo_loss(-2, -3, -2, -3)
        updated = dpo.dpo_loss(-2.1, -3.5, -2, -3)
        self.assertAlmostEqual(updated['relative_delta'], 0.4)
        self.assertLess(updated['loss'], baseline['loss'])

    def test_dpo_stable_extreme_margins_and_frozen_reference_derivatives(self):
        self.assertAlmostEqual(dpo.dpo_loss(-1, -1001, -1, -1, beta=1)['loss'], 0)
        self.assertAlmostEqual(dpo.dpo_loss(-1001, -1, -1, -1, beta=1)['loss'], 1000)
        args = [-1.2, -2.0, -1.0, -1.5]
        result = dpo.dpo_loss(*args, beta=0.3)
        for index, field in ((0, 'grad_chosen_logp'), (1, 'grad_rejected_logp')):
            plus, minus = list(args), list(args)
            plus[index] += 1e-5
            minus[index] -= 1e-5
            derivative = (dpo.dpo_loss(*plus, beta=0.3)['loss'] - dpo.dpo_loss(*minus, beta=0.3)['loss']) / 2e-5
            self.assertAlmostEqual(result[field], derivative, places=8)

    def test_completion_mask_and_sum_versus_length_average(self):
        chosen = dpo.completion_logratio([-30, -1, -1], [-1, -1.3, -1.3], [0, 1, 1])
        rejected = dpo.completion_logratio([-1], [-1.5], [1])
        self.assert_values(chosen, {'sum': 0.6, 'mean': 0.3, 'tokens': 2, 'per_token': [0.3, 0.3]})
        self.assertAlmostEqual(chosen['sum'] - rejected['sum'], 0.1)
        self.assertAlmostEqual(chosen['mean'] - rejected['mean'], -0.2)

    def test_completion_rejects_empty_mask_or_nonfinite_logp(self):
        for args in (([-1], [-1], [0]), ([-1], [-1, -2], [1]), ([-1], [-1], [2]), ([-1], [float('nan')], [1])):
            with self.assertRaises(ValueError):
                dpo.completion_logratio(*args)

    def test_demo_all_preference_outputs(self):
        result = dpo.demo()
        self.assert_values(result['optimal']['policy'], [0.75, 0.25])
        self.assertAlmostEqual(result['loss']['loss'], math.log(2))
        self.assertAlmostEqual(result['chosen']['sum'] - result['rejected']['sum'], 0.1)


class PolicyOptimizationTests(TrainingCase):
    def test_advantages_explicit_ddof_and_missing_not_zero_reward(self):
        self.assert_values(grpo.group_advantages([0, None, 2], ddof=0, eps=1), {
            'mean': 1, 'std': 1, 'advantages': [-0.5, 0, 0.5], 'valid_count': 2})
        sample = grpo.group_advantages([0, 0, 1, 1], ddof=1)
        population = grpo.group_advantages([0, 0, 1, 1], ddof=0)
        self.assertAlmostEqual(sample['std'], math.sqrt(1 / 3))
        self.assertAlmostEqual(population['std'], 0.5)
        self.assertAlmostEqual(sample['advantages'][0], -0.5 / (math.sqrt(1 / 3) + 1e-4))

    def test_equal_singleton_and_missing_groups_have_zero_signal(self):
        for rewards in ([2, 2], [None, 5], [None, None]):
            result = grpo.group_advantages(rewards)
            self.assertEqual(result['advantages'], [0, 0])
        self.assertIsNone(grpo.group_advantages([None, None])['mean'])
        with self.assertRaises(ValueError):
            grpo.group_advantages([1, float('nan')])

    def test_four_clipping_regions_and_frozen_old_at_ratio_one(self):
        for ratio, advantage, objective, gradient, saturated in (
            (1.5, 1, 1.2, 0, True), (1.5, -1, -1.5, 1.5, False),
            (0.5, 1, 0.5, -0.5, False), (0.5, -1, -0.8, 0, True), (1, 2, 2, -2, False)):
            result = grpo.clipped_surrogate(math.log(ratio) - 1, -1, advantage)
            self.assert_values(result, {'ratio': ratio, 'objective': objective, 'loss': -objective,
                                        'grad_new_logp': gradient, 'saturated': saturated})

    def test_clipped_derivative_matches_nonboundary_finite_difference(self):
        for ratio, advantage in ((1.5, 1), (1.5, -1), (0.5, 1), (0.5, -1)):
            lp = math.log(ratio) - 1
            derivative = (grpo.clipped_surrogate(lp + 1e-5, -1, advantage)['loss'] -
                          grpo.clipped_surrogate(lp - 1e-5, -1, advantage)['loss']) / 2e-5
            self.assertAlmostEqual(derivative, grpo.clipped_surrogate(lp, -1, advantage)['grad_new_logp'], places=8)

    def test_three_reductions_keep_unequal_length_weights_and_masks(self):
        rows = [[-1, -1], [-1, -1, -1]]
        result = grpo.grpo_loss_terms(rows, rows, rows, [1, 3], [[1, 0], [1, 1, 1]], max_completion_length=3)
        self.assert_values(result, {'token_losses': [[-1, 0], [-3, -3, -3]],
            'sampled_kl': [[0, 0], [0, 0, 0]], 'lengths': [1, 3],
            'sequence_mean': -2, 'token_mean': -2.5, 'constant_mean': -5 / 3})

    def test_sampled_kl_weighted_by_current_policy_matches_finite_space_kl(self):
        current = [[math.log(0.6)], [math.log(0.4)]]
        reference = [[math.log(0.5)], [math.log(0.5)]]
        result = grpo.grpo_loss_terms(current, current, reference, [0, 0], [[1], [1]], beta=1)
        first, second = result['sampled_kl'][0][0], result['sampled_kl'][1][0]
        self.assertAlmostEqual(first, 5 / 6 - 1 + math.log(1.2))
        self.assertAlmostEqual(second, 1.25 - 1 + math.log(0.8))
        self.assertGreaterEqual(min(first, second), 0)
        self.assertAlmostEqual(0.6 * first + 0.4 * second, 0.6 * math.log(1.2) + 0.4 * math.log(0.8))

    def test_grpo_explicit_invalid_domains_are_rejected(self):
        with self.assertRaises(ValueError):
            grpo.clipped_surrogate(-1, -1, 1, epsilon=1)
        with self.assertRaises(ValueError):
            grpo.grpo_loss_terms([[-1]], [[-1]], [[-1]], [1], [[0]])
        with self.assertRaises(ValueError):
            grpo.grpo_loss_terms([[-1, -1]], [[-1, -1]], [[-1, -1]], [1], [[1, 1]], max_completion_length=1)

    def test_demo_all_grpo_outputs(self):
        result = grpo.demo()
        self.assertAlmostEqual(result['advantages']['mean'], 0.5)
        self.assertTrue(result['positive_clip']['saturated'])
        self.assertFalse(result['negative_unclipped']['saturated'])
        self.assert_values([result['reductions']['sequence_mean'], result['reductions']['token_mean'],
                            result['reductions']['constant_mean']], [-2, -2.5, -5 / 3])

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_pretraining_cli(self):
        assert_cli_matches_demo(self, 'examples/training/pretraining.py')

    def test_pretraining_quiet_import(self):
        assert_quiet_import(self, 'examples/training/pretraining.py')

    def test_sft_cli(self):
        assert_cli_matches_demo(self, 'examples/training/sft.py')

    def test_sft_quiet_import(self):
        assert_quiet_import(self, 'examples/training/sft.py')

    def test_preference_cli(self):
        assert_cli_matches_demo(self, 'examples/training/preference.py')

    def test_preference_quiet_import(self):
        assert_quiet_import(self, 'examples/training/preference.py')

    def test_policy_optimization_cli(self):
        assert_cli_matches_demo(self, 'examples/training/policy-optimization.py')

    def test_policy_optimization_quiet_import(self):
        assert_quiet_import(self, 'examples/training/policy-optimization.py')
