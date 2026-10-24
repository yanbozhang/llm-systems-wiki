"""宿主教学函数的状态、预算、闭包与错误层级验证，仅使用模拟输入。"""
import copy
import importlib.util
import itertools
from pathlib import Path
import unittest
from unittest.mock import patch


def load_example(name):
    path = Path(__file__).resolve().parents[1] / 'examples/harness' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


loop = load_example('agent-loop')
context = load_example('context')
memory = load_example('memory')
tools = load_example('tools-skills')


class HarnessCase(unittest.TestCase):
    def run_demo(self, module, names):
        from contextlib import ExitStack
        from socket import socket
        called = {name: 0 for name in names}

        def observe(name):
            real = getattr(module, name)

            def invoke(*args, **kwargs):
                called[name] += 1
                return real(*args, **kwargs)
            return invoke

        with ExitStack() as stack:
            for name in names:
                stack.enter_context(patch.object(module, name, wraps=observe(name)))
            stack.enter_context(patch.object(socket, 'connect', side_effect=AssertionError('禁止联网')))
            result = module.demo()
        self.assertTrue(all(n > 0 for n in called.values()))
        return result


class AgentLoopTests(HarnessCase):
    def test_timeout_requires_lookup_then_business_acceptance(self):
        state, states = 'ready', ['ready']
        for event in ('dispatch', 'timeout', 'found', 'accepted'):
            state = loop.transition(state, event)
            states.append(state)
        self.assertEqual(states, ['ready', 'pending', 'unknown', 'verifying', 'done'])

    def test_rejection_absence_and_mismatch_return_to_ready(self):
        self.assertEqual(loop.transition('pending', 'ok'), 'verifying')
        for state, event in (('pending', 'rejected'), ('unknown', 'absent'), ('verifying', 'mismatch')):
            self.assertEqual(loop.transition(state, event), 'ready')

    def test_invalid_shortcuts_rejected_and_done_absorbs_duplicate_events(self):
        for state, event in (('unknown', 'dispatch'), ('pending', 'accepted'), ('ready', 'accepted'), ('invalid', 'dispatch')):
            with self.assertRaises(ValueError):
                loop.transition(state, event)
        for event in ('accepted', 'dispatch', 'timeout'):
            self.assertEqual(loop.transition('done', event), 'done')

    def test_budget_reservation_subtracts_each_unit_and_accepts_equality(self):
        self.assertEqual(loop.admit_budget((3, 100, 500), (1, 40, 100)), (True, (2, 60, 400)))
        self.assertEqual(loop.admit_budget((1, 40, 100), (1, 40, 100)), (True, (0, 0, 0)))
        remaining = (3, 0, 0)
        for step in range(3):
            accepted, remaining = loop.admit_budget(remaining, (1, 0, 0))
            self.assertTrue(accepted)
            self.assertEqual(remaining[0], 2 - step)
        self.assertEqual(loop.admit_budget(remaining, (1, 0, 0)), (False, (0, 0, 0)))

    def test_each_exhausted_dimension_rejects_without_spending(self):
        budget = (2, 60, 400)
        for request in ((3, 0, 0), (1, 70, 0), (1, 0, 401)):
            self.assertEqual(loop.admit_budget(budget, request), (False, budget))

    def test_budget_rejects_zero_step_negative_and_wrong_dimensions(self):
        for remaining, reservation in (((1, 2), (1, 1, 1)), ((1, -1, 3), (1, 0, 0)),
                                       ((1, 2, 3), (0, 1, 1)), ((1, 2, 3), (1, 0.5, 1))):
            with self.assertRaises(ValueError):
                loop.admit_budget(remaining, reservation)

    def test_reconciliation_distinguishes_absence_pending_and_committed(self):
        self.assertEqual(loop.reconcile_outcome('a', '正文', {}), 'query')
        self.assertEqual(loop.reconcile_outcome('a', '正文', {}, True), 'dispatch')
        ledger = {'a': ('正文', 'pending')}
        self.assertEqual(loop.reconcile_outcome('a', '正文', ledger), 'wait')
        self.assertEqual(ledger, {'a': ('正文', 'pending')})
        self.assertEqual(loop.reconcile_outcome('a', '正文', {'a': ('正文', 'committed')}, True), 'verify')

    def test_reconciliation_conflict_and_invalid_ledger_state(self):
        self.assertEqual(loop.reconcile_outcome('a', '新正文', {'a': ('旧正文', 'committed')}, True), 'conflict')
        with self.assertRaises(ValueError):
            loop.reconcile_outcome('', '正文', {})
        with self.assertRaises(ValueError):
            loop.reconcile_outcome('a', '正文', {'a': ('正文', 'unknown')})

    def test_demo_runs_all_loop_functions(self):
        result = self.run_demo(loop, ('transition', 'admit_budget', 'reconcile_outcome'))
        self.assertEqual(result, {'states': ['ready', 'pending', 'unknown', 'verifying', 'done'],
                                  'budget': (True, (2, 60, 400)), 'recovery': 'verify'})


