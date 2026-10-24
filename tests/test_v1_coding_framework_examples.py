"""三种开源编程方案的本库教学契约；不运行真实框架、shell、Git或模型。"""
import copy
import importlib.util
import itertools
from pathlib import Path
import unittest
from unittest.mock import patch


def load_example(name):
    p = Path(__file__).resolve().parents[1] / 'examples/agents' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


openhands = load_example('openhands')
swe = load_example('swe-agent')
aider = load_example('aider')


class OpenHandsTeachingTests(unittest.TestCase):
    def test_conversation_selects_parent_branch_and_deepcopies_events(self):
        events = [{'id': 'new', 'parent_id': 'a', 'data': {'value': 1}},
                  {'id': 'old', 'parent_id': 'a'}, {'id': 'a', 'parent_id': 'root'},
                  {'id': 'root', 'parent_id': None}]
        before = copy.deepcopy(events)
        path = openhands.conversation_path(events, 'new')
        self.assertEqual([x['id'] for x in path], ['root', 'a', 'new'])
        self.assertEqual([x['id'] for x in openhands.conversation_path(events, 'old')], ['root', 'a', 'old'])
        self.assertEqual(openhands.conversation_path(events, 'root'), [events[-1]])
        self.assertEqual(openhands.conversation_path(events, None), [])
        path[-1]['data']['value'] = 9
        self.assertEqual(events, before)

    def test_conversation_rejects_duplicate_missing_and_cyclic_parent_chain(self):
        with self.assertRaises(ValueError):
            openhands.conversation_path([{'id': 'a'}, {'id': 'a'}], 'a')
        with self.assertRaises(KeyError):
            openhands.conversation_path([{'id': 'a', 'parent_id': 'missing'}], 'a')
        with self.assertRaises(ValueError):
            openhands.conversation_path([{'id': 'a', 'parent_id': 'b'}, {'id': 'b', 'parent_id': 'a'}], 'a')

    def test_action_projection_combines_only_contiguous_matching_responses(self):
        action = lambda identity, response, text='': {'id': identity, 'kind': 'action',
            'llm_response_id': response, 'tool_call_id': 'call-' + identity, 'text': text}
        message = {'kind': 'user', 'data': {'text': '继续'}}
        events = [action('a', 'r1', '共享文本'), action('b', 'r1'), message,
                  action('c', 'r1', '第二批'), action('d', 'r2', '第三批')]
        before = copy.deepcopy(events)
        messages = openhands.project_action_batches(events)
        self.assertEqual(messages[0], {'role': 'assistant', 'text': '共享文本',
                                      'action_ids': ['a', 'b'], 'tool_call_ids': ['call-a', 'call-b']})
        self.assertEqual(len(messages), 4)
        self.assertEqual(sum(len(m.get('tool_call_ids', [])) for m in messages), 4)
        self.assertEqual([m['text'] for m in messages if m.get('role') == 'assistant'], ['共享文本', '第二批', '第三批'])
        messages[1]['data']['text'] = '变更副本'
        self.assertEqual(events, before)

    def test_action_projection_rejects_duplicate_shared_text_and_call_ids(self):
        first = {'id': 'a', 'kind': 'action', 'llm_response_id': 'r', 'tool_call_id': 'c1', 'text': '共享'}
        second = dict(first, id='b', tool_call_id='c2')
        with self.assertRaises(ValueError):
            openhands.project_action_batches([first, second])
        with self.assertRaises(ValueError):
            openhands.project_action_batches([first, dict(second, tool_call_id='c1', text='')])

    def test_observations_can_arrive_out_of_order_and_leave_pending(self):
        actions = [{'id': x, 'tool_call_id': 'c-' + x, 'tool_name': 'read'} for x in ('a', 'b', 'c')]
        observations = [{'action_id': x, 'tool_call_id': 'c-' + x, 'tool_name': 'read'} for x in ('b', 'a')]
        self.assertEqual(openhands.observation_links(actions, observations), {'observed': ['a', 'b'], 'pending': ['c']})
        self.assertEqual(openhands.observation_links(actions, []), {'observed': [], 'pending': ['a', 'b', 'c']})

    def test_observation_identity_constraints_and_duplicate_results(self):
        action = {'id': 'a', 'tool_call_id': 'c1', 'tool_name': 'read'}
        observation = {'action_id': 'a', 'tool_call_id': 'c1', 'tool_name': 'read'}
        for change in ({'action_id': 'missing'}, {'tool_call_id': 'wrong'}, {'tool_name': 'write'}):
            with self.assertRaises(ValueError):
                openhands.observation_links([action], [dict(observation, **change)])
        with self.assertRaises(ValueError):
            openhands.observation_links([action], [observation, observation])
        with self.assertRaises(ValueError):
            openhands.observation_links([action, dict(action, id='b')], [])

    def test_openhands_demo(self):
        result = openhands.demo()
        self.assertEqual([x['id'] for x in result['branch']], ['root', 'a', 'new'])
        self.assertEqual(result['messages'][0]['tool_call_ids'], ['cx', 'cy'])
        self.assertEqual(result['links'], {'observed': ['y'], 'pending': ['x']})


