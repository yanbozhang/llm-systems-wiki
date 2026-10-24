"""记忆保鲜：先判适用性，再排序，最后传播撤回。"""
from math import isfinite


def eligible_memories(records: list[dict], namespace: tuple[str, ...],
                      version: str, now: float) -> list[str]:
    """仅召回当前命名空间、版本、有效期内且可追溯的活跃记忆。"""
    if not isfinite(now):
        raise ValueError('当前时间必须有限')
    result = []
    for row in records:
        expiry = row.get('expires_at')
        if expiry is not None and not isfinite(expiry):
            raise ValueError('失效时间必须有限')
        if (tuple(row['namespace']) == namespace and row['version'] == version
                and row['active'] is True and bool(row['source'])
                and (expiry is None or now < expiry)):
            result.append(row['id'])
    return sorted(set(result))


def freshness_score(relevance: float, age: float, half_life: float) -> float:
    """计算自定义半衰期排序分；不是事实为真的概率。"""
    if not all(isfinite(x) for x in (relevance, age, half_life)):
        raise ValueError('参数必须有限')
    if not 0 <= relevance <= 1 or age < 0 or half_life <= 0:
        raise ValueError('相关度、年龄或半衰期不合法')
    return relevance * 2 ** (-age / half_life)


def invalidation_closure(seeds: set[str], depends_on: dict[str, set[str]]) -> set[str]:
    """从撤回来源传播到所有依赖它的派生条目，支持依赖环。"""
    reverse = {}
    for derived, parents in depends_on.items():
        for parent in parents:
            reverse.setdefault(parent, set()).add(derived)
    invalid = set(seeds)
    pending = list(seeds)
    while pending:
        current = pending.pop()
        for child in reverse.get(current, set()) - invalid:
            invalid.add(child)
            pending.append(child)
    return invalid


def demo() -> dict:
    """返回半衰期和来源撤回的确定性结果。"""
    return {'score_now': freshness_score(0.8, 0, 30),
            'score_later': freshness_score(0.8, 30, 30),
            'invalid': sorted(invalidation_closure({'source'},
                {'note': {'source'}, 'index': {'note'}, 'answer': {'index'}}))}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
