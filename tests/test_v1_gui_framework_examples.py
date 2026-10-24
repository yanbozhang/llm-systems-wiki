"""移动和桌面GUI方案的标准库教学模型；不采集屏幕或连接设备。"""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def load_example(name):
    p = Path(__file__).resolve().parents[1] / 'examples/agents' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mobile = load_example('mobile-agent')
app = load_example('app-agent')
ui = load_example('ui-tars')


class MobileAgentTeachingTests(unittest.TestCase):
    def test_text_merge_documented_center_and_input_preservation(self):
        boxes = [{'text': '晴', 'box': [12, 35, 52, 55]}, {'text': '天气', 'box': [10, 10, 50, 30]}]
        before = copy.deepcopy(boxes)
        self.assertEqual(mobile.perception_index(boxes, [], 100, 100),
                         [{'text': 'text: 天气\n晴', 'coordinates': [31, 32]}])
        self.assertEqual(boxes, before)

    def test_merge_thresholds_are_asymmetric_and_strict_where_documented(self):
        first = {'text': 'a', 'box': [10, 10, 50, 30]}
        for box, count in (([10, 60, 50, 80], 2), ([10, 59, 50, 79], 1),
                           ([20, 35, 60, 55], 2), ([10, 20, 50, 40], 1),
                           ([10, 19, 50, 39], 2), ([10, 35, 50, 65], 2)):
            result = mobile.perception_index([first, {'text': 'b', 'box': box}], [], 100, 100)
            self.assertEqual(len(result), count, box)

    def test_merge_uses_latest_chain_anchor_and_keeps_icon_identity(self):
        boxes = [{'text': 'a', 'box': [10, 10, 30, 20]}, {'text': 'b', 'box': [18, 25, 38, 35]},
                 {'text': 'c', 'box': [26, 40, 46, 50]}]
        icons = [{'text': '按钮', 'box': [80, 80, 100, 100]}]
        self.assertEqual(mobile.perception_index(boxes, icons, 100, 100), [
            {'text': 'text: a\nb\nc', 'coordinates': [28, 30]},
            {'text': 'icon: 按钮', 'coordinates': [90, 90]}])

    def test_perception_rejects_invalid_geometry(self):
        for box in ([-1, 0, 10, 10], [0, 0, 101, 10], [10, 0, 10, 10]):
            with self.assertRaises(ValueError):
                mobile.perception_index([{'text': 'a', 'box': box}], [], 100, 100)

    def test_planning_keeps_progress_memory_and_operation_history_distinct(self):
        goals = ['查询', '填写', '核对']
        steps = [{'goal': '查询', 'operation': '尝试查询', 'completes_goal': False},
                 {'goal': '查询', 'operation': '读到晴', 'completes_goal': True},
                 {'goal': '查询', 'operation': '再次确认', 'completes_goal': True}]
        facts = {'天气': {'值': '晴'}}
        result = mobile.planning_projection(goals, steps, facts)
        self.assertEqual(result['completed'], ['查询'])
        self.assertEqual(result['remaining'], ['填写', '核对'])
        self.assertEqual(result['accepted_operations'], ['尝试查询', '读到晴', '再次确认'])
        result['memory']['天气']['值'] = '变更副本'
        self.assertEqual(facts, {'天气': {'值': '晴'}})
        with self.assertRaises(ValueError):
            mobile.planning_projection(['a', 'a'], [], {})
        with self.assertRaises(ValueError):
            mobile.planning_projection(['a'], [{'goal': 'b', 'operation': 'x'}], {})

    def test_reflection_a_commits_b_and_c_preserve_success_history(self):
        state = {'history': ['old'], 'progress': '旧进度', 'nested': {'x': 1}}
        before = copy.deepcopy(state)
        accepted = mobile.reflection_transition(state, 'A', 'new', '新进度')
        self.assertEqual(accepted['history'], ['old', 'new'])
        self.assertEqual(accepted['progress'], '新进度')
        self.assertFalse(accepted['error_flag'])
        self.assertEqual(accepted['next_control'], 'DECIDE')
        for verdict, control in (('B', 'BACK_THEN_OBSERVE'), ('C', 'REVISE_ACTION')):
            result = mobile.reflection_transition(state, verdict, 'not-accepted')
            self.assertEqual(result['history'], ['old'])
            self.assertEqual(result['progress'], '旧进度')
            self.assertTrue(result['error_flag'])
            self.assertEqual(result['next_control'], control)
        accepted['nested']['x'] = 2
        self.assertEqual(state, before)

    def test_strict_reflection_and_mobile_demo(self):
        with self.assertRaises(ValueError):
            mobile.reflection_transition({}, 'A', 'action')
        with self.assertRaises(ValueError):
            mobile.reflection_transition({}, 'A because...', 'action', 'progress')
        result = mobile.demo()
        self.assertEqual(result['perception'][0]['coordinates'], [31, 32])
        self.assertEqual(result['planning']['remaining'], ['填写'])
        self.assertEqual(result['reflection']['next_control'], 'BACK_THEN_OBSERVE')


