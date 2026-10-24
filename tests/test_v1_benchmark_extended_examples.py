"""六类评测的独立数学/状态断言；只运行标准库教学函数，不运行基准环境。"""
import copy
import importlib.util
import math
from pathlib import Path
import random
import unittest


def load_example(name):
    path = Path(__file__).resolve().parents[1] / 'examples/benchmark' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agents = load_example('benchmark-agents')
judge = load_example('benchmark-judge')
robust = load_example('benchmark-robustness')
rag = load_example('benchmark-rag')
systems = load_example('benchmark-systems')
multimodal = load_example('benchmark-multimodal')


class AgentBenchmarkTests(unittest.TestCase):
    def test_patch_full_requires_repair_but_regression_skip_is_version_specific(self):
        for status in ('PASSED', 'XFAIL'):
            result = agents.grade_patch(['fix'], ['keep'], {'fix': status, 'keep': 'SKIPPED'})
            self.assertEqual(result, {'status': 'FULL', 'resolved': True, 'f2p_rate': 1,
                                     'p2p_rate': 1, 'f2p_failed': [], 'p2p_failed': [],
                                     'missing': [], 'regression_tests': 1})
        no_regression = agents.grade_patch(['fix'], [], {'fix': 'PASSED'})
        self.assertTrue(no_regression['resolved'])
        self.assertEqual(no_regression['regression_tests'], 0)
        for status in ('FAILED', 'ERROR', 'SKIPPED'):
            self.assertFalse(agents.grade_patch(['fix'], [], {'fix': status})['resolved'])

    def test_patch_missing_partial_and_regression_failures_are_distinct(self):
        result = agents.grade_patch(['fix-2', 'fix-1'], ['keep'], {'fix-1': 'PASSED', 'keep': 'PASSED'})
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['f2p_rate'], 0.5)
        self.assertEqual(result['missing'], ['fix-2'])
        self.assertEqual(result['f2p_failed'], ['fix-2'])
        self.assertFalse(result['resolved'])
        for keep in ('FAILED', 'ERROR'):
            failed = agents.grade_patch(['fix'], ['keep'], {'fix': 'PASSED', 'keep': keep})
            self.assertEqual(failed['status'], 'NO')
            self.assertEqual(failed['p2p_failed'], ['keep'])
        missing = agents.grade_patch(['z'], ['a'], {})
        self.assertEqual(missing['missing'], ['a', 'z'])
        self.assertEqual(missing['p2p_rate'], 0)

    def test_patch_invalid_execution_cannot_resolve_and_bad_contract_is_rejected(self):
        for applied, ran in [(False, True), (True, False), (False, False)]:
            result = agents.grade_patch(['f'], [], {'f': 'PASSED'}, applied, ran)
            self.assertEqual(result['status'], 'INVALID')
            self.assertFalse(result['resolved'])
        for f2p, p2p in [([], []), (['f', 'f'], []), (['f'], ['p', 'p']), (['f'], ['f'])]:
            with self.assertRaises(ValueError):
                agents.grade_patch(f2p, p2p, {})
        with self.assertRaises(ValueError):
            agents.grade_patch(['f'], [], {'f': 'UNKNOWN'})
        with self.assertRaises(ValueError):
            agents.grade_patch(['f'], [], {'f': 'PASSED'}, patch_applied=1)

    def test_state_or_within_fields_and_and_across_fields_preserve_diagnostics(self):
        requirements = {'record': ['R1'], 'title': ['示例', '别名'], 'saved': [True]}
        state = {'record': 'R1', 'title': '别名', 'saved': False}
        before = copy.deepcopy((state, requirements))
        result = agents.state_acceptance(state, requirements)
        self.assertEqual(result['checks'], {'record': True, 'title': True, 'saved': False})
        self.assertEqual(result['fraction_met'], 2 / 3)
        self.assertFalse(result['resolved'])
        self.assertEqual(agents.state_acceptance(state, dict(reversed(list(requirements.items())))), result)
        self.assertTrue(agents.state_acceptance(dict(state, saved=True), requirements)['resolved'])
        missing = agents.state_acceptance({'record': 'R1', 'title': '示例'}, requirements)
        self.assertEqual(missing['missing'], ['saved'])
        self.assertFalse(missing['resolved'])
        self.assertEqual((state, requirements), before)

    def test_state_rejects_empty_or_malformed_acceptance_conditions(self):
        for requirements in ({}, {'saved': []}, {'saved': True}, {'saved': 'true'}):
            with self.assertRaises(ValueError):
                agents.state_acceptance({'saved': True}, requirements)

    def test_budget_keeps_assigned_tasks_attempts_and_environment_denominators(self):
        attempts = [{'task_id': 'A', 'attempt': 2, 'calls': 2, 'result': 'resolved'},
                    {'task_id': 'B', 'attempt': 1, 'calls': 3, 'result': 'failed'},
                    {'task_id': 'C', 'attempt': 1, 'calls': 0, 'result': 'infra_error'},
                    {'task_id': 'A', 'attempt': 1, 'calls': 2, 'result': 'failed'}]
        before = copy.deepcopy(attempts)
        self.assertEqual(agents.budget_report(['A', 'B', 'C', 'D'], attempts),
                         {'assigned_tasks': 4, 'first_successes': 0, 'budget_successes': 1,
                          'first_rate': 0, 'budget_rate': 0.25, 'executable_tasks': 2,
                          'conditional_budget_rate': 0.5, 'valid_attempts': 3,
                          'attempt_success_rate': 1 / 3, 'infra_errors': 1,
                          'over_budget_attempts': 0, 'unattempted_tasks': ['D'], 'observed_calls': 7})
        self.assertEqual(attempts, before)

    def test_budget_counts_failed_cost_and_excludes_success_outside_either_limit(self):
        for first_status in ('failed', 'infra_error'):
            attempts = [{'task_id': 'A', 'attempt': 1, 'calls': 2, 'result': first_status},
                        {'task_id': 'A', 'attempt': 2, 'calls': 3, 'result': 'resolved'}]
            self.assertEqual(agents.budget_report(['A'], attempts, 2, 5)['budget_rate'], 1)
            for max_attempts, max_calls in ((1, 5), (2, 4)):
                result = agents.budget_report(['A'], attempts, max_attempts, max_calls)
                self.assertEqual(result['budget_rate'], 0)
                self.assertEqual(result['observed_calls'], 5)
                self.assertEqual(result['over_budget_attempts'], 1)
                self.assertEqual(result['executable_tasks'], 1)
        twice = [{'task_id': 'A', 'attempt': i, 'calls': 0, 'result': 'resolved'} for i in (1, 2)]
        result = agents.budget_report(['A'], twice)
        self.assertEqual(result['budget_successes'], 1)
        self.assertEqual(result['first_successes'], 1)
        self.assertEqual(result['valid_attempts'], 2)

    def test_budget_no_executable_attempts_retains_undefined_conditional_rates(self):
        for attempts in ([], [{'task_id': 'A', 'attempt': 1, 'calls': 1, 'result': 'infra_error'}]):
            result = agents.budget_report(['A'], attempts)
            self.assertEqual(result['budget_rate'], 0)
            self.assertIsNone(result['conditional_budget_rate'])
            self.assertIsNone(result['attempt_success_rate'])
        self.assertEqual(agents.budget_report(['A'], [])['unattempted_tasks'], ['A'])

    def test_budget_rejects_identity_sequence_and_cost_errors(self):
        row = {'task_id': 'A', 'attempt': 1, 'calls': 1, 'result': 'failed'}
        for attempts in ([row, row], [dict(row, attempt=2)],
                         [row, dict(row, attempt=3)], [dict(row, task_id='B')],
                         [dict(row, result='unknown')], [dict(row, calls=-1)],
                         [dict(row, calls=True)], [dict(row, attempt=True)]):
            with self.assertRaises(ValueError):
                agents.budget_report(['A'], attempts)
        for ids in ([], ['A', 'A']):
            with self.assertRaises(ValueError):
                agents.budget_report(ids, [])
        for attempts, calls in ((0, 5), (3, 0), (True, 5)):
            with self.assertRaises(ValueError):
                agents.budget_report(['A'], [], attempts, calls)

    def test_agent_benchmark_demo_has_three_independent_diagnostics(self):
        result = agents.demo()
        self.assertEqual(result['patch']['status'], 'NO')
        self.assertFalse(result['state']['resolved'])
        self.assertEqual(result['state']['fraction_met'], 2 / 3)
        self.assertEqual(result['budget']['budget_rate'], 1 / 3)
        self.assertEqual(result['budget']['conditional_budget_rate'], 0.5)
        self.assertEqual(result['budget']['observed_calls'], 7)