class SweAgentTeachingTests(unittest.TestCase):
    def test_window_tail_empty_file_and_line_count_conservation(self):
        self.assertEqual(swe.file_window('a\nb\nc\nd\ne\nf', 6, 3),
                         {'lines': [(4, 'd'), (5, 'e'), (6, 'f')], 'above': 3, 'below': 0, 'total': 6})
        self.assertEqual(swe.file_window(''), {'lines': [], 'above': 0, 'below': 0, 'total': 0})
        for start, size in ((1, 2), (3, 2), (20, 2), (1, 20)):
            result = swe.file_window('a\nb\nc\nd\ne\nf', start, size)
            self.assertEqual(result['above'] + len(result['lines']) + result['below'], 6)
            self.assertLessEqual(len(result['lines']), size)
            self.assertEqual([i for i, _ in result['lines']], list(range(result['above'] + 1, 7 - result['below'])))

    def test_unique_edit_zero_one_many_and_unchanged(self):
        text = 'x = 1\ny = 1'
        for old, new, status in (('missing', '2', 'missing'), ('1', '2', 'ambiguous'), ('x = 1', 'x = 1', 'unchanged')):
            result = swe.unique_edit(text, old, new)
            self.assertEqual(result['status'], status)
            self.assertEqual(result['text'], text)
            self.assertTrue(result['feedback'])
        edited = swe.unique_edit(text, 'x = 1', 'x = 2')
        self.assertEqual(edited['text'], 'x = 2\ny = 1')
        self.assertEqual(edited['status'], 'edited')
        with self.assertRaises(ValueError):
            swe.unique_edit(text, '', 'new')

    def test_retry_format_limit_stops_before_consuming_extra_attempt(self):
        def attempts():
            yield {'kind': 'format_error'}
            yield {'kind': 'blocked_action'}
            raise AssertionError('已达到预算，不能读取第三条')
        result = swe.retry_trace(attempts(), max_format_failures=2)
        self.assertEqual(result['status'], 'exit_format')
        self.assertEqual(result['format_failures'], 2)
        self.assertEqual(len(result['trace']), 2)
        self.assertIs(result['executed'], False)

    def test_retry_budget_exit_and_insufficient_input_are_distinct(self):
        budget = swe.retry_trace([{'kind': 'bash_syntax_error'}, {'kind': 'budget_error'}, {'kind': 'ok'}])
        self.assertEqual(budget['status'], 'exit_budget')
        self.assertEqual(budget['format_failures'], 1)
        self.assertEqual(len(budget['trace']), 2)
        self.assertEqual(swe.retry_trace([]), {'trace': [], 'format_failures': 0, 'status': 'needs_attempt', 'executed': False})
        self.assertEqual(swe.retry_trace([{'kind': 'format_error'}])['status'], 'needs_attempt')

    def test_retry_deepcopies_query_and_never_runs_action_text(self):
        attempts = [{'kind': 'format_error', 'query': [{'content': 'original'}]},
                    {'kind': 'ok', 'action': 'not-a-real-command', 'query': [{'content': 'corrected'}]}]
        before = copy.deepcopy(attempts)
        with patch('os.system', side_effect=AssertionError('禁止shell')) as system, \
             patch('subprocess.run', side_effect=AssertionError('禁止进程')) as run:
            result = swe.retry_trace(attempts)
        self.assertEqual(result['status'], 'step_complete')
        self.assertIs(result['executed'], True)  # 仅表示合成记录报告正常结果。
        result['trace'][0]['query'][0]['content'] = 'mutated'
        self.assertEqual(attempts, before)
        system.assert_not_called()
        run.assert_not_called()

    def test_swe_explicit_parameter_errors_and_demo(self):
        with self.assertRaises(ValueError):
            swe.file_window('a', 0, 1)
        with self.assertRaises(ValueError):
            swe.retry_trace([], 0)
        with self.assertRaises(ValueError):
            swe.retry_trace([{'kind': 'other'}])
        result = swe.demo()
        self.assertEqual(result['window']['above'], 3)
        self.assertEqual(result['edit']['status'], 'ambiguous')
        self.assertEqual(result['trace']['format_failures'], 1)


