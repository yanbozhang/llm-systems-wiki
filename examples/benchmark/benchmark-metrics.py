"""评测统计的纯标准库教学实现，不产生任何真实模型成绩。"""
import json
import math
import random


def grouped_accuracy(groups):
    """分组二元结果分别计算逐题micro和类别等权macro；每组必须非空。"""
    if not isinstance(groups, dict) or not groups:
        raise ValueError('至少一个分组')
    means, correct, total = {}, 0, 0
    for name, values in groups.items():
        if not isinstance(name, str) or not isinstance(values, list) or not values:
            raise ValueError('分组名须为字符串且结果列表非空')
        if any(type(v) not in (int, bool) or v not in (0, 1) for v in values):
            raise ValueError('每题结果只能为0或1')
        means[name] = sum(values) / len(values)
        correct += sum(values)
        total += len(values)
    return {'micro': correct / total, 'macro': math.fsum(means.values()) / len(means),
            'by_group': means, 'n': total}


def wilson_interval(successes, total, z=1.959963984540054):
    """二项比例的双侧Wilson区间；z默认约为标准正态分布的97.5%分位。"""
    if type(successes) is not int or type(total) is not int or total <= 0:
        raise ValueError('计数须为整数且总数为正')
    if not 0 <= successes <= total or not isinstance(z, (int, float)) or not math.isfinite(z) or z <= 0:
        raise ValueError('计数范围或z不合法')
    p = successes / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return max(0.0, (center - radius) / denominator), min(1.0, (center + radius) / denominator)


def paired_bootstrap(a, b, draws=1000, seed=7):
    """相同题目的A/B分数按共同索引有放回重采样，返回均值差分布。"""
    if not isinstance(a, list) or not isinstance(b, list) or not a or len(a) != len(b):
        raise ValueError('两组非空结果必须逐题等长')
    if type(draws) is not int or draws <= 0 or type(seed) is not int:
        raise ValueError('抽样次数须为正整数，种子须为整数')
    if any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in a + b):
        raise ValueError('分数须为0到1的有限数')
    differences = [x - y for x, y in zip(a, b)]
    rng, n = random.Random(seed), len(differences)
    samples = [math.fsum(differences[rng.randrange(n)] for _ in range(n)) / n
               for _ in range(draws)]
    return {'observed': math.fsum(differences) / n, 'replicates': samples}


def demo():
    return {'accuracy': grouped_accuracy({'A': [1] * 81 + [0] * 9, 'B': [1] + [0] * 9}),
            'wilson_90_of_100': wilson_interval(90, 100),
            'paired_example': paired_bootstrap([1, 1, 0, 1], [1, 0, 0, 1], draws=8)}


if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
