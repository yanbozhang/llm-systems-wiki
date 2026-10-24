"""业务Agent模拟契约测试，不操作设备、业务系统或真实代码仓库。"""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest


def load_example(name):
    p = Path(__file__).resolve().parents[1] / 'examples/agents' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


task = load_example('task-loop')
gui = load_example('gui-agent')
coding = load_example('coding-agent')
evaluation = load_example('agent-evaluation')


class BusinessTaskTests(unittest.TestCase):
    def test_terminal_truth_table_retains_unknown_and_prioritizes_failure(self):
        for values, expected in (([True, True], 'succeeded'), ([True, None], 'unknown'),
                                  ([False, None], 'failed'), ([None, False], 'failed'), ([None, None], 'unknown')):
            self.assertEqual(task.terminal_contract(dict(enumerate(values))), expected)
        for checks in ({}, {'a': 1}, {'a': 'true'}):
            with self.assertRaises(ValueError):
                task.terminal_contract(checks)

    def test_frontier_waits_for_all_parents_and_propagates_only_dependent_failures(self):
        graph = {'a': set(), 'b': set(), 'draft': {'a', 'b'}, 'verify': {'draft'}, 'template': set()}
        self.assertEqual(task.task_frontier(graph, {'a'}, set()),
                         {'ready': ['b', 'template'], 'blocked': [], 'all_completed': False})
        self.assertEqual(task.task_frontier(graph, {'a'}, {'b'}),
                         {'ready': ['template'], 'blocked': ['b', 'draft', 'verify'], 'all_completed': False})
        self.assertTrue(task.task_frontier(graph, set(graph), set())['all_completed'])
        self.assertEqual(task.task_frontier({}, set(), set()), {'ready': [], 'blocked': [], 'all_completed': True})

    def test_frontier_rejects_cycles_dangling_dependencies_and_inconsistent_completion(self):
        for graph, completed, failed in (({'a': {'b'}, 'b': {'a'}}, set(), set()),
                                        ({'a': {'missing'}}, set(), set()),
                                        ({'a': set(), 'b': {'a'}}, {'b'}, set()),
                                        ({'a': set()}, {'a'}, {'a'})):
            with self.assertRaises(ValueError):
                task.task_frontier(graph, completed, failed)

    def test_compensation_reconciles_unknown_before_irreversibility(self):
        actions = [{'id': 'sent', 'status': 'committed', 'reversible': False},
                   {'id': 'u1', 'status': 'unknown', 'reversible': True},
                   {'id': 'u2', 'status': 'unknown', 'reversible': False}]
        self.assertEqual(task.compensation_plan(actions), {'mode': 'reconcile', 'actions': ['u1', 'u2']})
        self.assertEqual(task.compensation_plan(actions[:1]), {'mode': 'manual', 'actions': []})

    def test_compensation_reverses_only_committed_actions_without_mutation(self):
        actions = [{'id': 'draft', 'status': 'committed', 'reversible': True},
                   {'id': 'none', 'status': 'absent', 'reversible': False},
                   {'id': 'index', 'status': 'committed', 'reversible': True}]
        before = copy.deepcopy(actions)
        self.assertEqual(task.compensation_plan(actions), {'mode': 'compensate', 'actions': ['index', 'draft']})
        self.assertEqual(actions, before)
        self.assertEqual(task.compensation_plan([]), {'mode': 'compensate', 'actions': []})

    def test_compensation_rejects_duplicate_id_status_and_implicit_reversibility(self):
        valid = {'id': 'a', 'status': 'committed', 'reversible': True}
        for actions in ([valid, valid], [dict(valid, status='failed')], [dict(valid, reversible=1)]):
            with self.assertRaises(ValueError):
                task.compensation_plan(actions)

    def test_task_demo_all_three_outputs(self):
        result = task.demo()
        self.assertEqual(result['terminal'], 'unknown')
        self.assertEqual(result['frontier']['ready'], ['draft'])
        self.assertEqual(result['compensation']['actions'], ['index', 'draft'])