class AppAgentTeachingTests(unittest.TestCase):
    def test_element_resource_fallback_parent_and_index_identity(self):
        attrs = {'resource-id': 'demo:id/send', 'class': 'Button', 'bounds': [0, 0, 100, 40], 'index': 0}
        self.assertEqual(app.element_identity(attrs), 'demo.id_send_0')
        self.assertEqual(app.element_identity(dict(attrs, **{'resource-id': ''})), 'Button_100_40_0')
        parent = {'resource-id': 'demo:id/form', 'bounds': [0, 0, 300, 240]}
        self.assertEqual(app.element_identity(attrs, parent), 'demo.id_form_demo.id_send_0')
        self.assertEqual(app.element_identity(dict(attrs, index=1)), 'demo.id_send_1')
        self.assertEqual(app.element_identity(attrs, add_index=False), 'demo.id_send')

    def test_short_description_threshold_and_invalid_bounds(self):
        attrs = {'resource-id': 'id', 'bounds': [0, 0, 10, 10], 'index': 0}
        self.assertEqual(app.element_identity(dict(attrs, **{'content-desc': 'Send now'})), 'id_Sendnow_0')
        self.assertEqual(app.element_identity(dict(attrs, **{'content-desc': 'x' * 19})), 'id_' + 'x' * 19 + '_0')
        self.assertEqual(app.element_identity(dict(attrs, **{'content-desc': 'x' * 20})), 'id_0')
        with self.assertRaises(ValueError):
            app.element_identity(dict(attrs, bounds=[0, 0, 0, 1]))

    def test_four_learning_decisions_separate_exclusion_and_document_write(self):
        ineffective = app.learn_action_document({}, [], 'u', 'tap', 'INEFFECTIVE')
        self.assertEqual(ineffective, {'documents': {}, 'blocked': ['u'], 'written': False, 'control': 'CONTINUE'})
        for decision, blocked, control in (('BACK', ['u'], 'BACK'), ('CONTINUE', ['u'], 'CONTINUE'),
                                           ('SUCCESS', [], 'CONTINUE')):
            result = app.learn_action_document({}, [], 'u', 'tap', decision, '打开详情')
            self.assertEqual(result['blocked'], blocked)
            self.assertEqual(result['control'], control)
            self.assertTrue(result['written'])
            self.assertEqual(result['documents']['u']['tap'], '打开详情')
            self.assertEqual(set(result['documents']['u']), {'tap', 'text', 'v_swipe', 'h_swipe', 'long_press'})

    def test_existing_action_slot_is_not_overwritten_and_inputs_are_copied(self):
        store, blocked = {'u': {'tap': '旧知识', 'text': ''}}, {'other'}
        before = copy.deepcopy((store, blocked))
        result = app.learn_action_document(store, blocked, 'u', 'tap', 'BACK', '新知识')
        self.assertFalse(result['written'])
        self.assertEqual(result['documents']['u']['tap'], '旧知识')
        self.assertEqual(result['blocked'], ['other', 'u'])
        result['documents']['u']['text'] = '副本'
        self.assertEqual((store, blocked), before)
        with self.assertRaises(ValueError):
            app.learn_action_document({}, [], 'u', 'tap', 'SUCCESS')

    def test_deployment_uses_only_visible_uids_with_current_tags(self):
        elements = [{'uid': 'a', 'box': [0, 0, 100, 40]}, {'uid': 'b', 'box': [100, 0, 200, 40]},
                    {'uid': 'c', 'box': [200, 0, 300, 40]}]
        docs = {'a': {'tap': 'A'}, 'c': {'tap': 'C'}, 'offscreen': {'tap': '不可见'}}
        result = app.deployment_context(elements, docs, {'area': 2}, 300, 240)
        self.assertEqual(result['visible_documentation'], [
            {'tag': 1, 'uid': 'a', 'actions': {'tap': 'A'}}, {'tag': 3, 'uid': 'c', 'actions': {'tap': 'C'}}])
        self.assertEqual(result['action'], {'kind': 'tap', 'point': [150, 20]})
        result['visible_documentation'][0]['actions']['tap'] = '副本'
        self.assertEqual(docs['a']['tap'], 'A')

    def test_grid_region_five_coordinates_and_document_exclusion(self):
        for subarea, point in (('top-left', [125, 150]), ('center', [150, 180]), ('bottom-right', [175, 210])):
            result = app.deployment_context([{'uid': 'a', 'box': [0, 0, 10, 10]}], {'a': {'tap': 'knowledge'}},
                                             {'area': 5, 'subarea': subarea}, 300, 240, (2, 3))
            self.assertEqual(result, {'visible_documentation': [], 'action': {'kind': 'tap', 'point': point}})
        with self.assertRaises(ValueError):
            app.deployment_context([], {}, {'area': 7}, 300, 240, (2, 3))
        with self.assertRaises(ValueError):
            app.deployment_context([], {}, {'area': 1, 'subarea': 'unknown'}, 300, 240, (2, 3))

    def test_app_demo_all_functions(self):
        result = app.demo()
        self.assertEqual(result['uid'], 'demo.id_send_0')
        self.assertTrue(result['learned']['written'])
        self.assertEqual(result['element']['action']['point'], [50, 20])
        self.assertEqual(result['grid']['action']['point'], [125, 150])