class JudgeBenchmarkTests(unittest.TestCase):
    def test_swapped_pair_identity_mapping_and_four_denominators(self):
        rows = [{'id': str(i), 'winner_ab': a, 'winner_ba': b}
                for i, (a, b) in enumerate([('A', 'B'), ('A', 'A'), ('tie', 'tie'), ('error', 'B')])]
        before = copy.deepcopy(rows)
        result = judge.swapped_pair_summary(rows)
        self.assertEqual(result['counts'], {'A': 1, 'B': 0, 'tie': 1, 'inconsistent': 1, 'invalid': 1})
        self.assertEqual([d['result'] for d in result['details']], ['A', 'inconsistent', 'tie', 'invalid'])
        self.assertEqual([d['swapped_to_original'] for d in result['details']], ['A', 'B', 'tie', 'A'])
        self.assertEqual(result['parse_coverage'], 7 / 8)
        self.assertEqual(result['valid_pair_coverage'], 3 / 4)
        self.assertEqual(result['consistency_on_valid_pairs'], 2 / 3)
        self.assertEqual(result['consistent_pair_fraction'], 0.5)
        self.assertEqual(result['first_slot_fraction_on_decisive_calls'], 3 / 5)
        self.assertEqual(rows, before)
        self.assertEqual(judge.swapped_pair_summary([{'id': 'b', 'winner_ab': 'B', 'winner_ba': 'A'}])['counts']['B'], 1)

    def test_swapped_all_errors_and_ties_keep_undefined_denominators(self):
        result = judge.swapped_pair_summary([{'id': 'x', 'winner_ab': 'error', 'winner_ba': 'error'}])
        self.assertEqual(result['counts']['invalid'], 1)
        self.assertEqual(result['counts']['tie'], 0)
        self.assertEqual(result['parse_coverage'], 0)
        self.assertIsNone(result['consistency_on_valid_pairs'])
        self.assertIsNone(result['first_slot_fraction_on_decisive_calls'])
        tie = judge.swapped_pair_summary([{'id': 'x', 'winner_ab': 'tie', 'winner_ba': 'tie'}])
        self.assertEqual(tie['consistency_on_valid_pairs'], 1)
        self.assertIsNone(tie['first_slot_fraction_on_decisive_calls'])

    def test_swapped_rejects_empty_duplicate_and_invalid_labels(self):
        row = {'id': 'x', 'winner_ab': 'A', 'winner_ba': 'B'}
        for rows in ([], [row, row], [dict(row, winner_ab=None)], [dict(row, winner_ba='unknown')]):
            with self.assertRaises(ValueError):
                judge.swapped_pair_summary(rows)

    def test_agreement_matrix_hand_value_and_reviewer_symmetry(self):
        human, automatic = ['A', 'A', 'A', 'B', 'tie', 'tie'], ['A', 'A', 'B', 'B', 'B', 'tie']
        before = copy.deepcopy((human, automatic))
        result = judge.agreement_audit(human, automatic)
        self.assertEqual(result['matrix'], [[2, 1, 0], [0, 1, 0], [0, 1, 1]])
        self.assertEqual(result['human_marginals'], [3, 1, 2])
        self.assertEqual(result['judge_marginals'], [2, 3, 1])
        self.assertEqual(result['observed_agreement'], 4 / 6)
        self.assertEqual(result['chance_agreement'], 11 / 36)
        self.assertEqual(result['kappa'], 13 / 25)
        reverse = judge.agreement_audit(automatic, human)
        self.assertEqual(reverse['matrix'], [[2, 0, 0], [1, 1, 1], [0, 0, 1]])
        self.assertEqual(reverse['kappa'], result['kappa'])
        self.assertEqual((human, automatic), before)

    def test_agreement_marginal_baseline_perfect_mixed_and_degenerate_cases(self):
        majority = judge.agreement_audit(['A'] * 19 + ['B'], ['A'] * 20)
        self.assertEqual(majority['observed_agreement'], 0.95)
        self.assertEqual(majority['chance_agreement'], 0.95)
        self.assertEqual(majority['kappa'], 0)
        self.assertIsNone(judge.agreement_audit(['A'], ['A'])['kappa'])
        self.assertEqual(judge.agreement_audit(['A', 'B'], ['A', 'B'])['kappa'], 1)
        self.assertEqual(judge.agreement_audit(['A', 'B'], ['B', 'A'])['kappa'], -1)

    def test_agreement_rejects_unpaired_empty_or_unparsed_labels(self):
        for human, automatic in [([], []), (['A'], []), (['A'], ['error']), ([None], ['tie'])]:
            with self.assertRaises(ValueError):
                judge.agreement_audit(human, automatic)

    def test_calibration_independent_brier_ece_and_acceptance_hand_calculation(self):
        probabilities, labels = [0.9, 0.8, 0.6, 0.2], [1, 1, 0, 0]
        result = judge.calibration_audit(probabilities, labels)
        self.assertAlmostEqual(result['binary_brier'], 0.1125)
        self.assertAlmostEqual(result['ece'], 0.125)
        self.assertEqual(result['accepted'], 2)
        self.assertEqual(result['coverage'], 0.5)
        self.assertEqual(result['accepted_error'], 0)
        self.assertEqual([b['count'] for b in result['reliability']], [1, 3])
        self.assertAlmostEqual(result['reliability'][1]['mean_probability'], 23 / 30)
        self.assertEqual(result['reliability'][1]['event_frequency'], 2 / 3)
        self.assertEqual(probabilities, [0.9, 0.8, 0.6, 0.2])
        self.assertEqual(labels, [1, 1, 0, 0])

    def test_calibration_boundary_bins_and_absent_acceptance(self):
        result = judge.calibration_audit([0, 0.5, 1], [0, 1, 1], bins=2, threshold=0.5)
        self.assertEqual([b['count'] for b in result['reliability']], [1, 2])
        self.assertEqual(result['accepted'], 2)
        self.assertAlmostEqual(result['ece'], 1 / 6)
        self.assertAlmostEqual(result['binary_brier'], 1 / 12)
        empty_bins = judge.calibration_audit([0, 1], [False, True], bins=4)
        self.assertEqual([b['count'] for b in empty_bins['reliability']], [1, 0, 0, 1])
        self.assertIsNone(empty_bins['reliability'][1]['mean_probability'])
        self.assertIsNone(empty_bins['reliability'][2]['event_frequency'])
        none = judge.calibration_audit([0.2], [0], threshold=0.8)
        self.assertEqual(none['coverage'], 0)
        self.assertIsNone(none['accepted_error'])
        all_accepted = judge.calibration_audit([0, 1], [1, 0], threshold=0)
        self.assertEqual(all_accepted['coverage'], 1)
        self.assertEqual(all_accepted['accepted_error'], 0.5)

    def test_calibration_rejects_shapes_nonfinite_values_and_invalid_labels(self):
        for probabilities, labels in [([], []), ([0.5], []), ([0.5], [2]), ([0.5], [1.0])]:
            with self.assertRaises(ValueError):
                judge.calibration_audit(probabilities, labels)
        for probability in (float('nan'), float('inf'), -0.1, 1.1, True):
            with self.assertRaises(ValueError):
                judge.calibration_audit([probability], [0])
            with self.assertRaises(ValueError):
                judge.calibration_audit([0.5], [0], threshold=probability)
        for bins in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                judge.calibration_audit([0.5], [0], bins=bins)

    def test_judge_demo_all_three_statistics(self):
        result = judge.demo()
        self.assertEqual(result['swapping']['consistency_on_valid_pairs'], 2 / 3)
        self.assertEqual(result['agreement']['kappa'], 0.52)
        self.assertAlmostEqual(result['calibration']['binary_brier'], 0.1125)
        self.assertAlmostEqual(result['calibration']['ece'], 0.125)


