"""网络结构小输入验证；依据四篇主题的公式、手算例子和明确前置条件。"""
import copy
import importlib.util
import math
from pathlib import Path
import socket
import unittest
from unittest.mock import patch


def load_example(name):
    path = Path(__file__).resolve().parents[1] / 'examples/network' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transformer = load_example('transformer')
heads = load_example('attention-heads')
position = load_example('position')
ffn = load_example('ffn-norm')


class NumericCase(unittest.TestCase):
    def assert_numeric(self, actual, expected, places=10):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                self.assert_numeric(actual[key], expected[key], places)
        elif isinstance(expected, (list, tuple)):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.assert_numeric(a, b, places)
        elif isinstance(expected, (int, float)):
            self.assertAlmostEqual(actual, expected, places=places)
        else:
            self.assertEqual(actual, expected)

    def finite_difference(self, function, x):
        columns = []
        for j in range(len(x)):
            plus, minus = list(x), list(x)
            plus[j] += 1e-5
            minus[j] -= 1e-5
            columns.append([(a - b) / 2e-5 for a, b in zip(function(plus), function(minus))])
        return [list(row) for row in zip(*columns)]

    def real_demo(self, module, names):
        calls = {name: 0 for name in names}
        from contextlib import ExitStack

        def observe(name):
            real = getattr(module, name)

            def invoke(*args, **kwargs):
                calls[name] += 1
                return real(*args, **kwargs)
            return invoke

        with ExitStack() as stack:
            for name in names:
                stack.enter_context(patch.object(module, name, wraps=observe(name)))
            stack.enter_context(patch.object(socket.socket, 'connect', side_effect=AssertionError('禁止联网')))
            result = module.demo()
        self.assertTrue(all(count > 0 for count in calls.values()), calls)
        return result


