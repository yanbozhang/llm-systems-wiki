"""LangGraph超步、检查点写入及interrupt重跑的纯数据教学。"""
from copy import deepcopy


def merge_superstep(state: dict[str, int], writes: list[tuple[str, str, int]],
                    reducers: dict[str, str]) -> dict[str, int]:
    """按教学任务路径排序后归并整数通道；普通last通道拒绝同一步多写。"""
    if any(type(value) is not int for value in state.values()):
        raise ValueError('初始通道值必须为整数')
    pending = {}
    for path, channel, value in sorted(writes, key=lambda row: row[0]):
        if channel not in state or type(value) is not int:
            raise ValueError('通道不存在或写入值类型不合法')
        pending.setdefault(channel, []).append(value)
    result = dict(state)
    for channel, values in pending.items():
        reducer = reducers.get(channel, 'last')
        if reducer == 'sum':
            result[channel] += sum(values)
        elif reducer == 'last' and len(values) == 1:
            result[channel] = values[0]
        elif reducer == 'last':
            raise ValueError('last通道在同一超步只能接收一个值')
        else:
            raise ValueError('不支持的教学归并器')
    return result


def checkpoint_writes(previous: dict, scope: tuple[str, str, str],
                      task_id: str, writes: list[tuple[str, str]]) -> dict:
    """模拟普通pending writes按线程、命名空间、检查点、任务和序号去重。"""
    if len(scope) != 3 or any(type(x) is not str for x in scope):
        raise ValueError('检查点范围必须为三个字符串')
    if not scope[0] or not scope[2] or not task_id:
        raise ValueError('线程、检查点和任务身份不能为空')
    result = deepcopy(previous)
    for index, (channel, value) in enumerate(writes):
        if not channel or channel.startswith('__'):
            raise ValueError('教学模型只接受普通命名通道')
        key = (*scope, task_id, index)
        result.setdefault(key, (channel, value))
    return result


def replay_interrupt_node(questions: list[str], answers: list[str],
                          ledger: set[str], action_key: str) -> dict:
    """从节点头重跑，按interrupt次序消费答案；用外部模拟账本去重前置效果。"""
    if (not questions or any(type(q) is not str or not q for q in questions)
            or len(set(questions)) != len(questions) or not action_key):
        raise ValueError('问题身份须非空且唯一，动作身份不能为空')
    if len(answers) > len(questions):
        raise ValueError('答案数量超过interrupt槽位')
    new_effect = action_key not in ledger
    next_ledger = set(ledger) | {action_key}
    consumed = list(zip(questions, answers))
    index = len(answers)
    return {'prefix_reexecuted': True, 'new_effect': new_effect,
            'ledger': next_ledger, 'consumed': consumed,
            'interrupt': questions[index] if index < len(questions) else None,
            'complete': index == len(questions)}


def demo() -> dict:
    """返回归并结果与第一次遇到interrupt的模拟记录。"""
    return {'state': merge_superstep({'total': 1}, [('b', 'total', 3), ('a', 'total', 2)], {'total': 'sum'}),
            'pause': replay_interrupt_node(['approve', 'destination'], [], set(), 'draft-1')}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
