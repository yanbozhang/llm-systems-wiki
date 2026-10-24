"""Mobile-Agent-v2的数据流教学；不截图、不调用模型、不发送设备动作。"""
from copy import deepcopy


def perception_index(text_boxes, icon_boxes, width, height):
    """按v2的几何阈值合并文本框，再把文本和图标描述转为中心坐标记录。"""
    if width <= 0 or height <= 0:
        raise ValueError("截图尺寸须为正")
    records = list(text_boxes) + list(icon_boxes)
    for item in records:
        x1, y1, x2, y2 = item['box']
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("边界框无效或越界")
    ordered = sorted(text_boxes, key=lambda item: (item['box'][1], item['box'][0]))
    used, merged = set(), []
    for i, first in enumerate(ordered):
        if i in used:
            continue
        chain, anchor = [first], first['box']
        for j in range(i + 1, len(ordered)):
            box = ordered[j]['box']
            if j not in used and abs(anchor[0] - box[0]) < 10 and -10 <= box[1] - anchor[3] < 30 and abs((anchor[3] - anchor[1]) - (box[3] - box[1])) < 10:
                chain.append(ordered[j]); used.add(j); anchor = box
        merged.append({'text': '\n'.join(item['text'] for item in chain),
                       'box': [min(item['box'][0] for item in chain), min(item['box'][1] for item in chain),
                               max(item['box'][2] for item in chain), max(item['box'][3] for item in chain)]})
    output = []
    for kind, items in [('text', merged), ('icon', icon_boxes)]:
        for item in items:
            x1, y1, x2, y2 = item['box']
            output.append({'text': kind + ': ' + item['text'],
                           'coordinates': [int((x1 + x2) / 2), int((y1 + y2) / 2)]})
    return output


def planning_projection(goals, accepted_steps, memory):
    """用人工标注子目标演示进度与页面事实分离；不模拟LLM语义推理。"""
    if len(set(goals)) != len(goals):
        raise ValueError("子目标ID须唯一")
    completed = []
    for step in accepted_steps:
        goal = step['goal']
        if goal not in goals:
            raise ValueError("步骤关联了未知子目标")
        if step.get('completes_goal', False) and goal not in completed:
            completed.append(goal)
    return {'completed': completed, 'remaining': [g for g in goals if g not in completed],
            'accepted_operations': [s['operation'] for s in accepted_steps],
            'memory': deepcopy(memory)}


def reflection_transition(state, verdict, operation, updated_progress=None):
    """演示A接受、B回退、C无效的状态更新；只返回待办指令而不操作设备。"""
    if verdict not in ('A', 'B', 'C'):
        raise ValueError("反思结果须为单个A、B或C")
    result = deepcopy(state)
    if verdict == 'A':
        if updated_progress is None:
            raise ValueError("接受操作后需要明确的进度更新结果")
        result['history'] = result.get('history', []) + [operation]
        result['progress'] = updated_progress
        result['error_flag'] = False
        result['next_control'] = 'DECIDE'
    elif verdict == 'B':
        result['error_flag'] = True
        result['next_control'] = 'BACK_THEN_OBSERVE'
    else:
        result['error_flag'] = True
        result['next_control'] = 'REVISE_ACTION'
    return result


def demo():
    """返回感知合并、进度投影和失败回退三个可核算例子。"""
    return {
        'perception': perception_index([{'text': '天气', 'box': [10, 10, 50, 30]}, {'text': '晴', 'box': [12, 35, 52, 55]}], [], 100, 100),
        'planning': planning_projection(['查询', '填写'], [{'goal': '查询', 'operation': '读到天气', 'completes_goal': True}], {'天气': '晴'}),
        'reflection': reflection_transition({'history': [], 'progress': '尚未完成'}, 'B', '点击图标'),
    }


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
