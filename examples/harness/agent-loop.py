"""Harness任务循环：纯函数模拟，不执行外部动作。"""


def transition(state: str, event: str) -> str:
    """根据已观测事件推进阶段；未知写入结果必须先回查。"""
    edges = {
        ('ready', 'dispatch'): 'pending',
        ('pending', 'ok'): 'verifying',
        ('pending', 'timeout'): 'unknown',
        ('pending', 'rejected'): 'ready',
        ('unknown', 'found'): 'verifying',
        ('unknown', 'absent'): 'ready',
        ('verifying', 'accepted'): 'done',
        ('verifying', 'mismatch'): 'ready',
    }
    if state not in {'ready', 'pending', 'unknown', 'verifying', 'done'}:
        raise ValueError('未知状态')
    if state == 'done':
        return 'done'
    if (state, event) not in edges:
        raise ValueError('非法状态转移')
    return edges[state, event]


def admit_budget(remaining: tuple[int, int, int],
                 reservation: tuple[int, int, int]) -> tuple[bool, tuple[int, int, int]]:
    """按步数、token、毫秒的上界预留预算；拒绝时预算不变。"""
    if len(remaining) != 3 or len(reservation) != 3:
        raise ValueError('预算必须有三个维度')
    if any(type(x) is not int or x < 0 for x in (*remaining, *reservation)):
        raise ValueError('预算必须是非负整数')
    if reservation[0] < 1:
        raise ValueError('每个调度动作至少消耗一步')
    if any(c > b for b, c in zip(remaining, reservation)):
        return False, remaining
    return True, tuple(b - c for b, c in zip(remaining, reservation))


def reconcile_outcome(key: str, payload: str, ledger: dict,
                      authoritative_absent: bool = False) -> str:
    """按幂等键回查；只在权威确认不存在时允许发送。"""
    if not key:
        raise ValueError('幂等键不能为空')
    if key in ledger:
        stored_payload, status = ledger[key]
        if stored_payload != payload:
            return 'conflict'
        if status not in {'pending', 'committed'}:
            raise ValueError('账本状态不合法')
        return 'verify' if status == 'committed' else 'wait'
    return 'dispatch' if authoritative_absent else 'query'


def demo() -> dict:
    """给出状态、预算与重复请求的可检查示例。"""
    state = 'ready'
    states = [state]
    for event in ['dispatch', 'timeout', 'found', 'accepted']:
        state = transition(state, event)
        states.append(state)
    return {'states': states, 'budget': admit_budget((3, 100, 500), (1, 40, 100)),
            'recovery': reconcile_outcome('draft-1', '正文', {'draft-1': ('正文', 'committed')})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
