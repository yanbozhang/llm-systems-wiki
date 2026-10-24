"""裁判交换顺序、一致性与概率校准教学；不调用模型，不产生人工标签。"""


def swapped_pair_summary(rows):
    """A/B指展示槽位；将第二轮交换结果映射回原候选，保留错误与不一致。"""
    if not rows or len({row['id'] for row in rows}) != len(rows):
        raise ValueError("题目须非空且ID唯一")
    reverse = {'A': 'B', 'B': 'A', 'tie': 'tie'}
    counts = dict.fromkeys(('A', 'B', 'tie', 'inconsistent', 'invalid'), 0)
    valid_calls = first_choices = decisive_calls = 0
    details = []
    for row in rows:
        ab, ba = row['winner_ab'], row['winner_ba']
        if ab not in ('A', 'B', 'tie', 'error') or ba not in ('A', 'B', 'tie', 'error'):
            raise ValueError("解析失败须显式使用error，不可转成tie")
        for label in (ab, ba):
            valid_calls += label != 'error'
            decisive_calls += label in ('A', 'B')
            first_choices += label == 'A'
        if 'error' in (ab, ba):
            result = 'invalid'
        else:
            result = ab if ab == reverse[ba] else 'inconsistent'
        counts[result] += 1
        details.append({'id': row['id'], 'original_order': ab,
                        'swapped_to_original': reverse.get(ba), 'result': result})
    valid_pairs = len(rows) - counts['invalid']
    consistent = sum(counts[label] for label in ('A', 'B', 'tie'))
    return {'pairs': len(rows), 'counts': counts, 'details': details,
            'parse_coverage': valid_calls / (2 * len(rows)),
            'valid_pair_coverage': valid_pairs / len(rows),
            'consistency_on_valid_pairs': consistent / valid_pairs if valid_pairs else None,
            'consistent_pair_fraction': consistent / len(rows),
            'first_slot_fraction_on_decisive_calls': first_choices / decisive_calls if decisive_calls else None}


def agreement_audit(human_labels, judge_labels):
    """计算同题配对的三分类混淆矩阵和未加权kappa；退化分母返回None。"""
    if not human_labels or len(human_labels) != len(judge_labels):
        raise ValueError("标签须非空、等长，并由调用方按同一题目顺序配对")
    labels = ('A', 'B', 'tie')
    if any(label not in labels for label in (*human_labels, *judge_labels)):
        raise ValueError("无效解析或缺失标签须先单独报告，不能当作tie")
    matrix = [[0] * len(labels) for _ in labels]
    for human, judge in zip(human_labels, judge_labels):
        matrix[labels.index(human)][labels.index(judge)] += 1
    n = len(human_labels)
    row_totals = [sum(row) for row in matrix]
    col_totals = [sum(matrix[i][j] for i in range(len(labels))) for j in range(len(labels))]
    diagonal = sum(matrix[i][i] for i in range(len(labels)))
    expected_numerator = sum(a * b for a, b in zip(row_totals, col_totals))
    denominator = n * n - expected_numerator
    kappa = (n * diagonal - expected_numerator) / denominator if denominator else None
    return {'n': n, 'labels': labels, 'matrix': matrix,
            'human_marginals': row_totals, 'judge_marginals': col_totals,
            'observed_agreement': diagonal / n,
            'chance_agreement': expected_numerator / (n * n), 'kappa': kappa}


def calibration_audit(probabilities, correctness, bins=2, threshold=0.8):
    """评估与独立人工仲裁一致这一事件的预测概率；不拟合校准器或调阈值。"""
    import math
    if not probabilities or len(probabilities) != len(correctness):
        raise ValueError("概率和事件标签须非空且等长")
    if type(bins) is not int or bins <= 0:
        raise ValueError("分箱数须为正整数")
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
           for p in (*probabilities, threshold)):
        raise ValueError("概率和阈值须为有限的零到一数值")
    if any(type(y) not in (int, bool) or y not in (0, 1) for y in correctness):
        raise ValueError("事件标签须为明确的零或一")
    n = len(probabilities)
    groups = [[] for _ in range(bins)]
    accepted = []
    for p, y in zip(probabilities, correctness):
        groups[min(int(p * bins), bins - 1)].append((p, y))
        if p >= threshold:
            accepted.append(y)
    reliability = []
    ece = 0.0
    for index, group in enumerate(groups):
        mean_p = sum(p for p, _ in group) / len(group) if group else None
        frequency = sum(y for _, y in group) / len(group) if group else None
        if group:
            ece += len(group) / n * abs(mean_p - frequency)
        reliability.append({'bin': index, 'count': len(group),
                            'mean_probability': mean_p, 'event_frequency': frequency})
    return {'n': n, 'binary_brier': sum((p - y) ** 2 for p, y in zip(probabilities, correctness)) / n,
            'ece': ece, 'reliability': reliability, 'threshold': threshold,
            'accepted': len(accepted), 'coverage': len(accepted) / n,
            'accepted_error': 1 - sum(accepted) / len(accepted) if accepted else None}


def demo():
    """返回可手算的小例；数值不是任何裁判模型的实测成绩。"""
    pairs = [{'id': 'q1', 'winner_ab': 'A', 'winner_ba': 'B'},
             {'id': 'q2', 'winner_ab': 'A', 'winner_ba': 'A'},
             {'id': 'q3', 'winner_ab': 'tie', 'winner_ba': 'tie'},
             {'id': 'q4', 'winner_ab': 'error', 'winner_ba': 'B'}]
    return {'swapping': swapped_pair_summary(pairs),
            'agreement': agreement_audit(['A', 'A', 'A', 'B', 'tie', 'tie'],
                                         ['A', 'A', 'B', 'B', 'B', 'tie']),
            'calibration': calibration_audit([0.9, 0.8, 0.6, 0.2], [1, 1, 0, 0])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
