"""Agent任务级验收和预算统计教学；仅读取调用方给定的结果，不执行测试。"""


def grade_patch(fail_to_pass, pass_to_pass, status_map, patch_applied=True, suite_ran=True):
    """模拟明确状态模式下的修复/回归判据；要求至少一个修复测试。"""
    f2p, p2p = list(fail_to_pass), list(pass_to_pass)
    if not f2p or len(set(f2p)) != len(f2p) or len(set(p2p)) != len(p2p) or set(f2p) & set(p2p):
        raise ValueError("修复测试须非空，测试ID须唯一且两组不重叠")
    if type(patch_applied) is not bool or type(suite_ran) is not bool:
        raise ValueError("运行前提须为明确布尔值")
    supported = {'PASSED', 'XFAIL', 'FAILED', 'ERROR', 'SKIPPED'}
    if any(status not in supported for status in status_map.values()):
        raise ValueError("未知测试状态须先由可信解析器处理")
    passed = {'PASSED', 'XFAIL'}
    f2p_ok = [case for case in f2p if status_map.get(case) in passed]
    p2p_ok = [case for case in p2p if status_map.get(case) in passed | {'SKIPPED'}]
    f2p_rate = len(f2p_ok) / len(f2p)
    p2p_rate = len(p2p_ok) / len(p2p) if p2p else 1.0
    valid = patch_applied and suite_ran
    status = 'INVALID' if not valid else ('FULL' if f2p_rate == p2p_rate == 1 else
                                         'PARTIAL' if 0 < f2p_rate < 1 and p2p_rate == 1 else 'NO')
    return {'status': status, 'resolved': status == 'FULL', 'f2p_rate': f2p_rate, 'p2p_rate': p2p_rate,
            'f2p_failed': [case for case in f2p if case not in f2p_ok],
            'p2p_failed': [case for case in p2p if case not in p2p_ok],
            'missing': sorted((set(f2p) | set(p2p)) - set(status_map)),
            'regression_tests': len(p2p)}


def state_acceptance(final_state, requirements):
    """各字段内允许多个等价值，字段之间须全部满足；不执行页面或表达式。"""
    if not requirements:
        raise ValueError("不能用空验收条件宣称任务完成")
    if any(not isinstance(choices, (list, tuple)) or not choices for choices in requirements.values()):
        raise ValueError("每个字段必须给出非空的允许值列表")
    checks = {field: field in final_state and final_state[field] in choices
              for field, choices in requirements.items()}
    return {'checks': checks, 'resolved': all(checks.values()),
            'fraction_met': sum(checks.values()) / len(checks),
            'missing': [field for field in requirements if field not in final_state]}


def budget_report(task_ids, attempts, max_attempts=3, max_calls=5):
    """按预先分配的任务计分，失败尝试也消耗每任务调用预算；保留次级分母。"""
    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise ValueError("分配任务须非空且ID唯一")
    if any(type(x) is not int or x <= 0 for x in (max_attempts, max_calls)):
        raise ValueError("尝试和调用预算须为正整数")
    grouped = {task: [] for task in task_ids}
    for row in attempts:
        if row['task_id'] not in grouped or row['result'] not in ('resolved', 'failed', 'infra_error'):
            raise ValueError("未知任务或结果类型")
        if type(row['attempt']) is not int or row['attempt'] <= 0 or type(row['calls']) is not int or row['calls'] < 0:
            raise ValueError("尝试序号须为正整数，调用数须非负整数")
        grouped[row['task_id']].append(row)
    first, final, executable = set(), set(), set()
    valid_attempts = successful_attempts = infra_errors = over_budget = observed_calls = 0
    for task, rows in grouped.items():
        rows = sorted(rows, key=lambda row: row['attempt'])
        if [row['attempt'] for row in rows] != list(range(1, len(rows) + 1)):
            raise ValueError("每任务尝试序号必须从1连续且不重复")
        calls = 0
        for row in rows:
            calls += row['calls']; observed_calls += row['calls']
            infra_errors += row['result'] == 'infra_error'
            if row['result'] != 'infra_error':
                executable.add(task)
            eligible = row['attempt'] <= max_attempts and calls <= max_calls
            over_budget += not eligible
            if eligible and row['result'] != 'infra_error':
                valid_attempts += 1
                if row['result'] == 'resolved':
                    successful_attempts += 1; final.add(task)
                    if row['attempt'] == 1:
                        first.add(task)
    n = len(task_ids)
    return {'assigned_tasks': n, 'first_successes': len(first), 'budget_successes': len(final),
            'first_rate': len(first) / n, 'budget_rate': len(final) / n,
            'executable_tasks': len(executable),
            'conditional_budget_rate': len(final) / len(executable) if executable else None,
            'valid_attempts': valid_attempts, 'attempt_success_rate': successful_attempts / valid_attempts if valid_attempts else None,
            'infra_errors': infra_errors, 'over_budget_attempts': over_budget,
            'unattempted_tasks': [task for task, rows in grouped.items() if not rows], 'observed_calls': observed_calls}


def demo():
    """返回回归失败、终态缺条件和任务/尝试分母不同的三个算例。"""
    attempts = [{'task_id': 'A', 'attempt': 1, 'calls': 2, 'result': 'failed'},
                {'task_id': 'A', 'attempt': 2, 'calls': 2, 'result': 'resolved'},
                {'task_id': 'B', 'attempt': 1, 'calls': 3, 'result': 'failed'},
                {'task_id': 'C', 'attempt': 1, 'calls': 0, 'result': 'infra_error'}]
    return {'patch': grade_patch(['fix'], ['keep'], {'fix': 'PASSED', 'keep': 'FAILED'}),
            'state': state_acceptance({'record': 'R1', 'title': '示例', 'saved': False},
                                      {'record': ['R1'], 'title': ['示例'], 'saved': [True]}),
            'budget': budget_report(['A', 'B', 'C'], attempts)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