class ContextTests(HarnessCase):
    def test_mandatory_context_and_combination_outperform_single_item(self):
        items = [('goal', 2, 0, True), ('a', 4, 6, False), ('b', 3, 5, False), ('c', 3, 5, False)]
        before = copy.deepcopy(items)
        self.assertEqual(context.select_context(items, 8), ['goal', 'b', 'c'])
        self.assertEqual(items, before)

    def test_small_optima_match_exhaustive_subset_oracle(self):
        items = [('goal', 2, 0, True), ('a', 4, 6, False), ('b', 3, 5, False),
                 ('c', 3, 5, False), ('d', 2, 3, False)]
        by_id = {row[0]: row for row in items}
        for budget in range(2, 15):
            feasible = []
            for bits in itertools.product((False, True), repeat=4):
                subset = [items[0]] + [row for row, selected in zip(items[1:], bits) if selected]
                cost = sum(row[1] for row in subset)
                if cost <= budget:
                    feasible.append((sum(row[2] for row in subset), -cost))
            chosen = context.select_context(items, budget)
            self.assertEqual(len(chosen), len(set(chosen)))
            self.assertIn('goal', chosen)
            score_cost = (sum(by_id[name][2] for name in chosen), -sum(by_id[name][1] for name in chosen))
            self.assertEqual(score_cost, max(feasible))

    def test_equal_value_prefers_low_cost_and_equal_cost_keeps_first(self):
        self.assertEqual(context.select_context([('costly', 3, 5, False), ('cheap', 2, 5, False)], 3), ['cheap'])
        self.assertEqual(context.select_context([('first', 2, 5, False), ('later', 2, 5, False)], 2), ['first'])
        self.assertEqual(context.select_context([('only', 2, 3, False)], 4), ['only'])
        self.assertEqual(context.select_context([], 0), [])

    def test_invalid_or_unaffordable_necessary_context_is_rejected(self):
        for items, budget in (([('must', 3, 0, True)], 2), ([('a', 0, 1, False)], 3),
                               ([('a', 1, 1, False), ('a', 1, 2, False)], 3),
                               ([('a', 1, -1, False)], 3), ([('a', 1, 1, 'yes')], 3)):
            with self.assertRaises(ValueError):
                context.select_context(items, budget)

    def test_trim_uses_complete_recent_suffix_without_skipping_newest(self):
        old = [{'kind': 'call', 'id': 'a', 'tokens': 2}, {'kind': 'result', 'id': 'a', 'tokens': 2}]
        recent = [{'kind': 'text', 'tokens': 1}, {'kind': 'call', 'id': 'b', 'tokens': 2},
                  {'kind': 'result', 'id': 'b', 'tokens': 2}]
        turns = [old, recent]
        before = copy.deepcopy(turns)
        trimmed = context.trim_complete_turns(turns, 6)
        self.assertEqual(trimmed, [recent])
        self.assertEqual(context.trim_complete_turns(turns, 4), [])
        self.assertEqual(context.trim_complete_turns(turns, 9), turns)
        self.assertIsNot(trimmed[0], recent)
        self.assertIs(trimmed[0][0], recent[0])  # 文档明确消息为共享只读视图。
        self.assertEqual(turns, before)

    def test_multiple_calls_can_complete_out_of_order_within_turn(self):
        turn = [{'kind': kind, 'id': key, 'tokens': 1}
                for kind, key in [('call', 'a'), ('call', 'b'), ('result', 'b'), ('result', 'a')]]
        self.assertEqual(context.trim_complete_turns([turn], 4), [turn])
        self.assertEqual(context.trim_complete_turns([], 0), [])

    def test_trim_rejects_orphan_duplicate_and_unfinished_calls(self):
        invalids = [
            [('result', 'a')], [('call', 'a')], [('call', 'a'), ('call', 'a')],
            [('call', 'a'), ('result', 'a'), ('result', 'a')], [('other', 'a')],
        ]
        for events in invalids:
            turn = [{'kind': kind, 'id': key, 'tokens': 1} for kind, key in events]
            with self.assertRaises(ValueError):
                context.trim_complete_turns([turn], 0)
        with self.assertRaises(ValueError):
            context.trim_complete_turns([[{'kind': 'text', 'tokens': -1}]], 3)

    def test_call_result_must_close_within_same_turn(self):
        with self.assertRaises(ValueError):
            context.trim_complete_turns([[{'kind': 'call', 'id': 'a', 'tokens': 1}],
                                         [{'kind': 'result', 'id': 'a', 'tokens': 1}]], 3)

    def test_checkpoint_audit_distinguishes_missing_changed_and_extra_fields(self):
        required = {'z': 'keep', 'b': 'old', 'a': 'missing'}
        summary = {'z': 'keep', 'b': 'new', 'extra': 'not-scored'}
        self.assertEqual(context.audit_checkpoint(required, summary), {
            'missing': ['a'], 'changed': ['b'], 'retention': 1 / 3,
        })
        self.assertEqual(context.audit_checkpoint({}, summary), {'missing': [], 'changed': [], 'retention': None})
        self.assertEqual(context.audit_checkpoint({'x': '1'}, {'x': '1', 'hallucination': '2'})['retention'], 1)

    def test_demo_runs_selection_and_audit(self):
        result = self.run_demo(context, ('select_context', 'audit_checkpoint'))
        self.assertEqual(result, {'chosen': ['goal', 'b', 'c'],
                                 'audit': {'missing': ['rule'], 'changed': ['target'], 'retention': 0}})


