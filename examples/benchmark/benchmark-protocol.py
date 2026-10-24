"""评测协议的教学实现：稳定身份、切分交集与完整分母，不调用模型。"""
import hashlib
import json
from itertools import combinations


def protocol_fingerprint(protocol):
    """非空JSON对象生成稳定SHA-256；键顺序不影响身份，字段值影响身份。"""
    if not isinstance(protocol, dict) or not protocol:
        raise ValueError('协议必须是非空对象')
    payload = json.dumps(protocol, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def split_overlap(splits):
    """输入切分名到字符串ID列表的映射，返回有交集的切分对及排序后的ID。"""
    if not isinstance(splits, dict):
        raise ValueError('切分必须是对象')
    sets = {}
    for name, ids in splits.items():
        if not isinstance(name, str) or not isinstance(ids, list):
            raise ValueError('切分名须为字符串，ID须为列表')
        if any(not isinstance(x, str) or not x for x in ids):
            raise ValueError('ID须为非空字符串')
        sets[name] = set(ids)
    return {(a, b): sorted(sets[a] & sets[b])
            for a, b in combinations(sorted(sets), 2) if sets[a] & sets[b]}


def score_run(records):
    """一题一条终态记录；passed/failed/error全部进入端到端成功率分母。"""
    if not isinstance(records, list) or not records:
        raise ValueError('至少需要一条记录')
    seen, counts = set(), dict.fromkeys(('passed', 'failed', 'error'), 0)
    for row in records:
        if not isinstance(row, dict):
            raise ValueError('记录必须是对象')
        key, status = row.get('id'), row.get('status')
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('样本ID缺失或重复')
        if not isinstance(status, str) or status not in counts:
            raise ValueError('非法终态')
        seen.add(key)
        counts[status] += 1
    n = len(records)
    scored = n - counts['error']
    return {'n': n, 'counts': counts, 'success_rate': counts['passed'] / n,
            'error_rate': counts['error'] / n,
            'scored_accuracy': counts['passed'] / scored if scored else None}


def demo():
    protocol = {'model_revision': '模型版本A', 'dataset_revision': '数据版本1',
                'prompt_revision': '提示版本1', 'scorer_revision': '评分器版本1',
                'seed': 7, 'attempt_budget': 1}
    return {'protocol': protocol_fingerprint(protocol),
            'overlap': [list(x) for x in split_overlap({'train': ['a', 'b'], 'test': ['b', 'c']}).values()],
            'result': score_run([{'id': 'a', 'status': 'passed'},
                                 {'id': 'b', 'status': 'failed'},
                                 {'id': 'c', 'status': 'error'}])}


if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
