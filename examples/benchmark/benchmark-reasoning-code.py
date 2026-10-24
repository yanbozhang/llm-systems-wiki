"""最终数值等价、pass@k和执行状态的教学计算；不执行生成代码。"""
import json
from fractions import Fraction
from math import comb


def numeric_equivalence(prediction, reference):
    """参考答案须为合法有理数文本；预测不可解析返回None，其他按精确值比较。"""
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError('参考答案须为非空有理数文本')
    try:
        expected = Fraction(reference.strip())
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('参考答案不是合法有理数') from exc
    if not isinstance(prediction, str):
        return None
    try:
        actual = Fraction(prediction.strip())
    except (ValueError, ZeroDivisionError):
        return None
    return actual == expected


def pass_at_k(n, correct, k):
    """n个已判定样本中无放回选k个，至少一个正确的组合估计。"""
    if any(type(v) is not int for v in (n, correct, k)):
        raise ValueError('计数须为整数')
    if n < 1 or not 0 <= correct <= n or not 1 <= k <= n:
        raise ValueError('需要n>=1、0<=correct<=n、1<=k<=n')
    if n - correct < k:
        return 1.0
    return 1.0 - comb(n - correct, k) / comb(n, k)


def execution_summary(records):
    """一条记录代表一个计划样本；未运行、超时、运行错误与测试失败分开。"""
    statuses = ('passed', 'assertion_failed', 'timeout', 'runtime_error', 'not_run')
    if not isinstance(records, list) or not records:
        raise ValueError('计划样本记录必须非空')
    counts, seen = dict.fromkeys(statuses, 0), set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError('记录须为对象')
        key, state = row.get('sample_id'), row.get('status')
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('样本ID缺失或重复')
        if not isinstance(state, str) or state not in counts:
            raise ValueError('执行状态无效')
        seen.add(key)
        counts[state] += 1
    n = len(records)
    attempted = n - counts['not_run']
    return {'counts': counts, 'planned': n, 'attempted': attempted,
            'coverage': attempted / n, 'success_rate': counts['passed'] / n,
            'attempted_success_rate': counts['passed'] / attempted if attempted else None}


def demo():
    return {'half': numeric_equivalence('0.5', '1/2'),
            'unparsed': numeric_equivalence('大约一半', '1/2'),
            'pass_at_2': pass_at_k(5, 2, 2),
            'execution': execution_summary([
                {'sample_id': 's1', 'status': 'passed'},
                {'sample_id': 's2', 'status': 'timeout'},
                {'sample_id': 's3', 'status': 'not_run'}])}


if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