class MemoryTests(HarnessCase):
    def setUp(self):
        self.base = {'id': 'good', 'namespace': ['project', 'x'], 'version': 'v2',
                     'active': True, 'source': 'source-v2', 'expires_at': 10}

    def test_each_eligibility_dimension_is_a_hard_filter(self):
        rows = [self.base]
        changes = [{'namespace': ['project']}, {'namespace': ['project', 'y']}, {'version': 'v1'},
                   {'active': False}, {'active': 'true'}, {'active': 1}, {'source': ''}, {'expires_at': 9}]
        rows += [dict(self.base, id=str(i), **change) for i, change in enumerate(changes)]
        before = copy.deepcopy(rows)
        self.assertEqual(memory.eligible_memories(rows, ('project', 'x'), 'v2', 9), ['good'])
        self.assertEqual(rows, before)

    def test_expiry_boundary_permanent_memory_sorted_and_deduplicated(self):
        rows = [self.base, dict(self.base, id='z', expires_at=None), dict(self.base, id='a', expires_at=None)]
        rows.append(dict(rows[-1]))
        self.assertEqual(memory.eligible_memories(rows, ('project', 'x'), 'v2', 10), ['a', 'z'])
        self.assertEqual(memory.eligible_memories([self.base], ('project', 'x'), 'v2', 9.999), ['good'])

    def test_eligibility_rejects_nonfinite_time(self):
        with self.assertRaises(ValueError):
            memory.eligible_memories([self.base], ('project', 'x'), 'v2', float('nan'))
        with self.assertRaises(ValueError):
            memory.eligible_memories([dict(self.base, expires_at=float('inf'))], ('project', 'x'), 'v2', 1)

    def test_freshness_half_lives_monotonicity_and_zero_relevance(self):
        self.assertEqual([memory.freshness_score(0.8, age, 30) for age in (0, 30, 60)], [0.8, 0.4, 0.2])
        values = [memory.freshness_score(0.8, age, 10) for age in (0, 1, 3, 10, 100)]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertTrue(all(0 <= value <= 0.8 for value in values))
        self.assertEqual(memory.freshness_score(0, 100, 1), 0)

    def test_invalid_freshness_domains_are_rejected(self):
        for args in ((-0.1, 0, 1), (1.1, 0, 1), (0.5, -1, 1), (0.5, 1, 0),
                     (0.5, float('inf'), 1), (float('nan'), 1, 1)):
            with self.assertRaises(ValueError):
                memory.freshness_score(*args)

    def test_invalidation_closure_propagates_any_parent_and_terminates_cycles(self):
        graph = {'note': {'source'}, 'index': {'note', 'cycle'}, 'cycle': {'index'},
                 'answer': {'index', 'other'}, 'unrelated': {'safe'}}
        seeds = {'source'}
        before = copy.deepcopy((seeds, graph))
        invalid = memory.invalidation_closure(seeds, graph)
        self.assertEqual(invalid, {'source', 'note', 'index', 'cycle', 'answer'})
        self.assertEqual(memory.invalidation_closure(invalid, graph), invalid)
        self.assertEqual((seeds, graph), before)
        self.assertTrue(invalid <= memory.invalidation_closure({'source', 'safe'}, graph))

    def test_invalidation_direction_and_empty_seed(self):
        graph = {'note': {'source'}, 'answer': {'note'}}
        self.assertEqual(memory.invalidation_closure({'note'}, graph), {'note', 'answer'})
        self.assertEqual(memory.invalidation_closure(set(), graph), set())
        self.assertEqual(memory.invalidation_closure({'unknown'}, graph), {'unknown'})

    def test_demo_runs_decay_and_closure(self):
        result = self.run_demo(memory, ('freshness_score', 'invalidation_closure'))
        self.assertEqual(result, {'score_now': 0.8, 'score_later': 0.4,
                                 'invalid': ['answer', 'index', 'note', 'source']})


