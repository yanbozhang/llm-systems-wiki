"""执行七篇前沿文档中明确授权的14个自编教学块，不导入任何来源缓存或快照。"""
import ast
import copy
from contextlib import redirect_stdout
from functools import lru_cache
import io
import math
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = {
    '模型网络': ('expert_macs', 'proxy_blocks'),
    '训练': ('tilted_success_probability', 'illustrative_token_advantage'),
    '推理': ('logdet_capacity_2d', 'shared_draft_cache_scalars'),
    'Harness': ('merge_research_state', 'illustrative_memory_quality'),
    '知识库': ('mask_reviewed_spans', 'reasoning_intensity_weights'),
    '业务Agent': ('stage_memory', 'masked_step_loss'),
    'Benchmark': ('paired_bootstrap_interval', 'matched_coverage'),
}


@lru_cache(maxsize=None)
def example(name):
    for module, expected in EXAMPLES.items():
        if name not in expected:
            continue
        path = ROOT / 'wiki/frontiers' / (module + '研究进展.md')
        text = path.read_text(encoding='utf-8')
        blocks = list(re.finditer(r'^```python\s*\n(.*?)^```\s*$', text, re.M | re.S))
        if len(blocks) != 2:
            raise AssertionError(f'{path.name} 应恰有两个已授权Python教学块')
        for match in blocks:
            code = match.group(1)
            tree = ast.parse(code)
            functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
            if functions != [name]:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    raise AssertionError('教学块出现未约定的导入')
                if isinstance(node, ast.ImportFrom) and node.module not in {'math', 'random'}:
                    raise AssertionError('教学块导入必须来自已审阅的标准库math/random')
            namespace = {'__name__': 'frontier_teaching_example'}
            stdout = io.StringIO()
            ast.increment_lineno(tree, text.count('\n', 0, match.start(1)))
            with redirect_stdout(stdout):
                exec(compile(tree, str(path), 'exec'), namespace)
            return namespace[name], stdout.getvalue()
    raise AssertionError('未找到已授权的教学函数：' + name)


class NetworkExamples(unittest.TestCase):
    def test_expert_macs_matches_two_hand_calculated_width_budgets(self):
        function, output = example('expert_macs')
        self.assertEqual(function(4, [.5, 1]), 192)
        self.assertEqual(function(4, [1, 1]), 256)
        self.assertEqual(output.splitlines(), ['192', '256'])

    def test_expert_macs_rejects_nonpositive_dimension(self):
        function, _ = example('expert_macs')
        with self.assertRaises(ValueError):
            function(0, [1])

    def test_expert_macs_rejects_width_outside_declared_interval(self):
        function, _ = example('expert_macs')
        for width in (0, 1.1):
            with self.assertRaises(ValueError):
                function(4, [width])

    def test_proxy_blocks_selects_second_block(self):
        function, output = example('proxy_blocks')
        self.assertEqual(function([1, 0], [[1, 0], [0, 1], [-1, 0], [2, 0]], 2, 2, 1), [1])
        self.assertEqual(output.strip(), '[1]')

    def test_proxy_blocks_rejects_mismatched_vectors(self):
        function, _ = example('proxy_blocks')
        with self.assertRaises(ValueError):
            function([1, 0], [[1]], 2, 2, 1)

    def test_proxy_blocks_rejects_declared_invalid_budget_parameters(self):
        function, _ = example('proxy_blocks')
        for query, dimension, block_size, keep in (([], 2, 2, 1), ([1], -1, 2, 1), ([1], 2, 0, 1), ([1], 2, 2, -1)):
            with self.assertRaises(ValueError):
                function(query, [], dimension, block_size, keep)