class TransformerTests(NumericCase):
    def test_attention_scaled_mask_before_normalization(self):
        q = [[1, 0, 0, 0]] * 3
        k = [[2, 0, 0, 0], [0, 0, 0, 0], [100, 0, 0, 0]]
        result = transformer.causal_attention(q, k, [[1, 2], [3, 4], [900, 800]])
        p = math.e / (math.e + 1)
        self.assert_numeric(result['weights'][0], [1, 0, 0])
        self.assert_numeric(result['weights'][1], [p, 1 - p, 0])
        self.assert_numeric(result['output'][1], [3 - 2 * p, 4 - 2 * p])
        for row in result['weights']:
            self.assertAlmostEqual(sum(row), 1)

    def test_future_key_and_value_changes_do_not_change_past(self):
        q, k, v = [[1], [2], [3]], [[1], [0], [2]], [[2], [4], [8]]
        original = transformer.causal_attention(q, k, v)
        changed = transformer.causal_attention(q, [[1], [0], [-1000]], [[2], [4], [-9000]])
        self.assertEqual(original['weights'][:2], changed['weights'][:2])
        self.assertEqual(original['output'][:2], changed['output'][:2])

    def test_large_equal_offset_remains_numerically_stable(self):
        result = transformer.causal_attention([[1], [1]], [[1000], [1000 + math.log(3)]], [[2], [6]])
        self.assert_numeric(result['weights'][1], [0.25, 0.75])
        self.assert_numeric(result['output'], [[2], [5]])

    def test_attention_rejects_documented_shape_and_finiteness_errors(self):
        for q, k, v in (([], [], []), ([[1]], [[1], [2]], [[1]]),
                         ([[1, 2]], [[1]], [[1]]), ([[1]], [[1]], [[float('nan')]])):
            with self.assertRaises(ValueError):
                transformer.causal_attention(q, k, v)

    def test_split_heads_preserves_token_channel_indices(self):
        rows = [[0, 1, 2, 3], [4, 5, 6, 7]]
        before = copy.deepcopy(rows)
        self.assertEqual(transformer.split_merge_heads(rows, 2), {
            'heads': [[[0, 1], [4, 5]], [[2, 3], [6, 7]]],
            'merged': rows, 'shape': [2, 2, 2],
        })
        self.assertEqual(rows, before)

    def test_single_head_and_single_channel_heads_round_trip(self):
        rows = [[1, 2, 3, 4]]
        self.assertEqual(transformer.split_merge_heads(rows, 1)['heads'], [rows])
        self.assertEqual(transformer.split_merge_heads(rows, 4)['heads'], [[[1]], [[2]], [[3]], [[4]]])

    def test_split_heads_rejects_nondivisible_or_ragged_width(self):
        for rows, count in (([[1, 2, 3]], 2), ([[1, 2], [3]], 1), ([[1]], 0)):
            with self.assertRaises(ValueError):
                transformer.split_merge_heads(rows, count)

    def test_generation_uses_new_history_and_documented_probabilities(self):
        table = [[0, math.log(3)], [math.log(4), 0]]
        result = transformer.generate_tokens(table, 0, [0.5, 0.5])
        self.assertEqual(result['tokens'], [0, 1, 0])
        self.assertEqual([x['history'] for x in result['trace']], [[0], [0, 1]])
        self.assert_numeric([x['probabilities'] for x in result['trace']], [[0.25, 0.75], [0.8, 0.2]])

    def test_temperature_changes_distribution_and_cdf_boundary(self):
        result = transformer.generate_tokens([[0, math.log(4)]] * 2, 0, [0.5], temperature=2)
        self.assert_numeric(result['trace'][0]['probabilities'], [1 / 3, 2 / 3])
        self.assertEqual(result['tokens'], [0, 1])
        self.assertEqual(transformer.generate_tokens([[0, 0]] * 2, 0, [0, 0.5])['tokens'], [0, 0, 1])

    def test_top_k_keeps_threshold_ties_and_empty_draws_keep_start(self):
        table = [[math.log(3), math.log(3), 0]] * 3
        result = transformer.generate_tokens(table, 0, [0.99], top_k=1)
        self.assertEqual(result['trace'][0]['candidates'], [0, 1])
        self.assert_numeric(result['trace'][0]['probabilities'], [0.5, 0.5])
        self.assertEqual(result['tokens'], [0, 1])
        self.assertEqual(transformer.generate_tokens(table, 2, []), {'tokens': [2], 'trace': []})

    def test_generation_rejects_explicit_temperature_draw_and_token_bounds(self):
        for kwargs in ({'temperature': 0}, {'temperature': float('inf')}, {'top_k': 0}, {'top_k': 3}):
            with self.assertRaises(ValueError):
                transformer.generate_tokens([[0, 0]] * 2, 0, [0.5], **kwargs)
        for draw in (-0.01, 1, float('nan')):
            with self.assertRaises(ValueError):
                transformer.generate_tokens([[0, 0]] * 2, 0, [draw])
        with self.assertRaises(ValueError):
            transformer.generate_tokens([[0]], 1, [0])

    def test_demo_runs_all_transformer_functions(self):
        result = self.real_demo(transformer, ('causal_attention', 'split_merge_heads', 'generate_tokens'))
        self.assertEqual(result['generation']['tokens'], [0, 1, 0])
        self.assertEqual(result['heads']['merged'], [[0, 1, 2, 3], [4, 5, 6, 7]])
        self.assert_numeric(result['attention']['weights'][0], [1, 0, 0])