class ToolSkillTests(HarnessCase):
    def test_query_valid_days_boundaries_and_semantic_city(self):
        for days in (1, 7):
            self.assertEqual(tools.validate_query({'city': '北京', 'days': days}, {'北京'}), (True, 'accepted'))
        self.assertEqual(tools.validate_query({'city': '朝阳', 'days': 3}, {'北京'}), (False, 'semantic_city'))

    def test_query_distinguishes_fields_types_and_ranges(self):
        for args in ({'city': '北京'}, {'city': '北京', 'days': 1, 'extra': 1}, None):
            self.assertEqual(tools.validate_query(args, {'北京'}), (False, 'schema_fields'))
        for args in ({'city': '北京', 'days': True}, {'city': '北京', 'days': 1.0}, {'city': 1, 'days': 1}):
            self.assertEqual(tools.validate_query(args, {'北京'}), (False, 'schema_types'))
        for days in (0, 8):
            self.assertEqual(tools.validate_query({'city': '北京', 'days': days}, {'北京'}), (False, 'schema_range'))

    def test_timeout_and_mismatched_response_are_distinct(self):
        self.assertEqual(tools.classify_response(None, 'r'), 'unknown')
        self.assertEqual(tools.classify_response({'jsonrpc': '1.0', 'id': 'r'}, 'r'), 'protocol_mismatch')
        self.assertEqual(tools.classify_response({'jsonrpc': '2.0', 'id': 'other'}, 'r'), 'protocol_mismatch')

    def test_response_requires_exactly_one_error_or_result(self):
        for fields in ({}, {'error': {'code': -1}, 'result': {}}):
            self.assertEqual(tools.classify_response(dict(jsonrpc='2.0', id='r', **fields), 'r'), 'malformed')

    def test_protocol_error_and_malformed_error_codes(self):
        self.assertEqual(tools.classify_response({'jsonrpc': '2.0', 'id': 'r', 'error': {'code': -32602}}, 'r'), 'protocol_error')
        for error in (None, {}, {'code': True}, {'code': 'bad'}):
            self.assertEqual(tools.classify_response({'jsonrpc': '2.0', 'id': 'r', 'error': error}, 'r'), 'malformed')

    def test_tool_error_takes_precedence_over_structured_output(self):
        self.assertEqual(tools.classify_response({'jsonrpc': '2.0', 'id': 'r', 'result': {'isError': True}}, 'r'), 'tool_error')
        for result in (None, [], {'isError': 1}):
            self.assertEqual(tools.classify_response({'jsonrpc': '2.0', 'id': 'r', 'result': result}, 'r'), 'malformed')

    def test_count_schema_validity_still_requires_business_verification(self):
        for count in (0, 2):
            response = {'jsonrpc': '2.0', 'id': 'r', 'result': {'structuredContent': {'count': count}}}
            self.assertEqual(tools.classify_response(response, 'r'), 'verify_business')
        for data in (None, {}, {'count': -1}, {'count': True}, {'count': 1.0}):
            self.assertEqual(tools.classify_response({'jsonrpc': '2.0', 'id': 'r', 'result': {'structuredContent': data}}, 'r'), 'output_schema_error')

    def test_load_budget_includes_metadata_but_only_active_body_and_requested_resource(self):
        args = ({'a': 10, 'b': 10}, {'a': 50, 'b': 80}, {'a'}, {'ref': ('a', 30), 'unused': ('a', 1000)}, {'ref'})
        before = copy.deepcopy(args)
        self.assertEqual(tools.skill_load_plan(*args, 100), {'accepted': True, 'tokens': 100, 'bodies': ['a'], 'resources': ['ref']})
        self.assertEqual(tools.skill_load_plan(*args, 99), {'accepted': False, 'tokens': 100, 'bodies': ['a'], 'resources': ['ref']})
        self.assertEqual(args, before)

    def test_load_plan_empty_activation_and_sorted_identities(self):
        self.assertEqual(tools.skill_load_plan({'a': 10, 'b': 10}, {'a': 50}, set(), {}, set(), 20),
                         {'accepted': True, 'tokens': 20, 'bodies': [], 'resources': []})
        result = tools.skill_load_plan({'z': 1, 'a': 1}, {'z': 2, 'a': 3}, {'z', 'a'},
                                       {'y': ('z', 4), 'x': ('a', 5)}, {'y', 'x'}, 16)
        self.assertEqual(result, {'accepted': True, 'tokens': 16, 'bodies': ['a', 'z'], 'resources': ['x', 'y']})

    def test_load_rejects_missing_activation_resource_or_owner(self):
        cases = [({}, {'a': 1}, {'a'}, {}, set()), ({'a': 1}, {}, {'a'}, {}, set()),
                 ({'a': 1}, {'a': 1}, {'a'}, {}, {'missing'}),
                 ({'a': 1, 'b': 1}, {'a': 1}, {'a'}, {'r': ('b', 1)}, {'r'})]
        for args in cases:
            with self.assertRaises(ValueError):
                tools.skill_load_plan(*args, 100)
        with self.assertRaises(ValueError):
            tools.skill_load_plan({'a': -1}, {}, set(), {}, set(), 100)

    def test_demo_runs_parameter_response_and_loading_functions(self):
        result = self.run_demo(tools, ('validate_query', 'classify_response', 'skill_load_plan'))
        self.assertEqual(result, {'query': (False, 'schema_types'), 'response': 'verify_business',
                                 'loading': {'accepted': True, 'tokens': 100, 'bodies': ['a'], 'resources': ['ref']}})

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_agent_loop_cli(self):
        assert_cli_matches_demo(self, 'examples/harness/agent-loop.py')

    def test_agent_loop_quiet_import(self):
        assert_quiet_import(self, 'examples/harness/agent-loop.py')

    def test_context_cli(self):
        assert_cli_matches_demo(self, 'examples/harness/context.py')

    def test_context_quiet_import(self):
        assert_quiet_import(self, 'examples/harness/context.py')

    def test_memory_cli(self):
        assert_cli_matches_demo(self, 'examples/harness/memory.py')

    def test_memory_quiet_import(self):
        assert_quiet_import(self, 'examples/harness/memory.py')

    def test_tools_skills_cli(self):
        assert_cli_matches_demo(self, 'examples/harness/tools-skills.py')

    def test_tools_skills_quiet_import(self):
        assert_quiet_import(self, 'examples/harness/tools-skills.py')