class TrainingExamples(unittest.TestCase):
    def test_tilted_probability_matches_hand_calculation_and_zero_support(self):
        function, output = example('tilted_success_probability')
        self.assertAlmostEqual(function(.2, math.log(4)), .5)
        self.assertEqual(function(0, math.log(4)), 0)
        self.assertAlmostEqual(float(output.strip()), .5)

    def test_tilted_probability_rejects_invalid_probability(self):
        function, _ = example('tilted_success_probability')
        for probability in (-.1, 1.1):
            with self.assertRaises(ValueError):
                function(probability, 0)

    def test_token_advantage_matches_positive_negative_and_zero_formula(self):
        function, output = example('illustrative_token_advantage')
        self.assertAlmostEqual(function(1, .2), .8)
        self.assertAlmostEqual(function(-1, .8), -.8)
        self.assertEqual(function(0, .5), 0)
        self.assertEqual([float(line) for line in output.splitlines()], [.8, -.8])

    def test_token_advantage_rejects_invalid_token_probability(self):
        function, _ = example('illustrative_token_advantage')
        for probability in (-.1, 1.1):
            with self.assertRaises(ValueError):
                function(1, probability)


class InferenceExamples(unittest.TestCase):
    def test_logdet_distinguishes_duplicate_and_orthogonal_directions(self):
        function, output = example('logdet_capacity_2d')
        self.assertAlmostEqual(function([(1, 0), (1, 0)]), math.log(3))
        self.assertAlmostEqual(function([(1, 0), (0, 1)]), math.log(4))
        values = [float(line) for line in output.splitlines()]
        self.assertAlmostEqual(values[0], math.log(3))
        self.assertAlmostEqual(values[1], math.log(4))

    def test_shared_draft_budget_matches_420_scalar_example(self):
        function, output = example('shared_draft_cache_scalars')
        self.assertEqual(function(100, 10, 4, 2), 420)
        self.assertEqual(output.splitlines(), ['420', '600'])

    def test_shared_draft_budget_rejects_negative_parameters(self):
        function, _ = example('shared_draft_cache_scalars')
        for index in range(4):
            values = [100, 10, 4, 2]
            values[index] = -1
            with self.assertRaises(ValueError):
                function(*values)


class HarnessExamples(unittest.TestCase):
    def test_research_state_deduplicates_verified_without_mutating_inputs(self):
        function, output = example('merge_research_state')
        previous = {'verified': ['已确认论文版本']}
        verified = ['已确认论文版本', '已找到源码入口']
        unresolved = ['尚未核对实验硬件']
        failed = ['旧下载链接已失效']
        before = copy.deepcopy((previous, verified, unresolved, failed))
        result = function(previous, verified, unresolved, failed)
        self.assertEqual(result['verified'], ['已确认论文版本', '已找到源码入口'])
        self.assertEqual(len(result['verified']), 2)
        self.assertEqual((previous, verified, unresolved, failed), before)
        self.assertEqual(output.strip(), '2')

    def test_smoothed_memory_quality_matches_no_evidence_and_three_of_four(self):
        function, output = example('illustrative_memory_quality')
        self.assertEqual(function(0, 0), .5)
        self.assertAlmostEqual(function(3, 4), 2 / 3)
        values = [float(line) for line in output.splitlines()]
        self.assertEqual(values[0], .5)
        self.assertAlmostEqual(values[1], 2 / 3)

    def test_memory_quality_rejects_impossible_feedback_counts(self):
        function, _ = example('illustrative_memory_quality')
        for helpful, evaluated in ((-1, 2), (3, 2)):
            with self.assertRaises(ValueError):
                function(helpful, evaluated)