class RobustnessBenchmarkTests(unittest.TestCase):
    @staticmethod
    def case(task='T', goal='G', u=True, a=False, side=False, exposed=False):
        return {'user_task': task, 'injection_goal': goal, 'utility': u,
                'attack_success': a, 'side_effect': side, 'exposed': exposed}

    def test_security_uses_distinct_task_case_and_conditional_denominators(self):
        benign = {'T1': True, 'T2': True, 'T3': True, 'T4': False}
        cases = [self.case('T1', exposed=True), self.case('T2', u=False, a=True, side=True, exposed=True),
                 self.case('T3', a=True, side=True), self.case('T4', u=False),
                 self.case('T1', 'G2', side=True)]
        before = copy.deepcopy((benign, cases))
        result = robust.security_metrics(benign, cases)
        self.assertEqual(result, {'benign_tasks': 4, 'security_cases': 5, 'benign_utility': 0.75,
                                 'raw_attacked_utility': 3 / 5, 'targeted_asr': 2 / 5,
                                 'side_effect_rate': 3 / 5, 'secure_utility_in_scope': 1 / 5,
                                 'joint_utility_attack': {'utility_only': 2, 'attack_only': 1, 'both': 1, 'neither': 1},
                                 'exposed_cases': 2, 'conditional_asr_exposed': 0.5,
                                 'benign_solved_cases': 4, 'conditional_asr_benign_solved': 0.5})
        self.assertEqual((benign, cases), before)

    def test_security_no_exposed_or_benign_solved_subset_is_undefined(self):
        result = robust.security_metrics({'T': False}, [self.case()])
        self.assertEqual(result['targeted_asr'], 0)
        self.assertEqual(result['secure_utility_in_scope'], 1)
        self.assertIsNone(result['conditional_asr_exposed'])
        self.assertIsNone(result['conditional_asr_benign_solved'])
        # 正常任务True不能作为无注入占位值混入ASR。
        clean = robust.security_metrics({'T': True, 'normal-only': True}, [self.case(u=False)])
        self.assertEqual(clean['benign_utility'], 1)
        self.assertEqual(clean['security_cases'], 1)
        self.assertEqual(clean['targeted_asr'], 0)

    def test_security_rejects_duplicate_unknown_or_inconsistent_labels(self):
        row = self.case()
        for benign, cases in [({}, [row]), ({'T': True}, []), ({'T': 1}, [row]),
                              ({'T': True}, [row, row]), ({'other': True}, [row]),
                              ({'T': True}, [self.case(a=True, side=False)])]:
            with self.assertRaises(ValueError):
                robust.security_metrics(benign, cases)
        for field in ('utility', 'attack_success', 'side_effect', 'exposed'):
            for invalid in (None, 0):
                with self.assertRaises(ValueError):
                    robust.security_metrics({'T': True}, [dict(row, **{field: invalid})])

    def test_authorization_requires_registered_tool_schema_and_resource_capability(self):
        registry = {'read': {'schema': {'fixture_id': str}, 'operation': 'read'},
                    'update': {'schema': {'fixture_id': str, 'version': int}, 'operation': 'update'}}
        capabilities = {('read', 'F1')}
        before = copy.deepcopy((registry, capabilities))
        self.assertEqual(robust.authorize_fixture_call('read', {'fixture_id': 'F1'}, registry, capabilities),
                         {'allowed': True, 'reason': 'authorized', 'required_capability': ('read', 'F1')})
        cases = [('absent', {}, 'unregistered_tool'), ('read', {}, 'schema_fields'),
                 ('read', {'fixture_id': 'F1', 'extra': 1}, 'schema_fields'),
                 ('read', {'fixture_id': {'nested_call': 'read'}}, 'schema_types'),
                 ('update', {'fixture_id': 'F1', 'version': True}, 'schema_types'),
                 ('update', {'fixture_id': 'F1', 'version': 1}, 'missing_resource_capability'),
                 ('read', {'fixture_id': 'F2'}, 'missing_resource_capability')]
        for tool, args, reason in cases:
            args_before = copy.deepcopy(args)
            self.assertEqual(robust.authorize_fixture_call(tool, args, registry, capabilities),
                             {'allowed': False, 'reason': reason})
            self.assertEqual(args, args_before)
        self.assertEqual((registry, capabilities), before)
        result = robust.authorize_fixture_call('update', {'fixture_id': 'F1', 'version': 1},
                                               registry, {('update', 'F1')})
        self.assertEqual(result['required_capability'], ('update', 'F1'))
        self.assertTrue(result['allowed'])

    def test_authorization_rejects_invalid_trusted_registry_configuration(self):
        for spec in ({'schema': {'fixture_id': int}, 'operation': 'read'},
                     {'schema': {'fixture_id': str}, 'operation': 'delete'}):
            with self.assertRaises(ValueError):
                robust.authorize_fixture_call('x', {'fixture_id': 'F1'}, {'x': spec}, {('read', 'F1')})

    def test_paired_effects_four_cells_and_net_identity_ignore_dictionary_order(self):
        reference = {'a': True, 'b': True, 'c': False, 'd': False}
        defended = {'d': False, 'c': True, 'b': False, 'a': True}
        before = copy.deepcopy((reference, defended))
        result = robust.paired_control_effects(reference, defended)
        self.assertEqual(result, {'pairs': 4, 'counts': {'kept_success': 1, 'lost': 1, 'gained': 1, 'kept_failure': 1},
                                 'reference_rate': 0.5, 'defended_rate': 0.5,
                                 'gain_rate': 0.25, 'loss_rate': 0.25, 'net_effect': 0})
        changed = robust.paired_control_effects(reference, dict(defended, d=True))
        self.assertEqual(changed['net_effect'], 0.25)
        self.assertEqual(changed['net_effect'], changed['defended_rate'] - changed['reference_rate'])
        self.assertEqual(changed['net_effect'], changed['gain_rate'] - changed['loss_rate'])
        self.assertEqual((reference, defended), before)

    def test_paired_effects_rejects_changed_identity_set_and_unknown_labels(self):
        for first, second in [({}, {}), ({'a': True}, {'b': True}),
                              ({'a': True}, {'a': None}), ({'a': 1}, {'a': True})]:
            with self.assertRaises(ValueError):
                robust.paired_control_effects(first, second)

    def test_robustness_demo_keeps_utility_attack_and_permission_separate(self):
        result = robust.demo()
        self.assertEqual(result['metrics']['benign_utility'], 0.75)
        self.assertEqual(result['metrics']['targeted_asr'], 0.5)
        self.assertEqual(result['metrics']['secure_utility_in_scope'], 0.25)
        self.assertTrue(result['read_decision']['allowed'])
        self.assertFalse(result['update_decision']['allowed'])
        self.assertEqual(result['paired']['net_effect'], 0)
        self.assertEqual(result['paired']['counts']['lost'], 1)


