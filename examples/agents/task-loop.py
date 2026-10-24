"""业务任务闭环：验收、依赖前沿与保守补偿规划。"""


def terminal_contract(checks: dict[str, bool | None]) -> str:
    """对冻结的非空业务断言做三值合取，失败优先于未知。"""
    if not checks:
        raise ValueError('业务契约不能为空')
    if any(v is not None and type(v) is not bool for v in checks.values()):
        raise ValueError('断言只能为True、False或None')
    if any(v is False for v in checks.values()):
        return 'failed'
    if any(v is None for v in checks.values()):
        return 'unknown'
    return 'succeeded'


def task_frontier(dependencies: dict[str, set[str]], completed: set[str],
                  failed: set[str]) -> dict:
    """求DAG中可执行与受失败阻断的节点，不执行实际业务。"""
    nodes = set(dependencies)
    if not (completed | failed) <= nodes or completed & failed:
        raise ValueError('完成与失败集合不合法')
    if any(not parents <= nodes for parents in dependencies.values()):
        raise ValueError('依赖节点不存在')
    ordered = set()
    while ordered != nodes:
        layer = {n for n in nodes - ordered if dependencies[n] <= ordered}
        if not layer:
            raise ValueError('依赖图存在环')
        ordered |= layer
    if any(not dependencies[n] <= completed for n in completed):
        raise ValueError('完成记录违反依赖顺序')
    blocked = set(failed)
    while True:
        extra = {n for n in nodes - blocked if dependencies[n] & blocked}
        if not extra:
            break
        blocked |= extra
    ready = {n for n in nodes - completed - blocked if dependencies[n] <= completed}
    return {'ready': sorted(ready), 'blocked': sorted(blocked),
            'all_completed': completed == nodes}


def compensation_plan(actions: list[dict]) -> dict:
    """结果未知先回查；仅对全部可逆的已提交动作生成逆序补偿计划。"""
    if len({a['id'] for a in actions}) != len(actions):
        raise ValueError('动作身份重复')
    if any(a['status'] not in {'committed', 'unknown', 'absent'} for a in actions):
        raise ValueError('未知动作状态')
    if any(type(a['reversible']) is not bool for a in actions):
        raise ValueError('可逆性必须显式标注')
    unknown = [a['id'] for a in actions if a['status'] == 'unknown']
    if unknown:
        return {'mode': 'reconcile', 'actions': unknown}
    committed = [a for a in actions if a['status'] == 'committed']
    if any(not a['reversible'] for a in committed):
        return {'mode': 'manual', 'actions': []}
    return {'mode': 'compensate', 'actions': [a['id'] for a in reversed(committed)]}


def demo() -> dict:
    """用资料整理任务展示局部完成与最终成功的差别。"""
    return {'terminal': terminal_contract({'sources': True, 'links': None}),
            'frontier': task_frontier({'read': set(), 'draft': {'read'}, 'verify': {'draft'}},
                                      {'read'}, set()),
            'compensation': compensation_plan([
                {'id': 'draft', 'status': 'committed', 'reversible': True},
                {'id': 'index', 'status': 'committed', 'reversible': True}])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
