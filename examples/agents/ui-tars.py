"""UI-TARS动作协议、坐标转换和SDK状态教学；不调用模型或桌面控制。"""
import ast
import math
import re
from copy import deepcopy


def parse_action(text):
    """严格解析单个公共动作子集，仅读取字面量；不执行函数或生成代码。"""
    payload = re.split(r'Action[:：]', text)[-1].strip()
    schema = {'click': {'start_box'}, 'drag': {'start_box', 'end_box'}, 'type': {'content'},
              'hotkey': {'key'}, 'scroll': {'start_box', 'direction'},
              'wait': set(), 'finished': set(), 'call_user': set()}
    try:
        node = ast.parse(payload, mode='eval').body
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.args:
            raise ValueError("要求无位置参数的动作调用")
        name = node.func.id
        if name not in schema or len(node.keywords) != len({k.arg for k in node.keywords}):
            raise ValueError("未知动作或重复参数")
        if {k.arg for k in node.keywords} != schema[name]:
            raise ValueError("参数缺失或多余")
        args = {k.arg: ast.literal_eval(k.value) for k in node.keywords}
        if any(not isinstance(value, str) for value in args.values()):
            raise ValueError("该教学协议要求参数为字符串字面量")
        for key, value in list(args.items()):
            if key.endswith('_box'):
                coords = ast.literal_eval(value)
                if not isinstance(coords, (list, tuple)) or len(coords) not in (2, 4):
                    raise ValueError("框须包含两个点坐标或四个边界坐标")
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in coords):
                    raise ValueError("框坐标须为有限数字")
                args[key] = list(coords) * 2 if len(coords) == 2 else list(coords)
        if name == 'scroll' and args['direction'] not in ('up', 'down'):
            raise ValueError("本例仅覆盖所读NutJS实现的上下滚动")
        return {'action_type': name, 'action_inputs': args}
    except (SyntaxError, TypeError, ValueError) as exc:
        raise ValueError("动作不符合教学协议") from exc


def grounding_coordinates(box, screen_size, normalization=(1000.0, 1000.0), display_scale=1.0):
    """分别计算归一化框、NutJS使用的屏幕点与解析器附加的缩放坐标。"""
    if len(box) not in (2, 4) or len(screen_size) != 2 or len(normalization) != 2:
        raise ValueError("要求二维屏幕、二维归一化尺度及二或四个框坐标")
    coords = list(box) * 2 if len(box) == 2 else list(box)
    w, h = screen_size
    fx, fy = normalization
    if not all(math.isfinite(v) for v in coords + [w, h, fx, fy, display_scale]) or min(w, h, fx, fy, display_scale) <= 0:
        raise ValueError("尺度须为正有限数，坐标须有限")
    normalized = [v / (fx if i % 2 == 0 else fy) for i, v in enumerate(coords)]
    x1, y1, x2, y2 = normalized
    if not (0 <= x1 <= x2 <= 1 and 0 <= y1 <= y2 <= 1):
        raise ValueError("归一化框越界或倒置")
    # 所读实现以DEFAULT_FACTORS=1000量化到千分之一屏幕坐标单位。
    point = [math.floor(((x1 + x2) / 2) * w * 1000 + 0.5) / 1000,
             math.floor(((y1 + y2) / 2) * h * 1000 + 0.5) / 1000]
    return {'normalized_box': normalized, 'operator_point': point,
            'parser_start_coords': [v * display_scale for v in point]}


def agent_loop_transition(state, actions, max_loops, aborted=False):
    """模拟一轮有效截图之后的无异常执行分支；只记录派发意图和终态。"""
    if not isinstance(max_loops, int) or max_loops <= 0:
        raise ValueError("最大轮数须为正整数")
    result = deepcopy(state)
    result['dispatched'] = []
    if result['status'] != 'RUNNING':
        return result
    if aborted:
        result['status'] = 'USER_STOPPED'
        return result
    if result['loops'] >= max_loops:
        result['status'] = 'ERROR'
        result['reason'] = 'REACH_MAXLOOP'
        return result
    result['loops'] += 1
    allowed = {'click', 'drag', 'type', 'hotkey', 'scroll', 'wait', 'finished', 'call_user'}
    for action in actions:
        kind = action['action_type']
        if kind not in allowed:
            raise ValueError("未支持的动作")
        result['dispatched'].append(deepcopy(action))
        if kind == 'finished':
            result['status'] = 'END'
            break
        if kind == 'call_user':
            result['status'] = 'CALL_USER'
            break
    result['needs_next_observation'] = result['status'] == 'RUNNING'
    return result


def demo():
    """返回文本动作、两种坐标字段与终态阻止后续动作的例子。"""
    click = parse_action("Action: click(start_box='[500,250]')")
    terminal = parse_action('call_user()')
    return {'parsed': click,
            'coordinates': grounding_coordinates(click['action_inputs']['start_box'], (1920, 1080), display_scale=2),
            'loop': agent_loop_transition({'status': 'RUNNING', 'loops': 0}, [terminal, click], 3)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
