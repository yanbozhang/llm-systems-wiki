"""编程Agent教学：上下文定位、受保护文本补丁和独立验收。"""
import ast
from hashlib import sha256


def repository_slice(calls: dict[str, set[str]], seeds: set[str], radius: int) -> list[str]:
    """在显式调用图上取种子周围的调用者和被调用者，不解析真实仓库。"""
    if type(radius) is not int or radius < 0:
        raise ValueError('半径须为非负整数')
    graph = {node: set(children) for node, children in calls.items()}
    for node, children in calls.items():
        for child in children:
            graph.setdefault(child, set()).add(node)
    if not seeds <= graph.keys():
        raise ValueError('种子不在调用图中')
    visited, frontier = set(seeds), set(seeds)
    for _ in range(radius):
        frontier = {v for u in frontier for v in graph[u]} - visited
        visited |= frontier
    return sorted(visited)


def guarded_replace(source: str, old: str, new: str, expected_sha: str) -> str:
    """对内存Python文本做基线与唯一锚点校验，再返回语法可解析的候选补丁。"""
    if sha256(source.encode()).hexdigest() != expected_sha:
        raise ValueError('补丁基线已变化')
    if not old or source.count(old) != 1:
        raise ValueError('替换锚点必须唯一且非空')
    candidate = source.replace(old, new, 1)
    ast.parse(candidate)
    return candidate


def grade_patch(repair: set[str], regression: set[str], outcomes: dict[str, str],
                patch_id: str, evidence_patch_id: str) -> dict:
    """用冻结测试身份审阅结果记录；只汇总数据，不运行测试。"""
    if not patch_id or not evidence_patch_id:
        raise ValueError('补丁和证据必须具有版本身份')
    if repair & regression:
        raise ValueError('修复与回归集合不可重叠')
    if any(v not in {'passed', 'failed', 'unknown'} for v in outcomes.values()):
        raise ValueError('结果状态不合法')
    if patch_id != evidence_patch_id:
        return {'status': 'stale', 'missing': [], 'failed': []}
    required = repair | regression
    missing = sorted(t for t in required if outcomes.get(t, 'unknown') == 'unknown')
    failed = sorted(t for t in required if outcomes.get(t) == 'failed')
    if failed:
        status = 'failed'
    elif missing or not repair or not regression:
        status = 'unknown'
    else:
        status = 'succeeded'
    return {'status': status, 'missing': missing, 'failed': failed}


def demo() -> dict:
    """返回定位范围与修复通过但回归失败的记录判断。"""
    return {'context': repository_slice({'entry': {'parse'}, 'parse': {'normalize'},
                                        'unrelated': set()}, {'parse'}, 1),
            'grade': grade_patch({'empty_input'}, {'normal_input'},
                                 {'empty_input': 'passed', 'normal_input': 'failed'}, 'p1', 'p1')}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