class AiderTeachingTests(unittest.TestCase):
    def test_two_node_dangling_pagerank_matches_stationary_solution(self):
        result = aider.repo_map(['A', 'B'], [('A', 'B', 'f', 1)], {'A': 7}, {('B', 'f'): 2}, 3, iterations=200)
        self.assertAlmostEqual(result['file_rank']['A'], 20 / 37, places=12)
        self.assertAlmostEqual(result['file_rank']['B'], 17 / 37, places=12)
        self.assertAlmostEqual(sum(result['file_rank'].values()), 1)
        self.assertTrue(all(value >= 0 for value in result['file_rank'].values()))
        self.assertAlmostEqual(result['symbol_rank'][0][1], 20 / 37, places=12)
        self.assertEqual(result['selected'], [('B', 'f')])
        self.assertEqual(result['remaining_tokens'], 1)
        self.assertLess(result['residual_l1'], 1e-12)

    def test_all_dangling_nodes_preserve_normalized_personalization(self):
        result = aider.repo_map(['A', 'B'], [], {'A': 1, 'B': 3}, {}, 9)
        self.assertEqual(result['file_rank'], {'A': 0.25, 'B': 0.75})
        self.assertEqual(result['selected'], [])
        self.assertEqual(result['remaining_tokens'], 9)

    def test_symbol_contributions_and_budget_prefix_are_independent_of_file_rank(self):
        edges = [('A', 'B', 'parse', 2), ('A', 'B', 'read', 1), ('B', 'B', 'self', 1)]
        costs = {('B', 'self'): 4, ('B', 'parse'): 1, ('B', 'read'): 1}
        result = aider.repo_map(['A', 'B'], edges, {'A': 1}, costs, 5)
        scores = dict(result['symbol_rank'])
        self.assertAlmostEqual(scores[('B', 'self')], 0.85)
        self.assertAlmostEqual(scores[('B', 'parse')], 0.1)
        self.assertAlmostEqual(scores[('B', 'read')], 0.05)
        self.assertEqual(result['selected'], [('B', 'self'), ('B', 'parse')])
        self.assertEqual(result['remaining_tokens'], 0)
        blocked = aider.repo_map(['A', 'B'], edges, {'A': 1}, costs, 3)
        self.assertEqual(blocked['selected'], [])
        self.assertEqual(blocked['remaining_tokens'], 3)

    def test_repo_map_rejects_invalid_graph_prior_and_edge_weights(self):
        for prior in ({'A': 0}, {'missing': 1}, {'A': -1}):
            with self.assertRaises(ValueError):
                aider.repo_map(['A'], [], prior, {}, 1)
        with self.assertRaises(ValueError):
            aider.repo_map(['A'], [('A', 'B', 'f', 1)], {'A': 1}, {}, 1)
        with self.assertRaises(ValueError):
            aider.repo_map(['A'], [('A', 'A', 'f', 0)], {'A': 1}, {('A', 'f'): 1}, 1)

    def test_search_replace_changes_first_exact_and_reports_duplicates(self):
        text = 'x = 1\nx = 1\n'
        self.assertEqual(aider.search_replace(text, 'x = 1\n', 'x = 2\n'),
                         {'text': 'x = 2\nx = 1\n', 'mode': 'exact', 'match_count': 2, 'start_line': 1})
        exact = aider.search_replace('    x = 1\nx = 1\n', 'x = 1\n', 'x = 2\n')
        self.assertEqual(exact['start_line'], 2)
        self.assertEqual(exact['mode'], 'exact')
        self.assertEqual(text, 'x = 1\nx = 1\n')

    def test_uniform_indent_restored_but_nonuniform_indent_not_matched(self):
        text = 'def f():\n    x = 1\n    y = 2\n'
        result = aider.search_replace(text, 'x = 1\ny = 2\n', 'x = 3\ny = 4\n')
        self.assertEqual(result, {'text': 'def f():\n    x = 3\n    y = 4\n',
                                  'mode': 'indent', 'match_count': None, 'start_line': 2})
        uneven = '    x = 1\n      y = 2\n'
        self.assertEqual(aider.search_replace(uneven, 'x = 1\ny = 2\n', 'z = 3\n'),
                         {'text': uneven, 'mode': 'no_match', 'match_count': 0, 'start_line': None})
        with self.assertRaises(ValueError):
            aider.search_replace(text, '  \n', 'new')

    def test_commit_flags_preserve_file_intersection_and_unrelated_dirty(self):
        dirty, edited = {'app.py', 'notes.md'}, {'app.py', 'new.py'}
        before = copy.deepcopy((dirty, edited))
        for auto, checkpoints, git, dry in itertools.product((False, True), repeat=4):
            active = (auto, git, dry) == (True, True, False)
            result = aider.commit_plan(dirty, edited, auto, checkpoints, git, dry)
            self.assertEqual(result['before_edit'], ['app.py'] if active and checkpoints else [])
            self.assertEqual(result['after_edit'], ['app.py', 'new.py'] if active else [])
            self.assertEqual(result['unrelated_dirty'], ['notes.md'])
            self.assertEqual(result['overlap_without_checkpoint'], [] if active and checkpoints else ['app.py'])
            self.assertIs(result['executes_git'], False)
        self.assertEqual((dirty, edited), before)

    def test_aider_demo(self):
        result = aider.demo()
        self.assertAlmostEqual(sum(result['map']['file_rank'].values()), 1)
        self.assertEqual(result['map']['selected'], [('lib.py', 'parse')])
        self.assertEqual(result['edit']['text'], '    x = 2\n')
        self.assertEqual(result['git']['before_edit'], ['app.py'])
        self.assertEqual(result['git']['unrelated_dirty'], ['notes.md'])

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_openhands_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/openhands.py')

    def test_openhands_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/openhands.py')

    def test_swe_agent_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/swe-agent.py')

    def test_swe_agent_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/swe-agent.py')

    def test_aider_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/aider.py')

    def test_aider_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/aider.py')