class RagBenchmarkTests(unittest.TestCase):
    def test_context_ap_precision_and_corpus_denominators_are_distinct(self):
        labels = [1, 0, 1]
        result = rag.context_precision_profile(labels, 4)
        # 分子1+2/3=5/3；AP分母有正文声明的正epsilon。
        self.assertAlmostEqual(result['context_ap'], 5 / 6)
        self.assertLess(result['context_ap'], 5 / 6)
        self.assertEqual(result['precision_at_k'], 2 / 3)
        self.assertAlmostEqual(result['corpus_ap'], 5 / 12)
        self.assertEqual(result['recall_at_k'], 0.5)
        self.assertEqual(result['retrieved_count'], 3)
        self.assertEqual(result['relevant_retrieved'], 2)
        self.assertFalse(result['empty_context'])
        self.assertGreater(rag.context_precision_profile([1, 1, 0], 4)['context_ap'], result['context_ap'])
        one = rag.context_precision_profile([1], 10)
        self.assertAlmostEqual(one['context_ap'], 1)
        self.assertEqual(one['recall_at_k'], 0.1)
        self.assertEqual(labels, [1, 0, 1])

    def test_context_empty_zero_labels_and_unknown_corpus_denominators(self):
        empty = rag.context_precision_profile([], 0)
        self.assertEqual(empty['context_ap'], 0)
        self.assertTrue(empty['empty_context'])
        for key in ('precision_at_k', 'corpus_ap', 'recall_at_k'):
            self.assertIsNone(empty[key])
        zeros = rag.context_precision_profile([0, 0], 3)
        self.assertFalse(zeros['empty_context'])
        self.assertEqual(zeros['precision_at_k'], 0)
        self.assertEqual(zeros['corpus_ap'], 0)
        self.assertEqual(zeros['recall_at_k'], 0)
        self.assertIsNone(rag.context_precision_profile([1])['recall_at_k'])

    def test_context_rejects_nonbinary_labels_and_impossible_corpus_counts(self):
        for labels in ([-1], [0.5], ['1'], [None]):
            with self.assertRaises(ValueError):
                rag.context_precision_profile(labels)
        for count in (1, -1, True, 2.5):
            with self.assertRaises(ValueError):
                rag.context_precision_profile([1, 1], count)

    def test_claim_reference_and_answer_sets_use_their_own_denominators(self):
        self.assertEqual(rag.claim_coverage([1, 0, 0, 0], [1]),
                         {'context_recall': 0.25, 'faithfulness': 1, 'reference_claim_count': 4,
                          'answer_claim_count': 1, 'reference_supported': 1, 'answer_supported': 1})
        self.assertIsNone(rag.claim_coverage([], [1])['context_recall'])
        self.assertIsNone(rag.claim_coverage([1], [])['faithfulness'])
        for reference, answer in [([2], [1]), ([1], [None]), ([1], [1.0])]:
            with self.assertRaises(ValueError):
                rag.claim_coverage(reference, answer)

    def test_judge_error_aligns_by_id_and_exposes_rate_bias(self):
        human = {'a': 1, 'b': 1, 'c': 0, 'd': 0}
        automatic = {'d': 0, 'c': 1, 'b': 1, 'a': 1}
        before = copy.deepcopy((human, automatic))
        result = rag.judge_error_audit(human, automatic)
        self.assertEqual(result, {'tp': 2, 'fn': 0, 'fp': 1, 'tn': 1, 'count': 4,
                                 'sensitivity': 1, 'false_positive_rate': 0.5,
                                 'human_support_rate': 0.5, 'judge_support_rate': 0.75, 'mean_bias': 0.25})
        balanced = rag.judge_error_audit(human, dict(automatic, b=0))
        self.assertEqual([balanced[x] for x in ('tp', 'fn', 'fp', 'tn')], [1, 1, 1, 1])
        self.assertEqual(balanced['mean_bias'], 0)
        self.assertEqual((human, automatic), before)

    def test_judge_error_empty_classes_and_invalid_id_or_labels(self):
        empty = rag.judge_error_audit({}, {})
        self.assertEqual(empty['count'], 0)
        for key in ('sensitivity', 'false_positive_rate', 'human_support_rate', 'judge_support_rate', 'mean_bias'):
            self.assertIsNone(empty[key])
        self.assertIsNone(rag.judge_error_audit({'a': 0}, {'a': 1})['sensitivity'])
        self.assertIsNone(rag.judge_error_audit({'a': 1}, {'a': 0})['false_positive_rate'])
        for human, automatic in [({'a': 1}, {'b': 1}), ({'a': 1}, {'a': 2}), ({'a': None}, {'a': 0})]:
            with self.assertRaises(ValueError):
                rag.judge_error_audit(human, automatic)

    def test_rag_benchmark_demo_all_three_metrics(self):
        result = rag.demo()
        self.assertAlmostEqual(result['ranking']['context_ap'], 5 / 6)
        self.assertEqual(result['claims']['context_recall'], 0.25)
        self.assertEqual(result['claims']['faithfulness'], 1)
        self.assertEqual(result['judge']['mean_bias'], 0.25)