class KnowledgeExamples(unittest.TestCase):
    def test_mask_only_replaces_reviewed_position_and_preserves_background(self):
        function, output = example('mask_reviewed_spans')
        tokens = ['项目', '发布于', '错误年份', '，作者为A']
        self.assertEqual(function(tokens, [2]), ['项目', '发布于', '[MASK]', '，作者为A'])
        self.assertEqual(tokens, ['项目', '发布于', '错误年份', '，作者为A'])
        self.assertEqual(ast.literal_eval(output.strip()), ['项目', '发布于', '[MASK]', '，作者为A'])

    def test_mask_rejects_out_of_range_positions(self):
        function, _ = example('mask_reviewed_spans')
        for position in (-1, 2):
            with self.assertRaises(ValueError):
                function(['背景', '答案'], [position])

    def test_reasoning_intensity_matches_capped_normalized_weights(self):
        function, output = example('reasoning_intensity_weights')
        self.assertEqual(function([2, 4], [1, 1], 3), [.4, .6])
        self.assertEqual(ast.literal_eval(output.strip()), [.4, .6])

    def test_reasoning_intensity_rejects_zero_denominator(self):
        function, _ = example('reasoning_intensity_weights')
        with self.assertRaises(ValueError):
            function([2], [0], 3)

    def test_reasoning_intensity_rejects_empty_or_mismatched_batch(self):
        function, _ = example('reasoning_intensity_weights')
        for original, rewritten in (([], []), ([1, 2], [1])):
            with self.assertRaises(ValueError):
                function(original, rewritten, 3)

    def test_reasoning_intensity_rejects_invalid_cap_or_negative_loss(self):
        function, _ = example('reasoning_intensity_weights')
        with self.assertRaises(ValueError):
            function([1], [1], 0)
        with self.assertRaises(ValueError):
            function([-1], [1], 3)

    def test_reasoning_intensity_rejects_zero_total_intensity(self):
        function, _ = example('reasoning_intensity_weights')
        with self.assertRaises(ValueError):
            function([0, 0], [1, 1], 3)


class AgentExamples(unittest.TestCase):
    def test_stage_memory_filters_stage_before_similarity_and_returns_none_without_candidate(self):
        function, output = example('stage_memory')
        memories = [{'id': 'edit-1', 'stage': 'edit', 'words': ['cache', 'bug']},
                    {'id': 'verify-1', 'stage': 'verify', 'words': ['cache', 'regression']}]
        self.assertEqual(function(memories, 'verify', ['cache', 'bug'])['id'], 'verify-1')
        self.assertIsNone(function(memories, 'deploy', ['cache', 'bug']))
        self.assertEqual(output.strip(), 'verify-1')

    def test_masked_loss_matches_log_two_and_returns_none_when_all_filtered(self):
        function, output = example('masked_step_loss')
        self.assertAlmostEqual(function([.5, .01, .5], [1, 0, 1]), math.log(2))
        self.assertIsNone(function([.5, .01, .5], [0, 0, 0]))
        self.assertAlmostEqual(float(output.strip()), math.log(2))

    def test_masked_loss_rejects_mismatched_length_and_nonbinary_mask(self):
        function, _ = example('masked_step_loss')
        with self.assertRaises(ValueError):
            function([.5], [1, 0])
        with self.assertRaises(ValueError):
            function([.5], [2])

    def test_masked_loss_rejects_probability_outside_declared_interval(self):
        function, _ = example('masked_step_loss')
        for probability in (0, 1.1):
            with self.assertRaises(ValueError):
                function([probability], [1])


class BenchmarkExamples(unittest.TestCase):
    def test_paired_bootstrap_identical_scores_have_zero_interval(self):
        function, output = example('paired_bootstrap_interval')
        self.assertEqual(function([1, 0, 1, 0], [1, 0, 1, 0]), (0, 0))
        self.assertEqual(ast.literal_eval(output.strip()), (0, 0))

    def test_paired_bootstrap_rejects_empty_or_unpaired_samples(self):
        function, _ = example('paired_bootstrap_interval')
        for first, second in (([], []), ([1, 0], [1])):
            with self.assertRaises(ValueError):
                function(first, second)

    def test_paired_bootstrap_rejects_fewer_than_two_draws(self):
        function, _ = example('paired_bootstrap_interval')
        with self.assertRaises(ValueError):
            function([1], [1], draws=1)

    def test_matching_coverage_uses_one_to_one_assignment_and_augmentation(self):
        function, output = example('matched_coverage')
        self.assertEqual(function([[0, 1]], 2), .5)
        self.assertEqual(function([[0, 1], [0]], 2), 1)
        self.assertEqual([float(line) for line in output.splitlines()], [.5, 1])

    def test_matching_coverage_rejects_invalid_gold_count(self):
        function, _ = example('matched_coverage')
        with self.assertRaises(ValueError):
            function([], 0)

    def test_matching_coverage_rejects_out_of_range_matching_edges(self):
        function, _ = example('matched_coverage')
        for edge in (-1, 2):
            with self.assertRaises(ValueError):
                function([[edge]], 2)