class AttentionHeadsTests(NumericCase):
    def test_shared_kv_has_distinct_query_distributions(self):
        result = heads.grouped_attention([[1], [-1]], [[[1], [-1]]], [[[0], [10]]])
        p = 1 / (1 + math.exp(-2))
        self.assertEqual(result['mapping'], [0, 0])
        self.assert_numeric(result['weights'], [[p, 1 - p], [1 - p, p]])
        self.assert_numeric(result['output'], [[10 * (1 - p)], [10 * p]])

    def test_mha_and_gqa_contiguous_group_mapping(self):
        keys, values = [[[0]], [[0]]], [[[10]], [[20]]]
        grouped = heads.grouped_attention([[0]] * 4, keys, values)
        self.assertEqual(grouped['mapping'], [0, 0, 1, 1])
        self.assertEqual(grouped['output'], [[10], [10], [20], [20]])
        self.assertEqual(heads.grouped_attention([[0]] * 2, keys, values)['mapping'], [0, 1])

    def test_group_attention_scales_by_query_width(self):
        result = heads.grouped_attention([[1, 0]], [[[math.sqrt(2) * math.log(3), 0], [0, 0]]], [[[2], [6]]])
        self.assert_numeric(result['weights'], [[0.75, 0.25]])
        self.assert_numeric(result['output'], [[3]])

    def test_invalid_group_mapping_and_shapes_are_rejected(self):
        with self.assertRaises(ValueError):
            heads.grouped_attention([[1]] * 6, [[[1]]] * 4, [[[1]]] * 4)
        with self.assertRaises(ValueError):
            heads.grouped_attention([[1, 2]], [[[1]]], [[[1]]])
        with self.assertRaises(ValueError):
            heads.grouped_attention([[1]], [[]], [[]])

    def test_kv_budget_bytes_units_and_unreduced_query_work(self):
        self.assert_numeric(heads.kv_budget(2, 3, 5, 4, 2, 7, 2), {
            'kv_bytes': 1680, 'mha_bytes': 3360, 'ratio': 0.5,
            'mib': 1680 / 2**20, 'decode_score_elements': 40,
        })
        mha = heads.kv_budget(2, 3, 5, 4, 4, 7, 2)
        mqa = heads.kv_budget(2, 3, 5, 4, 1, 7, 2)
        self.assertEqual(mha['kv_bytes'], 4 * mqa['kv_bytes'])
        self.assertEqual(mha['decode_score_elements'], mqa['decode_score_elements'])

    def test_budget_rejects_nonpositive_dimensions_and_nondivisible_heads(self):
        with self.assertRaises(ValueError):
            heads.kv_budget(1, 1, 0, 4, 2, 1)
        with self.assertRaises(ValueError):
            heads.kv_budget(1, 1, 1, 6, 4, 1)

    def test_mean_pool_is_groupwise_least_squares_minimizer(self):
        vectors = [[1, 0], [-1, 0], [2, 4], [4, 2]]
        pooled = heads.mean_pool_heads(vectors, 2)
        self.assertEqual(pooled, [[0, 0], [3, 3]])
        for group, center in zip((vectors[:2], vectors[2:]), pooled):
            objective = lambda point: sum((v[j] - point[j]) ** 2 for v in group for j in range(2))
            shifted = [center[0] + 1, center[1] - 2]
            self.assertEqual(objective(shifted) - objective(center), 2 * (1 + 4))
        self.assertEqual(heads.mean_pool_heads(vectors, 4), vectors)

    def test_mean_pool_does_not_preserve_nonlinear_attention(self):
        original = heads.grouped_attention([[1], [1]], [[[math.log(3)], [0]], [[-math.log(3)], [0]]],
                                           [[[1], [0]], [[1], [0]]])
        shared = heads.mean_pool_heads([[math.log(3), 0], [-math.log(3), 0]], 1)[0]
        converted = heads.grouped_attention([[1], [1]], [[[x] for x in shared]], [[[1], [0]]])
        self.assert_numeric(original['output'][0], [0.75])
        self.assert_numeric(converted['output'][0], [0.5])

    def test_pool_rejects_unequal_shapes_or_nondivisible_grouping(self):
        for values, count in (([[1], [2], [3]], 2), ([[1, 2], [3]], 1), ([], 1)):
            with self.assertRaises(ValueError):
                heads.mean_pool_heads(values, count)

    def test_demo_covers_three_head_functions(self):
        result = self.real_demo(heads, ('grouped_attention', 'kv_budget', 'mean_pool_heads'))
        self.assertEqual(result['budget']['kv_bytes'], 134217728)
        self.assertEqual(result['budget']['mib'], 128)
        self.assertEqual(result['budget']['mha_bytes'], 512 * 2**20)
        self.assertEqual(result['pool'], [[0, 0], [3, 3]])
        self.assertNotEqual(result['grouped']['output'][0], result['grouped']['output'][1])