class SystemsBenchmarkTests(unittest.TestCase):
    LOADGEN = ('min_duration', 'min_queries', 'min_samples', 'latency', 'early_stopping')
    SUBMISSION = ('accuracy', 'seed_and_settings', 'no_log_errors', 'compliance',
                  'system_and_measurements', 'division_and_model')

    def test_loadgen_uses_floor_index_quantile_and_request_tpot(self):
        rows = [{'ttft_ns': first, 'latency_ns': first + 30, 'tokens': 4} for first in (100, 10, 30, 20)]
        before = copy.deepcopy(rows)
        result = systems.loadgen_latency_profile(rows, 0.5)
        self.assertEqual(result, {'count': 4, 'ttft': {'mean_ns': 40, 'percentile_ns': 30},
                                 'tpot': {'mean_ns': 10, 'percentile_ns': 10},
                                 'tpot_per_request_ns': [10, 10, 10, 10]})
        self.assertEqual(systems.loadgen_latency_profile(rows, 0)['ttft']['percentile_ns'], 10)
        self.assertEqual(systems.loadgen_latency_profile(rows, 0.99)['ttft']['percentile_ns'], 100)
        self.assertEqual(rows, before)

    def test_loadgen_nanosecond_integer_truncation_and_empty_samples(self):
        rows = [{'ttft_ns': 1, 'latency_ns': 6, 'tokens': 3},
                {'ttft_ns': 4, 'latency_ns': 14, 'tokens': 4}]
        result = systems.loadgen_latency_profile(rows, 0.5)
        self.assertEqual(result['tpot_per_request_ns'], [2, 3])
        self.assertEqual(result['tpot'], {'mean_ns': 2, 'percentile_ns': 3})
        self.assertEqual(result['ttft'], {'mean_ns': 2, 'percentile_ns': 4})
        self.assertEqual(systems.loadgen_latency_profile([]),
                         {'count': 0, 'ttft': {'mean_ns': None, 'percentile_ns': None},
                          'tpot': {'mean_ns': None, 'percentile_ns': None}, 'tpot_per_request_ns': []})
        zero = systems.loadgen_latency_profile([{'ttft_ns': 0, 'latency_ns': 0, 'tokens': 2}])
        self.assertEqual(zero['tpot_per_request_ns'], [0])

    def test_loadgen_rejects_invalid_percentile_timing_and_token_domain(self):
        for p in (-0.1, 1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                systems.loadgen_latency_profile([], p)
        row = {'ttft_ns': 2, 'latency_ns': 5, 'tokens': 2}
        for change in ({'ttft_ns': -1}, {'latency_ns': 1}, {'tokens': 1},
                       {'tokens': True}, {'latency_ns': 5.0}, {'ttft_ns': False}):
            with self.assertRaises(ValueError):
                systems.loadgen_latency_profile([dict(row, **change)])

    def test_slo_id_intersection_and_frechet_bounds_preserve_failed_denominator(self):
        first = {'a': True, 'b': True, 'c': False}
        later = {'c': True, 'b': False, 'a': True}
        before = copy.deepcopy((first, later))
        result = systems.slo_overlap(first, later, 2)
        self.assertEqual(result, {'offered': 3, 'both_pass': 1, 'ttft_rate': 2 / 3,
                                 'tpot_rate': 2 / 3, 'joint_rate': 1 / 3, 'lower_bound': 1 / 3,
                                 'upper_bound': 2 / 3, 'latency_goodput_rps': 0.5})
        self.assertEqual((first, later), before)
        a = {'a': True, 'b': True, 'c': True, 'd': False}
        overlap = systems.slo_overlap(a, a, 1)
        disjoint_failures = systems.slo_overlap(a, {'a': False, 'b': True, 'c': True, 'd': True}, 1)
        self.assertEqual(overlap['ttft_rate'], disjoint_failures['ttft_rate'])
        self.assertEqual(overlap['tpot_rate'], disjoint_failures['tpot_rate'])
        self.assertEqual(overlap['joint_rate'], 0.75)
        self.assertEqual(disjoint_failures['joint_rate'], 0.5)

    def test_slo_empty_and_invalid_duration_ids_and_labels(self):
        result = systems.slo_overlap({}, {}, 1)
        self.assertEqual(result['latency_goodput_rps'], 0)
        for key in ('ttft_rate', 'tpot_rate', 'joint_rate', 'lower_bound', 'upper_bound'):
            self.assertIsNone(result[key])
        for duration in (0, -1, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                systems.slo_overlap({'a': True}, {'a': True}, duration)
        for first, later in [({'a': True}, {'b': True}), ({'a': 1}, {'a': True}), ({'a': True}, {'a': None})]:
            with self.assertRaises(ValueError):
                systems.slo_overlap(first, later, 1)

    def test_submission_requires_every_field_and_keeps_layers_separate(self):
        performance, submission = dict.fromkeys(self.LOADGEN, True), dict.fromkeys(self.SUBMISSION, True)
        result = systems.submission_layers(performance, submission)
        self.assertTrue(result['all_recorded_checks_passed'])
        self.assertEqual(result['loadgen_layer'], {'status': 'passed', 'failed': [], 'missing': []})
        self.assertEqual(result['submission_layer'], {'status': 'passed', 'failed': [], 'missing': []})
        for layer, fields in [('loadgen_layer', self.LOADGEN), ('submission_layer', self.SUBMISSION)]:
            for field in fields:
                for replacement, expected in [(False, 'failed'), (None, 'incomplete')]:
                    left, right = performance.copy(), submission.copy()
                    target = left if layer == 'loadgen_layer' else right
                    target[field] = replacement
                    result = systems.submission_layers(left, right)
                    self.assertEqual(result[layer]['status'], expected)
                    self.assertIn(field, result[layer]['failed' if replacement is False else 'missing'])
                    self.assertFalse(result['all_recorded_checks_passed'])
        missing = systems.submission_layers(performance, {})
        self.assertEqual(missing['loadgen_layer']['status'], 'passed')
        self.assertEqual(missing['submission_layer']['missing'], list(self.SUBMISSION))
        self.assertEqual(missing['submission_layer']['status'], 'incomplete')
        self.assertEqual(performance, dict.fromkeys(self.LOADGEN, True))

    def test_submission_failure_dominates_unknown_and_rejects_non_boolean_labels(self):
        result = systems.submission_layers({'latency': False}, {})
        self.assertEqual(result['loadgen_layer']['status'], 'failed')
        self.assertEqual(result['loadgen_layer']['failed'], ['latency'])
        self.assertIn('min_duration', result['loadgen_layer']['missing'])
        for left, right in [({'latency': 1}, {}), ({}, {'accuracy': 'passed'})]:
            with self.assertRaises(ValueError):
                systems.submission_layers(left, right)

    def test_systems_demo_keeps_latency_joint_goodput_and_submission_evidence_distinct(self):
        result = systems.demo()
        self.assertEqual(result['latency']['ttft']['percentile_ns'], 30)
        self.assertEqual(result['joint']['joint_rate'], 1 / 3)
        self.assertEqual(result['joint']['latency_goodput_rps'], 1)
        self.assertEqual(result['layers']['loadgen_layer']['status'], 'passed')
        self.assertEqual(result['layers']['submission_layer']['status'], 'incomplete')
        self.assertFalse(result['layers']['all_recorded_checks_passed'])


class MultimodalBenchmarkTests(unittest.TestCase):
    def test_square_pad_documented_legend_geometry(self):
        box = [0, 280, 640, 320]
        self.assertEqual(multimodal.square_pad_geometry(640, 320, box),
                         {'side': 640, 'offset': (0, 160), 'translated_box': (0, 440, 640, 480),
                          'normalized_box': (0, 0.6875, 1, 0.75), 'content_area_fraction': 0.5})
        self.assertEqual(box, [0, 280, 640, 320])

    def test_square_pad_tall_odd_and_square_inputs_preserve_area(self):
        tall = multimodal.square_pad_geometry(3, 6, (0, 0, 3, 6))
        self.assertEqual(tall['offset'], (1, 0))
        self.assertEqual(tall['translated_box'], (1, 0, 4, 6))
        self.assertEqual(tall['normalized_box'], (1 / 6, 0, 2 / 3, 1))
        self.assertEqual(tall['content_area_fraction'], 0.5)
        square = multimodal.square_pad_geometry(4, 4, (1, 2, 3, 4))
        self.assertEqual(square['offset'], (0, 0))
        self.assertEqual(square['translated_box'], (1, 2, 3, 4))
        self.assertEqual(square['content_area_fraction'], 1)
        for width, height, box in [(6, 3, (1, 0, 4, 2)), (3, 6, (0, 1, 2, 4))]:
            result = multimodal.square_pad_geometry(width, height, box)
            l, t, r, b = result['translated_box']
            self.assertEqual((r - l) * (b - t), 6)
            self.assertTrue(all(0 <= v <= 1 for v in result['normalized_box']))

    def test_square_pad_rejects_invalid_dimensions_and_outside_or_zero_area_boxes(self):
        for width, height in [(0, 3), (3, -1), (True, 3), (3, 2.5)]:
            with self.assertRaises(ValueError):
                multimodal.square_pad_geometry(width, height, (0, 0, 1, 1))
        for box in ((0, 0, 1), (0, 0, float('nan'), 1), (-1, 0, 1, 1),
                    (0, 0, 5, 1), (1, 0, 1, 1), (0, 3, 1, 2)):
            with self.assertRaises(ValueError):
                multimodal.square_pad_geometry(4, 4, box)

    def test_mmmu_choice_uses_exact_labels_and_has_no_random_fallback(self):
        state = random.getstate()
        self.assertTrue(multimodal.mmmu_answer_score('multiple-choice', ['A', 'C'], 'C'))
        self.assertFalse(multimodal.mmmu_answer_score('multiple-choice', 'A', 'a'))
        self.assertFalse(multimodal.mmmu_answer_score('multiple-choice', 'A', 'answer is A'))
        self.assertFalse(multimodal.mmmu_answer_score('multiple-choice', 'A', ''))
        self.assertEqual(random.getstate(), state)

    def test_mmmu_open_rounding_numeric_normalization_and_literal_substrings(self):
        self.assertTrue(multimodal.mmmu_answer_score('open', '3.14', [3.144]))
        self.assertFalse(multimodal.mmmu_answer_score('open', '3.14', [3.146]))
        self.assertTrue(multimodal.mmmu_answer_score('open', '1,000', ['1e3']))
        self.assertFalse(multimodal.mmmu_answer_score('open', '1 m', ['100 cm']))
        self.assertTrue(multimodal.mmmu_answer_score('open', 'art', ['EARTH']))
        self.assertTrue(multimodal.mmmu_answer_score('open', 'x', ['x axis']))
        self.assertFalse(multimodal.mmmu_answer_score('open', 'x', ['axe']))
        candidates = ['irrelevant', '3.144']
        self.assertTrue(multimodal.mmmu_answer_score('open', ['other', '3.14'], candidates))
        self.assertEqual(candidates, ['irrelevant', '3.144'])
        self.assertFalse(multimodal.mmmu_answer_score('open', '3.14', []))

    def test_mmmu_rejects_empty_reference_wrong_shape_and_nonfinite_numbers(self):
        for kind, gold, prediction in [('open', [], ['x']), ('unknown', 'A', ['A']),
                                       ('open', 'x', 'x'), ('multiple-choice', 'A', ['A'])]:
            with self.assertRaises(ValueError):
                multimodal.mmmu_answer_score(kind, gold, prediction)
        for value in ('nan', 'inf', '-inf'):
            with self.assertRaises(ValueError):
                multimodal.mmmu_answer_score('open', '1', [value])
            with self.assertRaises(ValueError):
                multimodal.mmmu_answer_score('open', value, ['1'])

    def test_stratified_micro_macro_and_failure_only_error_denominator(self):
        rows = [{'id': str(i), 'subject': 'chart', 'kind': 'image', 'correct': i < 3,
                 'error_layer': 'perception'} for i in range(4)]
        rows.append({'id': '4', 'subject': 'medicine', 'kind': 'image', 'correct': False})
        before = copy.deepcopy(rows)
        result = multimodal.stratified_accuracy(rows, expected_ids=set('01234'))
        self.assertEqual(result['groups'], {'chart': {'correct': 3, 'count': 4, 'accuracy': 0.75},
                                           'medicine': {'correct': 0, 'count': 1, 'accuracy': 0}})
        self.assertEqual(result['micro_accuracy'], 0.6)
        self.assertEqual(result['macro_accuracy'], 0.375)
        self.assertEqual(result['error_counts'], {'perception': 1, 'unclassified': 1})
        self.assertEqual(result['error_rates_among_failures'], {'perception': 0.5, 'unclassified': 0.5})
        by_kind = multimodal.stratified_accuracy(rows, group_key='kind')
        self.assertEqual(by_kind['macro_accuracy'], 0.6)
        self.assertEqual(rows, before)

    def test_stratified_empty_perfect_and_invalid_identity_or_labels(self):
        empty = multimodal.stratified_accuracy([], expected_ids=[])
        self.assertIsNone(empty['micro_accuracy'])
        self.assertIsNone(empty['macro_accuracy'])
        self.assertEqual(empty['error_rates_among_failures'], {})
        row = {'id': 'a', 'subject': 'chart', 'correct': True}
        perfect = multimodal.stratified_accuracy([row])
        self.assertEqual(perfect['micro_accuracy'], 1)
        self.assertEqual(perfect['error_counts'], {})
        for rows, ids in [([row, row], None), ([row], ['a', 'b']), ([dict(row, correct=1)], None)]:
            with self.assertRaises(ValueError):
                multimodal.stratified_accuracy(rows, expected_ids=ids)

    def test_multimodal_demo_all_three_functions(self):
        result = multimodal.demo()
        self.assertEqual(result['geometry']['translated_box'], (0, 440, 640, 480))
        self.assertIs(result['score'], True)
        self.assertEqual(result['groups']['micro_accuracy'], 2 / 3)
        self.assertEqual(result['groups']['macro_accuracy'], 0.5)

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_benchmark_agents_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-agents.py')

    def test_benchmark_agents_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-agents.py')

    def test_benchmark_judge_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-judge.py')

    def test_benchmark_judge_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-judge.py')

    def test_benchmark_robustness_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-robustness.py')

    def test_benchmark_robustness_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-robustness.py')

    def test_benchmark_rag_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-rag.py')

    def test_benchmark_rag_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-rag.py')

    def test_benchmark_systems_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-systems.py')

    def test_benchmark_systems_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-systems.py')

    def test_benchmark_multimodal_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-multimodal.py')

    def test_benchmark_multimodal_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-multimodal.py')
