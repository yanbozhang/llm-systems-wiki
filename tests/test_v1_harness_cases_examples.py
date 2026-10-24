"""依据四篇专题的公式和状态契约验证本库教学实现；不运行真实客户端或框架。"""
import copy
import importlib.util
import itertools
from pathlib import Path
import unittest


def load_example(relative):
    path = Path(__file__).resolve().parents[1] / 'examples' / relative
    spec = importlib.util.spec_from_file_location('teaching_' + path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


codex = load_example('agents/codex-cli.py')
claude = load_example('agents/claude-code.py')
graph = load_example('harness/langgraph.py')
team = load_example('harness/autogen.py')


class CodexCliTeachingTests(unittest.TestCase):
    def test_launch_preserves_override_order_and_separates_entry_paths(self):
        root = [('model', 'root-model'), ('format', 'text')]
        sub = [('model', 'sub-model'), ('format', 'json')]
        before = copy.deepcopy((root, sub))
        result = codex.launch_plan('exec', root, sub)
        self.assertEqual(result['overrides'], [('model', 'root-model'), ('format', 'text'),
                                              ('model', 'sub-model'), ('format', 'json')])
        self.assertEqual(result['path'], ['cli_main', 'run_main', 'run_exec_session',
                                          'InProcessAppServerClient', 'turn/start'])
        interactive = codex.launch_plan('interactive', [], [], remote=True)
        self.assertEqual(interactive['path'], ['cli_main', 'run_interactive_tui'])
        self.assertEqual(interactive['overrides'], [])
        result['overrides'].append(('extra', 'only-in-copy'))
        result['path'].clear()
        self.assertEqual((root, sub), before)
        self.assertEqual(codex.launch_plan('exec', [], [])['path'][0], 'cli_main')

    def test_launch_rejects_exec_remote_and_undeclared_entry_values(self):
        for mode, remote in [('exec', True), ('other', False), ('interactive', 1)]:
            with self.assertRaises(ValueError):
                codex.launch_plan(mode, [], [], remote)

    def test_route_ordinary_unknown_and_payload_mismatch_have_distinct_results(self):
        registry = {'echo': ('function', 'skip')}
        self.assertIsNone(codex.route_call({'type': 'message', 'text': 'echo'}, registry))
        unknown = {'type': 'function_call', 'call_id': 'request-2', 'name': 'absent'}
        mismatch = {'type': 'custom_tool_call', 'call_id': 'request-3', 'name': 'echo'}
        before = copy.deepcopy((unknown, mismatch, registry))
        self.assertEqual(codex.route_call(unknown, registry),
                         {'status': 'respond_to_model', 'call_id': 'request-2'})
        self.assertEqual(codex.route_call(mismatch, registry),
                         {'status': 'fatal_payload', 'call_id': 'request-3'})
        self.assertEqual((unknown, mismatch, registry), before)

    def test_route_admission_respects_forbidden_and_strict_review(self):
        # 表由正文准入规则给出，禁止优先；skip仍受严格检查约束。
        cases = [('skip', False, False, 'ready_for_runtime'),
                 ('skip', False, True, 'await_approval'),
                 ('skip', True, True, 'ready_for_runtime'),
                 ('needs_approval', False, False, 'await_approval'),
                 ('needs_approval', True, False, 'ready_for_runtime'),
                 ('forbidden', False, False, 'rejected'),
                 ('forbidden', True, False, 'rejected'),
                 ('forbidden', True, True, 'rejected')]
        for item_type, kind in [('function_call', 'function'), ('custom_tool_call', 'custom')]:
            for requirement, approved, strict, expected in cases:
                result = codex.route_call({'type': item_type, 'name': 'echo', 'call_id': 'c-7'},
                                         {'echo': (kind, requirement)}, approved, strict)
                self.assertEqual(result, {'status': expected, 'call_id': 'c-7', 'kind': kind})

    def test_route_rejects_missing_identity_and_invalid_policy_flags(self):
        item = {'type': 'function_call', 'name': 'echo', 'call_id': 'c'}
        registry = {'echo': ('function', 'skip')}
        for field in ('name', 'call_id'):
            with self.assertRaises(ValueError):
                codex.route_call({k: v for k, v in item.items() if k != field}, registry)
        with self.assertRaises(ValueError):
            codex.route_call(item, {'echo': ('function', 'unknown-policy')})
        for approved, strict in [(1, False), (False, 1)]:
            with self.assertRaises(ValueError):
                codex.route_call(item, registry, approved, strict)

    def test_capture_hand_calculation_and_byte_units(self):
        self.assertEqual(codex.capture_output([b'abc', b'def'], 4, 1, 'exited'),
                         {'retained': b'abcd', 'consumed_bytes': 6, 'emitted_deltas': 1,
                          'truncated': True, 'terminal': 'exited'})
        result = codex.capture_output(['中文'.encode('utf-8')], 4, 2, 'exited')
        self.assertEqual(result['consumed_bytes'], 6)
        self.assertEqual(result['retained'], b'\xe4\xb8\xad\xe6')
        self.assertEqual(result['emitted_deltas'], 1)

    def test_capture_limits_empty_chunks_and_terminal_are_independent(self):
        chunks = [b'ab', b'', b'cd', b'ef']
        before = list(chunks)
        for cap, retained, truncated in [(0, b'', True), (4, b'abcd', True),
                                          (6, b'abcdef', False), (8, b'abcdef', False)]:
            for delta_cap, emitted in [(0, 0), (1, 1), (3, 3), (5, 3)]:
                for terminal in ('running', 'exited', 'timed_out', 'cancelled'):
                    result = codex.capture_output(chunks, cap, delta_cap, terminal)
                    self.assertEqual(result, {'retained': retained, 'consumed_bytes': 6,
                                             'emitted_deltas': emitted, 'truncated': truncated,
                                             'terminal': terminal})
        self.assertEqual(chunks, before)
        self.assertEqual(codex.capture_output([], 0, 0, 'running'),
                         {'retained': b'', 'consumed_bytes': 0, 'emitted_deltas': 0,
                          'truncated': False, 'terminal': 'running'})

    def test_capture_rejects_invalid_limits_chunks_and_terminal(self):
        for cap, events in [(-1, 1), (1, -1), (True, 1), (1, False), (1.5, 1)]:
            with self.assertRaises(ValueError):
                codex.capture_output([b'abc'], cap, events, 'exited')
        with self.assertRaises(ValueError):
            codex.capture_output(['abc'], 3, 1, 'exited')
        with self.assertRaises(ValueError):
            codex.capture_output([b'abc'], 3, 1, 'success')

    def test_codex_demo_retains_independent_launch_and_capture_results(self):
        result = codex.demo()
        self.assertEqual(result['launch']['path'][-2:], ['InProcessAppServerClient', 'turn/start'])
        self.assertEqual(result['capture'], {'retained': b'abcd', 'consumed_bytes': 6,
                                            'emitted_deltas': 1, 'truncated': True, 'terminal': 'exited'})


class ClaudeCodeTeachingTests(unittest.TestCase):
    def test_response_includes_first_result_without_consuming_tail(self):
        # 尾项故意无效：遇到首个result后不可再检查或收集它。
        events = [{'type': 'assistant', 'text': '已准备'}, {'type': 'tool', 'text': '反馈'},
                  {'type': 'result', 'is_error': True}, None]
        before = copy.deepcopy(events)
        result = claude.response_window(events)
        self.assertEqual(result['messages'], events[:3])
        self.assertTrue(result['response_complete'])
        self.assertIsNone(result['business_verified'])
        result['messages'][0]['text'] = '仅修改返回消息'
        self.assertEqual(events, before)

    def test_response_without_result_stays_incomplete_and_unverified(self):
        for events in ([], [{'type': 'assistant', 'text': 'result success 完成'}]):
            self.assertEqual(claude.response_window(events),
                             {'messages': events, 'response_complete': False, 'business_verified': None})
        result = claude.response_window([{'type': 'result', 'is_error': False}])
        self.assertTrue(result['response_complete'])
        self.assertIsNone(result['business_verified'])

    def test_response_rejects_missing_type_before_result(self):
        for event in ({}, None, 'result'):
            with self.assertRaises(ValueError):
                claude.response_window([event, {'type': 'result'}])

    def test_hook_allow_deny_and_abstention_preserve_control_request_identity(self):
        decisions = {'accept': 'allow', 'block': 'deny', 'neutral': None}
        before = dict(decisions)
        for callback, decision in [('accept', 'allow'), ('block', 'deny')]:
            result = claude.hook_reply('request-17', callback, decisions)
            self.assertEqual(result, {'type': 'control_response', 'response': {
                'subtype': 'success', 'request_id': 'request-17', 'response': {
                    'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision}}}})
        self.assertEqual(claude.hook_reply('request-18', 'neutral', decisions),
                         {'type': 'control_response', 'response': {
                             'subtype': 'success', 'request_id': 'request-18', 'response': {}}})
        self.assertEqual(decisions, before)

    def test_hook_unknown_callback_is_correlated_control_error(self):
        result = claude.hook_reply('request-19', 'missing', {'known': 'allow'})
        self.assertEqual(result['type'], 'control_response')
        self.assertEqual(result['response']['request_id'], 'request-19')
        self.assertEqual(result['response']['subtype'], 'error')
        self.assertIn('callback', result['response']['error'])

    def test_hook_rejects_missing_id_and_outside_decision_subset(self):
        for request, callback, decisions in [('', 'h', {'h': 'allow'}),
                                              ('r', '', {'h': 'allow'}),
                                              ('r', 'h', {'h': 'ask'})]:
            with self.assertRaises(ValueError):
                claude.hook_reply(request, callback, decisions)

    def test_sdk_tool_echoes_exact_integers_without_mutating_inputs(self):
        for value in (0, 3, -4, 10**20):
            arguments, registry = {'value': value}, {'echo': {'fail': False}}
            before = copy.deepcopy((arguments, registry))
            self.assertEqual(claude.sdk_tool_route('echo', arguments, registry),
                             {'isError': False, 'content': [{'type': 'text', 'text': str(value)}]})
            self.assertEqual((arguments, registry), before)

    def test_sdk_tool_returns_readable_errors_for_discovery_schema_and_handler(self):
        errors = []
        cases = [('missing', {'value': 1}, {'echo': {}}),
                 ('echo', {}, {'echo': {}}), ('echo', {'value': True}, {'echo': {}}),
                 ('echo', {'value': 1, 'extra': 2}, {'echo': {}}),
                 ('echo', {'value': '1'}, {'echo': {}}), ('echo', None, {'echo': {}}),
                 ('echo', {'value': 1.0}, {'echo': {}}),
                 ('echo', {'value': 3}, {'echo': {'fail': True}})]
        for name, arguments, registry in cases:
            result = claude.sdk_tool_route(name, arguments, registry)
            self.assertIs(result['isError'], True)
            self.assertEqual(len(result['content']), 1)
            self.assertEqual(result['content'][0]['type'], 'text')
            self.assertTrue(result['content'][0]['text'].strip())
            errors.append(result['content'][0]['text'])
        self.assertIn('unknown', errors[0])
        self.assertIn('fields', errors[1])
        self.assertIn('integer', errors[2])
        self.assertIn('handler', errors[-1])

    def test_claude_demo_keeps_response_control_and_tool_status_separate(self):
        result = claude.demo()
        self.assertEqual([m['type'] for m in result['response']['messages']], ['assistant', 'result'])
        self.assertIsNone(result['response']['business_verified'])
        self.assertEqual(result['hook']['response']['subtype'], 'success')
        self.assertEqual(result['hook']['response']['response']['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertIs(result['tool']['isError'], True)


class LangGraphTeachingTests(unittest.TestCase):
    def test_sum_superstep_is_permutation_invariant_and_preserves_unwritten_channels(self):
        state = {'total': 1, 'unchanged': -8}
        writes = [('b', 'total', 3), ('a', 'total', 2)]
        for ordering in itertools.permutations(writes):
            result = graph.merge_superstep(state, list(ordering), {'total': 'sum'})
            self.assertEqual(result, {'total': 6, 'unchanged': -8})
        self.assertEqual(state, {'total': 1, 'unchanged': -8})
        self.assertEqual(writes, [('b', 'total', 3), ('a', 'total', 2)])
        self.assertEqual(graph.merge_superstep({'total': 5}, [('a', 'total', -5)], {'total': 'sum'}), {'total': 0})

    def test_last_accepts_one_write_keeps_zero_writes_and_rejects_multiple(self):
        state = {'value': 4, 'idle': 9}
        self.assertEqual(graph.merge_superstep(state, [], {}), state)
        self.assertEqual(graph.merge_superstep(state, [('a', 'value', 7)], {}), {'value': 7, 'idle': 9})
        for values in ((2, 3), (2, 2)):
            with self.assertRaises(ValueError):
                graph.merge_superstep(state, [('a', 'value', values[0]), ('b', 'value', values[1])], {'value': 'last'})
        self.assertEqual(state, {'value': 4, 'idle': 9})

    def test_merge_rejects_noninteger_missing_channels_and_unknown_reducer(self):
        cases = [({'x': True}, [], {}), ({'x': 1}, [('a', 'x', 1.5)], {}),
                 ({'x': 1}, [('a', 'x', False)], {}), ({'x': 1}, [('a', 'missing', 2)], {}),
                 ({'x': 1}, [('a', 'x', 2)], {'x': 'concat'})]
        for state, writes, reducers in cases:
            before = copy.deepcopy((state, writes, reducers))
            with self.assertRaises(ValueError):
                graph.merge_superstep(state, writes, reducers)
            self.assertEqual((state, writes, reducers), before)

    def test_checkpoint_same_identity_keeps_first_write_and_appends_new_index(self):
        scope = ('thread', 'namespace', 'checkpoint')
        original = {}
        first = graph.checkpoint_writes(original, scope, 'task-a', [('x', 'old'), ('y', 'second')])
        expected = {('thread', 'namespace', 'checkpoint', 'task-a', 0): ('x', 'old'),
                    ('thread', 'namespace', 'checkpoint', 'task-a', 1): ('y', 'second')}
        self.assertEqual(first, expected)
        self.assertEqual(original, {})
        retry = graph.checkpoint_writes(first, scope, 'task-a', [('x', 'new'), ('y', 'changed'), ('z', 'third')])
        self.assertEqual(retry, {**expected, ('thread', 'namespace', 'checkpoint', 'task-a', 2): ('z', 'third')})
        self.assertEqual(first, expected)
        self.assertEqual(graph.checkpoint_writes(first, scope, 'task-a', [('x', 'old'), ('y', 'second')]), first)
        retry[('thread', 'namespace', 'checkpoint', 'task-a', 0)] = ('x', 'edited-copy')
        self.assertEqual(first, expected)

    def test_checkpoint_thread_namespace_checkpoint_and_task_are_separate_identity_dimensions(self):
        records = [ (('t', 'n', 'c'), 'a'), (('t2', 'n', 'c'), 'a'),
                    (('t', 'n2', 'c'), 'a'), (('t', 'n', 'c2'), 'a'), (('t', 'n', 'c'), 'b')]
        ledger = {}
        for index, (scope, task) in enumerate(records):
            ledger = graph.checkpoint_writes(ledger, scope, task, [('channel', str(index))])
        self.assertEqual(len(ledger), 5)
        for index, (scope, task) in enumerate(records):
            self.assertEqual(ledger[(*scope, task, 0)], ('channel', str(index)))
        self.assertEqual(graph.checkpoint_writes({}, ('t', '', 'c'), 'a', [('x', 'v')]),
                         {('t', '', 'c', 'a', 0): ('x', 'v')})

    def test_checkpoint_rejects_invalid_scope_identity_and_control_channels(self):
        for scope in [('t', 'c'), ('t', 1, 'c'), ('', 'n', 'c'), ('t', 'n', '')]:
            with self.assertRaises(ValueError):
                graph.checkpoint_writes({}, scope, 'task', [('x', 'v')])
        with self.assertRaises(ValueError):
            graph.checkpoint_writes({}, ('t', '', 'c'), '', [('x', 'v')])
        for channel in ('', '__resume'):
            with self.assertRaises(ValueError):
                graph.checkpoint_writes({}, ('t', '', 'c'), 'task', [(channel, 'v')])

    def test_interrupt_replays_prefix_and_advances_answers_without_repeating_effect(self):
        questions = ['批准吗', '保存到哪']
        original_ledger = {'earlier-action'}
        first = graph.replay_interrupt_node(questions, [], original_ledger, 'draft-1')
        self.assertEqual(first, {'prefix_reexecuted': True, 'new_effect': True,
                                'ledger': {'earlier-action', 'draft-1'}, 'consumed': [],
                                'interrupt': '批准吗', 'complete': False})
        answers = ['同意']
        second = graph.replay_interrupt_node(questions, answers, first['ledger'], 'draft-1')
        self.assertTrue(second['prefix_reexecuted'])
        self.assertFalse(second['new_effect'])
        self.assertEqual(second['consumed'], [('批准吗', '同意')])
        self.assertEqual(second['interrupt'], '保存到哪')
        self.assertFalse(second['complete'])
        final = graph.replay_interrupt_node(questions, ['同意', '草稿目录'], second['ledger'], 'draft-1')
        self.assertTrue(final['prefix_reexecuted'])
        self.assertFalse(final['new_effect'])
        self.assertEqual(final['consumed'], [('批准吗', '同意'), ('保存到哪', '草稿目录')])
        self.assertIsNone(final['interrupt'])
        self.assertTrue(final['complete'])
        self.assertEqual(final['ledger'], {'earlier-action', 'draft-1'})
        self.assertEqual(original_ledger, {'earlier-action'})
        self.assertEqual(questions, ['批准吗', '保存到哪'])
        self.assertEqual(answers, ['同意'])

    def test_interrupt_different_action_key_is_new_and_invalid_slots_are_rejected(self):
        result = graph.replay_interrupt_node(['q'], [], {'old'}, 'new')
        self.assertTrue(result['new_effect'])
        self.assertEqual(result['ledger'], {'old', 'new'})
        cases = [([], [], 'a'), (['q', 'q'], [], 'a'), ([''], [], 'a'),
                 (['q'], ['a', 'extra'], 'a'), (['q'], [], '')]
        for questions, answers, key in cases:
            with self.assertRaises(ValueError):
                graph.replay_interrupt_node(questions, answers, set(), key)

    def test_langgraph_demo_has_sum_six_and_first_interrupt(self):
        result = graph.demo()
        self.assertEqual(result['state'], {'total': 6})
        self.assertEqual(result['pause']['consumed'], [])
        self.assertEqual(result['pause']['interrupt'], 'approve')
        self.assertIs(result['pause']['complete'], False)
        self.assertIs(result['pause']['new_effect'], True)


class AutoGenTeachingTests(unittest.TestCase):
    def test_round_robin_two_cycles_and_single_participant(self):
        participants = ['critic', 'writer', 'planner']
        cursor, selected, cursors = 2, [], []
        for _ in range(6):
            speaker, cursor = team.select_round_robin(participants, cursor)
            selected.append(speaker)
            cursors.append(cursor)
        self.assertEqual(selected, ['planner', 'critic', 'writer', 'planner', 'critic', 'writer'])
        self.assertEqual(cursors, [0, 1, 2, 0, 1, 2])
        self.assertEqual(participants, ['critic', 'writer', 'planner'])
        self.assertEqual(team.select_round_robin(['solo'], 0), ('solo', 0))

    def test_round_robin_rejects_invalid_participants_and_cursor(self):
        for names in ([], ['a', 'a'], [''], [1]):
            with self.assertRaises(ValueError):
                team.select_round_robin(names, 0)
        for cursor in (-1, 2, True, 0.5):
            with self.assertRaises(ValueError):
                team.select_round_robin(['a', 'b'], cursor)

    def test_termination_accumulates_only_delta_and_hits_joint_threshold(self):
        first_delta = [{'kind': 'chat', 'source': 'writer', 'text': '草稿'},
                       {'kind': 'chat', 'source': 'critic', 'text': '继续'}]
        second_delta = [{'kind': 'chat', 'source': 'critic', 'text': 'APPROVE'}]
        before = copy.deepcopy((first_delta, second_delta))
        state, stopped = team.termination_step((0, False), first_delta, 3, 'APPROVE', 'critic', 'and')
        self.assertEqual((state, stopped), ((2, False), False))
        self.assertEqual(team.termination_step(state, second_delta, 3, 'APPROVE', 'critic', 'and'),
                         ((3, True), True))
        self.assertEqual((first_delta, second_delta), before)
        self.assertEqual(team.termination_step((1, False), [], 3, 'APPROVE', 'critic'), ((1, False), False))

    def test_termination_event_count_switch_is_independent_of_text_matching(self):
        delta = [{'kind': 'event', 'source': 'critic', 'text': 'APPROVE'},
                 {'kind': 'chat', 'source': 'writer', 'text': 'draft'}]
        self.assertEqual(team.termination_step((0, False), delta, 5, 'APPROVE', 'critic', 'and', False),
                         ((1, True), False))
        self.assertEqual(team.termination_step((0, False), delta, 5, 'APPROVE', 'critic', 'and', True),
                         ((2, True), False))

    def test_and_latches_conditions_satisfied_in_either_batch_order(self):
        chats = [{'kind': 'chat', 'source': 'writer', 'text': 'draft'}] * 2
        marker_event = [{'kind': 'event', 'source': 'critic', 'text': 'APPROVE'}]
        count_first, stop = team.termination_step((0, False), chats, 2, 'APPROVE', 'critic', 'and')
        self.assertEqual((count_first, stop), ((2, False), False))
        self.assertEqual(team.termination_step(count_first, chats + marker_event, 2, 'APPROVE', 'critic', 'and'),
                         ((2, True), True))
        hit_first, stop = team.termination_step((0, False), marker_event, 2, 'APPROVE', 'critic', 'and')
        self.assertEqual((hit_first, stop), ((0, True), False))
        self.assertEqual(team.termination_step(hit_first, chats, 2, 'APPROVE', 'critic', 'and'), ((2, True), True))

    def test_or_stops_for_either_condition_and_batch_count_can_overshoot(self):
        chats = [{'kind': 'chat', 'source': 'writer', 'text': 'draft'}] * 5
        self.assertEqual(team.termination_step((0, False), chats, 2, 'APPROVE', 'critic'), ((5, False), True))
        event = [{'kind': 'event', 'source': 'critic', 'text': 'APPROVE'}]
        self.assertEqual(team.termination_step((0, False), event, 9, 'APPROVE', 'critic'), ((0, True), True))
        self.assertEqual(team.termination_step((5, False), event, 2, 'APPROVE', 'critic', 'and'), ((5, True), True))

    def test_termination_source_filter_and_literal_substring_are_not_business_verification(self):
        wrong_source = [{'kind': 'chat', 'source': 'user', 'text': 'APPROVE'}]
        self.assertEqual(team.termination_step((0, False), wrong_source, 8, 'APPROVE', 'critic'), ((1, False), False))
        lower_case = [{'kind': 'chat', 'source': 'critic', 'text': 'approve'}]
        self.assertEqual(team.termination_step((0, False), lower_case, 8, 'APPROVE', 'critic'), ((1, False), False))
        negation = [{'kind': 'chat', 'source': 'critic', 'text': 'NOT APPROVE'}]
        self.assertEqual(team.termination_step((0, False), negation, 8, 'APPROVE', 'critic'), ((1, True), True))

    def test_terminated_condition_requires_reset_before_new_delta(self):
        for state, mode in [((2, False), 'or'), ((0, True), 'or'), ((2, True), 'and')]:
            with self.assertRaises(ValueError):
                team.termination_step(state, [], 2, 'APPROVE', 'critic', mode)
        self.assertEqual(team.termination_step((0, False), [], 2, 'APPROVE', 'critic'), ((0, False), False))

    def test_termination_rejects_declared_invalid_state_config_and_message_values(self):
        for state in ((-1, False), (True, False), (0, 1)):
            with self.assertRaises(ValueError):
                team.termination_step(state, [], 3, 'OK', 'critic')
        for limit, marker, mode, events in [(0, 'OK', 'or', False), (True, 'OK', 'or', False),
                                          (3, '', 'or', False), (3, 'OK', 'xor', False), (3, 'OK', 'or', 1)]:
            with self.assertRaises(ValueError):
                team.termination_step((0, False), [], limit, marker, 'critic', mode, events)
        for item in ({'kind': 'other', 'text': 'OK', 'source': 'critic'},
                     {'kind': 'chat', 'text': 1, 'source': 'critic'}):
            with self.assertRaises(ValueError):
                team.termination_step((0, False), [item], 3, 'OK', 'critic')

    def test_snapshot_contains_all_roles_and_deepcopies_nested_state(self):
        agents = {'writer': {'context': ['draft']}, 'critic': {'context': ['review']}}
        manager = {'message_thread': [{'source': 'writer', 'text': 'draft'}],
                   'current_turn': 2, 'next_speaker_index': 1, 'version': 'teaching-v1'}
        before = copy.deepcopy((agents, manager))
        result = team.snapshot_team(agents, 'manager', manager, False)
        self.assertEqual(result, {'agent_states': {**agents, 'manager': manager}})
        result['agent_states']['writer']['context'].append('changed')
        result['agent_states']['manager']['message_thread'][0]['text'] = 'changed'
        self.assertEqual((agents, manager), before)
        manager['current_turn'] = 10
        self.assertEqual(result['agent_states']['manager']['current_turn'], 2)

    def test_snapshot_rejects_incomplete_manager_identity_conflicts_and_running_team(self):
        manager = {'message_thread': [], 'current_turn': 0, 'next_speaker_index': 0}
        for key in ('message_thread', 'current_turn', 'next_speaker_index'):
            with self.assertRaises(ValueError):
                team.snapshot_team({'a': {}}, 'manager', {k: v for k, v in manager.items() if k != key}, False)
        for agents, name, running in [({}, 'manager', False), ({'a': {}}, 'a', False),
                                      ({'a': {}}, '', False), ({'a': {}}, 'manager', True),
                                      ({'a': {}}, 'manager', 0)]:
            with self.assertRaises(ValueError):
                team.snapshot_team(agents, name, manager, running)

    def test_autogen_demo_returns_selected_speaker_and_text_stop(self):
        result = team.demo()
        self.assertEqual(result['speaker'], ('writer', 1))
        self.assertEqual(result['termination'], ((1, True), True))

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_codex_cli_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/codex-cli.py')

    def test_codex_cli_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/codex-cli.py')

    def test_claude_code_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/claude-code.py')

    def test_claude_code_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/claude-code.py')

    def test_langgraph_cli(self):
        assert_cli_matches_demo(self, 'examples/harness/langgraph.py')

    def test_langgraph_quiet_import(self):
        assert_quiet_import(self, 'examples/harness/langgraph.py')

    def test_autogen_cli(self):
        assert_cli_matches_demo(self, 'examples/harness/autogen.py')

    def test_autogen_quiet_import(self):
        assert_quiet_import(self, 'examples/harness/autogen.py')