class GuiMechanismTests(unittest.TestCase):
    def test_map_scaling_letterbox_crop_origin_and_inclusive_display_endpoints(self):
        view, device = (100, 50, 200, 100), (10, 20, 400, 200)
        self.assertEqual(gui.map_point((150, 100), view, device), (110, 120))
        self.assertEqual(gui.map_point((100, 50), view, device), (10, 20))
        self.assertEqual(gui.map_point((300, 150), view, device), (409, 219))
        self.assertEqual(gui.map_point((100.49, 50.49), view, device), (10, 20))
        self.assertEqual(gui.map_point((1, 1), (0, 0, 1, 1), (7, 8, 1, 1)), (7, 8))

    def test_map_rejects_letterbox_points_nonfinite_or_invalid_size(self):
        for point in ((99, 60), (301, 60), (150, 49), (150, 151), (float('nan'), 60)):
            with self.assertRaises(ValueError):
                gui.map_point(point, (100, 50, 200, 100), (10, 20, 400, 200))
        with self.assertRaises(ValueError):
            gui.map_point((0, 0), (0, 0, 0, 100), (0, 0, 10, 10))

    def test_observation_gate_age_and_each_layout_dimension(self):
        observed = {'captured_at': 10, 'layout_revision': 'v1', 'width': 100, 'height': 80, 'scroll': 0, 'overlay': False}
        current = dict(observed, busy=False)
        self.assertEqual(gui.observation_gate(observed, current, 10.5, 1), 'act')
        self.assertEqual(gui.observation_gate(observed, current, 11, 1), 'reobserve')
        for field, value in (('layout_revision', 'v2'), ('width', 101), ('height', 81), ('scroll', 1), ('overlay', True)):
            self.assertEqual(gui.observation_gate(observed, dict(current, **{field: value}), 10.5, 1), 'relocalize')
        self.assertEqual(gui.observation_gate(observed, dict(current, busy=True, scroll=1), 20, 1), 'wait')
        with self.assertRaises(ValueError):
            gui.observation_gate(observed, current, 9, 1)

    def test_verification_separates_grounding_driver_unknown_and_business(self):
        box = (10, 20, 30, 40)
        self.assertEqual(gui.verify_gui_action((10, 20), box, True, True), 'succeeded')
        self.assertEqual(gui.verify_gui_action((10, 20), box, False, True), 'driver_error')
        self.assertEqual(gui.verify_gui_action((10, 20), box, True, None), 'unknown')
        self.assertEqual(gui.verify_gui_action((10, 20), box, True, False), 'business_mismatch')
        for point in ((30, 20), (10, 40), (9, 20)):
            self.assertEqual(gui.verify_gui_action(point, box, True, True), 'grounding_error')

    def test_gui_verification_rejects_invalid_box_or_result_types(self):
        with self.assertRaises(ValueError):
            gui.verify_gui_action((0, 0), (0, 0, 0, 1), True, True)
        with self.assertRaises(ValueError):
            gui.verify_gui_action((0, 0), (0, 0, 1, 1), 1, True)
        with self.assertRaises(ValueError):
            gui.verify_gui_action((0, 0), (0, 0, 1, 1), True, 0)

    def test_gui_demo_outputs(self):
        self.assertEqual(gui.demo(), {'point': (480, 540), 'verification': 'unknown'})


class CodingMechanismTests(unittest.TestCase):
    def test_repository_slice_includes_callers_callees_and_radius_only(self):
        calls = {'entry': {'parse'}, 'parse': {'normalize'}, 'outer': {'entry'}, 'unrelated': set()}
        before = copy.deepcopy(calls)
        self.assertEqual(coding.repository_slice(calls, {'parse'}, 0), ['parse'])
        self.assertEqual(coding.repository_slice(calls, {'parse'}, 1), ['entry', 'normalize', 'parse'])
        self.assertEqual(coding.repository_slice(calls, {'parse'}, 2), ['entry', 'normalize', 'outer', 'parse'])
        self.assertEqual(coding.repository_slice(calls, {'normalize'}, 1), ['normalize', 'parse'])
        self.assertEqual(calls, before)
        with self.assertRaises(ValueError):
            coding.repository_slice(calls, {'unknown'}, 1)

    def test_guarded_replace_matches_baseline_and_returns_unexecuted_source(self):
        source = 'raise RuntimeError("仅解析，不执行")\ndef f(x):\n    return x\n'
        digest = hashlib.sha256(source.encode()).hexdigest()
        candidate = coding.guarded_replace(source, 'return x', 'return x + 1', digest)
        self.assertEqual(candidate, 'raise RuntimeError("仅解析，不执行")\ndef f(x):\n    return x + 1\n')
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), digest)

    def test_guarded_replace_rejects_stale_missing_duplicate_or_empty_anchor(self):
        source = 'x = 1\ny = 1\n'
        digest = hashlib.sha256(source.encode()).hexdigest()
        for old, expected in (('x = 1', 'stale'), ('missing', digest), ('1', digest), ('', digest)):
            with self.assertRaises(ValueError):
                coding.guarded_replace(source, old, '2', expected)
        with self.assertRaises(SyntaxError):
            coding.guarded_replace(source, 'x = 1', 'x = (', digest)

    def test_grade_preserves_regression_failure_missing_and_stale_evidence(self):
        repair, regression = {'fix'}, {'normal', 'edge'}
        result = coding.grade_patch(repair, regression, {'fix': 'passed', 'normal': 'failed'}, 'p2', 'p2')
        self.assertEqual(result, {'status': 'failed', 'missing': ['edge'], 'failed': ['normal']})
        self.assertEqual(coding.grade_patch(repair, regression, {'fix': 'passed'}, 'p2', 'p1'),
                         {'status': 'stale', 'missing': [], 'failed': []})
        self.assertEqual(coding.grade_patch({'fix'}, {'normal'}, {'fix': 'passed', 'normal': 'passed'}, 'p1', 'p1')['status'], 'succeeded')

    def test_grade_unknown_empty_groups_and_invalid_status_contracts(self):
        self.assertEqual(coding.grade_patch({'fix'}, {'normal'}, {'fix': 'passed'}, 'p1', 'p1')['status'], 'unknown')
        self.assertEqual(coding.grade_patch(set(), {'normal'}, {'normal': 'passed'}, 'p1', 'p1')['status'], 'unknown')
        with self.assertRaises(ValueError):
            coding.grade_patch({'same'}, {'same'}, {}, 'p1', 'p1')
        with self.assertRaises(ValueError):
            coding.grade_patch({'fix'}, {'normal'}, {'normal': 'skipped'}, 'p1', 'p1')

    def test_coding_demo_slice_and_grade(self):
        result = coding.demo()
        self.assertEqual(result['context'], ['entry', 'normalize', 'parse'])
        self.assertEqual(result['grade'], {'status': 'failed', 'missing': [], 'failed': ['normal_input']})


