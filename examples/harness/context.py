"""上下文选择：预算优化、调用闭包与检查点审计。"""


def select_context(items: list[tuple[str, int, int, bool]], budget: int) -> list[str]:
    """在小整数token预算内精确选择条目，强制保留必要项。"""
    if type(budget) is not int or budget < 0:
        raise ValueError('预算须为非负整数')
    if len({x[0] for x in items}) != len(items):
        raise ValueError('条目身份重复')
    if any(type(c) is not int or c <= 0 or type(v) is not int or v < 0
           or type(m) is not bool for _, c, v, m in items):
        raise ValueError('成本、价值或必选标记不合法')
    mandatory = [name for name, _, _, m in items if m]
    left = budget - sum(c for _, c, _, m in items if m)
    if left < 0:
        raise ValueError('必要上下文已超预算')
    states = {0: (0, ())}
    for name, cost, value, required in items:
        if required:
            continue
        for used, (score, chosen) in list(states.items()):
            new = used + cost
            if new <= left and score + value > states.get(new, (-1, ()))[0]:
                states[new] = score + value, chosen + (name,)
    best = max(states, key=lambda used: (states[used][0], -used))
    return mandatory + list(states[best][1])


def trim_complete_turns(turns: list[list[dict]], budget: int) -> list[list[dict]]:
    """将完整调用回合作为原子块，保留预算内最近的连续后缀。"""
    if type(budget) is not int or budget < 0:
        raise ValueError('预算须为非负整数')
    costs = []
    for turn in turns:
        pending, seen = set(), set()
        for msg in turn:
            if type(msg['tokens']) is not int or msg['tokens'] < 0:
                raise ValueError('token计数不合法')
            kind = msg['kind']
            if kind == 'call':
                if msg['id'] in seen:
                    raise ValueError('调用身份重复')
                seen.add(msg['id']); pending.add(msg['id'])
            elif kind == 'result':
                if msg['id'] not in pending:
                    raise ValueError('结果缺少对应调用')
                pending.remove(msg['id'])
            elif kind != 'text':
                raise ValueError('消息类型不合法')
        if pending:
            raise ValueError('回合包含未完成调用')
        costs.append(sum(m['tokens'] for m in turn))
    used, start = 0, len(turns)
    for i in range(len(turns) - 1, -1, -1):
        if used + costs[i] > budget:
            break
        used += costs[i]; start = i
    return [list(turn) for turn in turns[start:]]


def audit_checkpoint(required: dict[str, str], summary: dict[str, str]) -> dict:
    """对必须逐字保持的约束、身份和来源版本做确定性审计。"""
    missing = sorted(required.keys() - summary.keys())
    changed = sorted(k for k in required.keys() & summary.keys()
                     if required[k] != summary[k])
    kept = len(required) - len(missing) - len(changed)
    return {'missing': missing, 'changed': changed,
            'retention': kept / len(required) if required else None}


def demo() -> dict:
    """返回可以手算的上下文选择和约束丢失结果。"""
    return {'chosen': select_context([('goal', 2, 0, True), ('a', 4, 6, False),
                                      ('b', 3, 5, False), ('c', 3, 5, False)], 8),
            'audit': audit_checkpoint({'target': 'repo@v1', 'rule': '保留原文件'},
                                      {'target': 'repo@v2'})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