class PositionTests(NumericCase):
    def test_relative_rotation_has_correct_sign_and_norm(self):
        result = position.relative_rotation([1, 0], [0, 1], 0, 1, math.pi / 2)
        self.assert_numeric(result, {'both': -1, 'relative': -1, 'q_norm_squared': 1, 'rotated_norm_squared': 1})
        result = position.relative_rotation([3, 4], [2, -1], 2, 5, 0.3)
        self.assertAlmostEqual(result['both'], result['relative'])
        self.assert_numeric([result['q_norm_squared'], result['rotated_norm_squared']], [25, 25])

    def test_translation_preserves_relative_dot_not_original_dot(self):
        first = position.relative_rotation([1, 0], [1, 0], 0, 1, math.pi / 2)
        shifted = position.relative_rotation([1, 0], [1, 0], 7, 8, math.pi / 2)
        self.assertAlmostEqual(first['both'], 0)
        self.assertAlmostEqual(first['both'], shifted['both'])

    def test_four_dimensional_pairing_uses_different_frequencies(self):
        self.assert_numeric(position.rope_layout([1, 2, 3, 4], 2 * math.pi, base=16), [1, -4, 3, 2])
        self.assert_numeric(position.rope_layout([1, 2, 3, 4], 2 * math.pi, base=16, layout='interleaved'), [1, 2, -4, 3])

    def test_pairing_equivalence_requires_channel_permutation(self):
        vector = [1, 3, 2, 4]
        adjacent = position.rope_layout(vector, 1, layout='interleaved')
        split = position.rope_layout([1, 2, 3, 4], 1, layout='split')
        self.assert_numeric(split, [adjacent[0], adjacent[2], adjacent[1], adjacent[3]])
        wrong = position.rope_layout([1, 2, 3, 4], 1, layout='interleaved')
        self.assertNotAlmostEqual(split[0], wrong[0])
        self.assertEqual(position.rope_layout(vector, 0), vector)

    def test_cached_scores_use_history_positions_scale_and_translation(self):
        query, keys = [1, 0], [[1, 0], [1, 0]]
        normal = position.cached_rope_scores(query, keys, 2, [0, 1])
        self.assert_numeric(normal, [math.cos(2) / math.sqrt(2), math.cos(1) / math.sqrt(2)])
        self.assert_numeric(position.cached_rope_scores(query, keys, 7, [5, 6]), normal)
        self.assert_numeric(position.cached_rope_scores(query, keys, 2, [0, 1], scale=2),
                            [math.cos(1) / math.sqrt(2), math.cos(0.5) / math.sqrt(2)])
        reset = position.cached_rope_scores(query, keys, 0, [0, 1])
        self.assertAlmostEqual(reset[0], 1 / math.sqrt(2))
        self.assertNotAlmostEqual(reset[0], normal[0])

    def test_rotation_and_layout_reject_explicit_dimension_and_finite_bounds(self):
        with self.assertRaises(ValueError):
            position.relative_rotation([1], [1, 0], 0, 1, 1)
        with self.assertRaises(ValueError):
            position.relative_rotation([1, 0], [1, 0], 0, 1, float('nan'))
        for vector, kwargs in (([1, 2, 3], {}), ([1, 2], {'layout': 'unknown'}), ([1, 2], {'base': 0})):
            with self.assertRaises(ValueError):
                position.rope_layout(vector, 1, **kwargs)

    def test_cached_scores_reject_missing_positions_and_nonpositive_scale(self):
        with self.assertRaises(ValueError):
            position.cached_rope_scores([1, 0], [[1, 0]], 2, [])
        with self.assertRaises(ValueError):
            position.cached_rope_scores([1, 0], [[1, 0]], 2, [0], scale=0)

    def test_demo_runs_all_rope_functions(self):
        result = self.real_demo(position, ('relative_rotation', 'rope_layout', 'cached_rope_scores'))
        self.assertAlmostEqual(result['identity']['both'], 0)
        self.assert_numeric(result['continued'], [math.cos(2) / math.sqrt(2), math.cos(1) / math.sqrt(2)])
        self.assertNotAlmostEqual(result['continued'][0], result['reset'][0])
        self.assert_numeric(result['layout'], [math.cos(1) - 3 * math.sin(1),
                            2 * math.cos(0.01) - 4 * math.sin(0.01),
                            math.sin(1) + 3 * math.cos(1), 2 * math.sin(0.01) + 4 * math.cos(0.01)])