class AgentEvaluationTests(unittest.TestCase):
    def test_success_summary_fixed_task_denominator_retry_and_unknown_bounds(self):
        histories = {'a': ['success'], 'b': ['success'], 'c': ['success'],
                     'd': ['failure', 'success'], 'e': ['unknown']}
        self.assertEqual(evaluation.success_summary(histories), {'tasks': 5, 'attempts': 6,
            'first_rate': 0.6, 'eventual_lower': 0.8, 'eventual_upper': 1, 'unresolved_tasks': 1})
        histories['d'].append('failure')
        result = evaluation.success_summary(histories)
        self.assertEqual(result['attempts'], 7)
        self.assertEqual(result['eventual_lower'], 0.8)
        self.assertEqual(evaluation.success_summary({'a': ['success', 'unknown']})['unresolved_tasks'], 0)

    def test_success_summary_rejects_empty_history_and_unknown_enum(self):
        for histories in ({}, {'a': []}, {'a': ['passed']}):
            with self.assertRaises(ValueError):
                evaluation.success_summary(histories)

    def test_first_divergence_requires_evidence_preserves_unknown_and_is_not_causal_proof(self):
        trace = [{'stage': 'read', 'passed': True, 'evidence': 'source'},
                 {'stage': 'plan', 'passed': None, 'evidence': 'pending'},
                 {'stage': 'locate', 'passed': False, 'evidence': ''},
                 {'stage': 'execute', 'passed': False, 'evidence': 'receipt'},
                 {'stage': 'verify', 'passed': False, 'evidence': 'artifact'}]
        self.assertEqual(evaluation.first_divergence(trace), {'candidate': 'execute', 'evidence': 'receipt',
            'earlier_unknown': ['plan', 'locate'], 'causality': 'unproven'})
        self.assertEqual(evaluation.first_divergence([{'stage': 'claim', 'passed': True, 'evidence': None}]),
                         {'candidate': None, 'evidence': None, 'earlier_unknown': ['claim'], 'causality': 'unproven'})

    def test_evaluator_confusion_counts_distinct_and_unlabeled_not_negative(self):
        predictions = [True, True, True, False, False, False, False, False, True]
        labels = [True, True, False, False, False, False, True, True, None]
        self.assertEqual(evaluation.audit_evaluator(predictions, labels),
                         {'tp': 2, 'fp': 1, 'tn': 3, 'fn': 2, 'unlabeled': 1, 'precision': 2 / 3, 'recall': 0.5})
        swapped = evaluation.audit_evaluator(labels[:-1], predictions[:-1])
        self.assertEqual(swapped['fp'], 2)
        self.assertEqual(swapped['fn'], 1)

    def test_evaluator_empty_zero_denominators_and_invalid_types(self):
        self.assertEqual(evaluation.audit_evaluator([], []),
                         {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0, 'unlabeled': 0, 'precision': None, 'recall': None})
        self.assertEqual(evaluation.audit_evaluator([True], [None])['unlabeled'], 1)
        for predictions, labels in (([True], []), ([1], [True]), ([True], [1])):
            with self.assertRaises(ValueError):
                evaluation.audit_evaluator(predictions, labels)

    def test_agent_evaluation_demo_outputs(self):
        result = evaluation.demo()
        self.assertEqual(result['tasks']['first_rate'], 1 / 3)
        self.assertEqual(result['tasks']['eventual_lower'], 2 / 3)
        self.assertEqual(result['tasks']['eventual_upper'], 1)
        self.assertEqual(result['audit']['precision'], 0.5)
        self.assertEqual(result['audit']['recall'], 0.5)

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_task_loop_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/task-loop.py')

    def test_task_loop_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/task-loop.py')

    def test_gui_agent_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/gui-agent.py')

    def test_gui_agent_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/gui-agent.py')

    def test_coding_agent_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/coding-agent.py')

    def test_coding_agent_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/coding-agent.py')

    def test_agent_evaluation_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/agent-evaluation.py')

    def test_agent_evaluation_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/agent-evaluation.py')