class UiTarsTeachingTests(unittest.TestCase):
    def test_parse_all_declared_actions_as_literal_data(self):
        cases = [("Action: click(start_box='[500,250]')", 'click', {'start_box': [500, 250, 500, 250]}),
                 ("Action：drag(start_box='[0,0]', end_box='[10,20,30,40]')", 'drag',
                  {'start_box': [0, 0, 0, 0], 'end_box': [10, 20, 30, 40]}),
                 ("type(content='你好\\n世界')", 'type', {'content': '你好\n世界'}),
                 ("hotkey(key='ctrl+c')", 'hotkey', {'key': 'ctrl+c'}),
                 ("scroll(start_box='[1,2]', direction='down')", 'scroll', {'start_box': [1, 2, 1, 2], 'direction': 'down'}),
                 ('wait()', 'wait', {}), ('finished()', 'finished', {}), ('call_user()', 'call_user', {})]
        with patch('builtins.eval', side_effect=AssertionError('禁止执行动作文本')) as evaluate:
            for text, name, args in cases:
                self.assertEqual(ui.parse_action(text), {'action_type': name, 'action_inputs': args})
        evaluate.assert_not_called()

    def test_parser_rejects_unknown_duplicate_extra_and_executable_arguments(self):
        for text in ('unknown()', "type(content='a', content='b')", "click('[1,2]')", 'click()',
                     "wait(extra='x')", 'type(content=str(1))', 'wait(); finished()',
                     "scroll(start_box='[1,2]', direction='left')"):
            with self.assertRaises(ValueError, msg=text):
                ui.parse_action(text)

    def test_parser_rejects_wrong_box_shapes_and_non_numeric_literals(self):
        for text in ("click(start_box='[1,2,3]')", "click(start_box='[True,2]')",
                     "click(start_box='[1e999,2]')", "click(start_box=[1,2])"):
            with self.assertRaises(ValueError):
                ui.parse_action(text)

    def test_grounding_separates_operator_and_parser_scaled_coordinates(self):
        result = ui.grounding_coordinates([500, 250], (1920, 1080), display_scale=2)
        self.assertEqual(result, {'normalized_box': [0.5, 0.25, 0.5, 0.25],
                                  'operator_point': [960, 270], 'parser_start_coords': [1920, 540]})
        explicit = ui.grounding_coordinates([480, 270], (1920, 1080), normalization=(960, 540))
        self.assertEqual(explicit['operator_point'], [960, 540])

    def test_grounding_zero_edge_quantization_and_invalid_normalization(self):
        self.assertEqual(ui.grounding_coordinates([0, 0], (100, 50))['operator_point'], [0, 0])
        self.assertEqual(ui.grounding_coordinates([1000, 1000], (100, 50))['operator_point'], [100, 50])
        self.assertEqual(ui.grounding_coordinates([1, 1], (1, 1), normalization=(3, 3))['operator_point'], [0.333, 0.333])
        for box in ([-1, 0], [1001, 0], [2, 0, 1, 1]):
            with self.assertRaises(ValueError):
                ui.grounding_coordinates(box, (100, 50))
        with self.assertRaises(ValueError):
            ui.grounding_coordinates([0, 0], (100, 50), normalization=(0, 1000))

    def test_one_loop_can_contain_multiple_actions_and_deepcopies_state(self):
        state = {'status': 'RUNNING', 'loops': 0, 'nested': {'x': 1}}
        actions = [{'action_type': 'click', 'action_inputs': {'start_box': [0, 0, 0, 0]}}, {'action_type': 'wait'}]
        before = copy.deepcopy((state, actions))
        result = ui.agent_loop_transition(state, actions, 3)
        self.assertEqual(result['loops'], 1)
        self.assertEqual(len(result['dispatched']), 2)
        self.assertEqual(result['status'], 'RUNNING')
        self.assertTrue(result['needs_next_observation'])
        result['nested']['x'] = 2
        result['dispatched'][0]['action_inputs']['start_box'][0] = 99
        self.assertEqual((state, actions), before)

    def test_terminal_actions_stop_tail_dispatch(self):
        for terminal, status in (('finished', 'END'), ('call_user', 'CALL_USER')):
            result = ui.agent_loop_transition({'status': 'RUNNING', 'loops': 0},
                                              [{'action_type': terminal}, {'action_type': 'unsupported-tail'}], 3)
            self.assertEqual(result['status'], status)
            self.assertEqual(result['dispatched'], [{'action_type': terminal}])
            self.assertFalse(result['needs_next_observation'])

    def test_pre_round_stop_budget_and_nonrunning_state_do_not_dispatch(self):
        action = [{'action_type': 'click'}]
        exhausted = ui.agent_loop_transition({'status': 'RUNNING', 'loops': 3}, action, 3)
        self.assertEqual(exhausted, {'status': 'ERROR', 'loops': 3, 'dispatched': [], 'reason': 'REACH_MAXLOOP'})
        aborted = ui.agent_loop_transition({'status': 'RUNNING', 'loops': 3}, action, 3, aborted=True)
        self.assertEqual(aborted['status'], 'USER_STOPPED')
        self.assertEqual(aborted['dispatched'], [])
        ended = ui.agent_loop_transition({'status': 'END', 'loops': 1}, action, 3, aborted=True)
        self.assertEqual(ended, {'status': 'END', 'loops': 1, 'dispatched': []})
        with self.assertRaises(ValueError):
            ui.agent_loop_transition({'status': 'RUNNING', 'loops': 0}, [{'action_type': 'unknown'}], 3)

    def test_ui_tars_demo_all_functions(self):
        result = ui.demo()
        self.assertEqual(result['parsed']['action_inputs']['start_box'], [500, 250, 500, 250])
        self.assertEqual(result['coordinates']['operator_point'], [960, 270])
        self.assertEqual(result['coordinates']['parser_start_coords'], [1920, 540])
        self.assertEqual(result['loop']['status'], 'CALL_USER')
        self.assertEqual(len(result['loop']['dispatched']), 1)

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_mobile_agent_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/mobile-agent.py')

    def test_mobile_agent_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/mobile-agent.py')

    def test_app_agent_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/app-agent.py')

    def test_app_agent_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/app-agent.py')

    def test_ui_tars_cli(self):
        assert_cli_matches_demo(self, 'examples/agents/ui-tars.py')

    def test_ui_tars_quiet_import(self):
        assert_quiet_import(self, 'examples/agents/ui-tars.py')