class FfnNormTests(NumericCase):
    def test_swiglu_independent_branches_and_output_projection(self):
        a = math.log(3)
        result = ffn.swiglu([1, 2], [[0, 0], [a, 0], [-a, 0]],
                            [[2, 0], [0, 1], [1, 1]], [[1, 2, 0], [0, -1, 3]])
        self.assert_numeric(result, {'gate': [0, a, -a], 'up': [2, 2, 3],
                            'hidden': [0, 1.5 * a, -0.75 * a], 'output': [3 * a, -3.75 * a],
                            'parameters': 18, 'hidden_elements': 3})

    def test_swiglu_equal_budget_and_stable_negative_gate(self):
        identity = [[1, 0], [0, 1]]
        result = ffn.swiglu([1000, -1000], identity, identity, identity)
        self.assertEqual(result['parameters'], 2 * 2 * 3)  # d=2,m0=3，门控m=2。
        self.assert_numeric(result['output'], [1000000, 0])

    def test_swiglu_rejects_projection_dimension_mismatch(self):
        with self.assertRaises(ValueError):
            ffn.swiglu([1, 2], [[1]], [[1, 2]], [[1], [1]])
        with self.assertRaises(ValueError):
            ffn.swiglu([1, 2], [[1, 2]], [[1, 2]], [[1]])

    def test_norm_statistics_and_exact_zero_epsilon_jacobian(self):
        root = math.sqrt(5)
        self.assert_numeric(ffn.norm_statistics([1, 3], eps=0), {
            'mean': 2, 'square_mean': 5, 'variance': 1,
            'rmsnorm': [1 / root, 3 / root], 'layernorm': [-1, 1],
            'jacobian': [[9 / (10 * root), -3 / (10 * root)], [-3 / (10 * root), 1 / (10 * root)]],
        })

    def test_layernorm_translation_and_rms_scale_sign(self):
        base = ffn.norm_statistics([1, 3], eps=0)
        shifted = ffn.norm_statistics([3, 5], eps=0)
        self.assert_numeric(base['layernorm'], shifted['layernorm'])
        self.assertNotAlmostEqual(base['rmsnorm'][0], shifted['rmsnorm'][0])
        self.assert_numeric(ffn.norm_statistics([2, 6], eps=0)['rmsnorm'], base['rmsnorm'])
        self.assert_numeric(ffn.norm_statistics([-2, -6], eps=0)['rmsnorm'], [-x for x in base['rmsnorm']])

    def test_positive_epsilon_radial_jacobian_and_finite_difference(self):
        x, eps = [1.0, 3.0], 2.0
        result = ffn.norm_statistics(x, eps)
        radial = [sum(row[j] * x[j] for j in range(2)) for row in result['jacobian']]
        self.assert_numeric(radial, [2 / (7 ** 1.5), 6 / (7 ** 1.5)])
        numerical = self.finite_difference(lambda y: ffn.norm_statistics(y, eps)['rmsnorm'], x)
        self.assert_numeric(result['jacobian'], numerical, places=8)

    def test_zero_input_and_explicit_zero_denominator_boundaries(self):
        result = ffn.norm_statistics([0, 0], eps=4)
        self.assert_numeric(result['rmsnorm'], [0, 0])
        self.assert_numeric(result['layernorm'], [0, 0])
        self.assert_numeric(result['jacobian'], [[0.5, 0], [0, 0.5]])
        for x, eps in (([0, 0], 0), ([2, 2], 0), ([1, 3], -1)):
            with self.assertRaises(ValueError):
                ffn.norm_statistics(x, eps)

    def test_zero_sublayer_preserves_pre_norm_identity(self):
        result = ffn.residual_paths([1, 3], [[0, 0], [0, 0]], eps=0)
        root = math.sqrt(5)
        self.assert_numeric(result['pre'], [1, 3])
        self.assert_numeric(result['pre_jacobian'], [[1, 0], [0, 1]])
        self.assert_numeric(result['post'], [1 / root, 3 / root])
        self.assert_numeric(result['post_jacobian'], [[9 / (10 * root), -3 / (10 * root)],
                                                      [-3 / (10 * root), 1 / (10 * root)]])

    def test_noncommuting_residual_jacobians_match_finite_differences(self):
        x, matrix, eps = [1.0, 3.0], [[2, 1], [-0.5, 1]], 0.25
        result = ffn.residual_paths(x, matrix, eps)
        scale = math.sqrt(5.25)
        self.assert_numeric(result['pre'], [1 + 5 / scale, 3 + 2.5 / scale])
        post_scale = math.sqrt((6**2 + 5.5**2) / 2 + eps)
        self.assert_numeric(result['post'], [6 / post_scale, 5.5 / post_scale])
        for output, jacobian in (('pre', 'pre_jacobian'), ('post', 'post_jacobian')):
            numerical = self.finite_difference(lambda y: ffn.residual_paths(y, matrix, eps)[output], x)
            self.assert_numeric(result[jacobian], numerical, places=8)

    def test_residual_rejects_nonsquare_sublayer(self):
        with self.assertRaises(ValueError):
            ffn.residual_paths([1, 3], [[1, 0]])

    def test_demo_runs_all_ffn_and_norm_functions(self):
        result = self.real_demo(ffn, ('swiglu', 'norm_statistics', 'residual_paths'))
        self.assert_numeric(result['swiglu']['output'], [1 / (1 + math.exp(-1)), 1 / (1 + math.e)])
        self.assertEqual(result['norm']['square_mean'], 5)
        self.assertEqual(result['residual']['pre'], [1, 3])
        self.assert_numeric(result['residual']['pre_jacobian'], [[1, 0], [0, 1]])

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_transformer_cli(self):
        assert_cli_matches_demo(self, 'examples/network/transformer.py')

    def test_transformer_quiet_import(self):
        assert_quiet_import(self, 'examples/network/transformer.py')

    def test_attention_heads_cli(self):
        assert_cli_matches_demo(self, 'examples/network/attention-heads.py')

    def test_attention_heads_quiet_import(self):
        assert_quiet_import(self, 'examples/network/attention-heads.py')

    def test_position_cli(self):
        assert_cli_matches_demo(self, 'examples/network/position.py')

    def test_position_quiet_import(self):
        assert_quiet_import(self, 'examples/network/position.py')

    def test_ffn_norm_cli(self):
        assert_cli_matches_demo(self, 'examples/network/ffn-norm.py')

    def test_ffn_norm_quiet_import(self):
        assert_quiet_import(self, 'examples/network/ffn-norm.py')
