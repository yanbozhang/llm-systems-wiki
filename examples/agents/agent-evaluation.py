"""Agent评测：固定分母、证据归因和评估器审计。"""


def success_summary(histories: dict[str, list[str]]) -> dict:
    """保留每个任务全部尝试，汇总首次与允许重试后的成功及未知边界。"""
    if not histories or any(not attempts for attempts in histories.values()):
        raise ValueError('任务集与每条尝试历史必须非空')
    if any(s not in {'success', 'failure', 'unknown'}
           for attempts in histories.values() for s in attempts):
        raise ValueError('结果状态不合法')
    n = len(histories)
    first = sum(a[0] == 'success' for a in histories.values())
    eventual = sum('success' in a for a in histories.values())
    unresolved = sum('success' not in a and 'unknown' in a for a in histories.values())
    return {'tasks': n, 'attempts': sum(map(len, histories.values())),
            'first_rate': first / n, 'eventual_lower': eventual / n,
            'eventual_upper': (eventual + unresolved) / n,
            'unresolved_tasks': unresolved}


def first_divergence(trace: list[dict]) -> dict:
    """查找最早有证据的契约违反，输出归因候选而不宣称因果根因。"""
    unknown = []
    for event in trace:
        value = event['passed']
        if value is not None and type(value) is not bool:
            raise ValueError('检查结果类型不合法')
        if value is None or not event.get('evidence'):
            unknown.append(event['stage'])
            continue
        if value is False:
            return {'candidate': event['stage'], 'evidence': event['evidence'],
                    'earlier_unknown': unknown, 'causality': 'unproven'}
    return {'candidate': None, 'evidence': None, 'earlier_unknown': unknown,
            'causality': 'unproven'}


def audit_evaluator(predictions: list[bool], labels: list[bool | None]) -> dict:
    """对独立复核标签统计混淆矩阵，标签缺失单独计数。"""
    if len(predictions) != len(labels):
        raise ValueError('预测与标签长度不同')
    if any(type(p) is not bool for p in predictions):
        raise ValueError('预测必须为布尔值')
    if any(y is not None and type(y) is not bool for y in labels):
        raise ValueError('复核标签必须为布尔值或None')
    counts = {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0, 'unlabeled': 0}
    for predicted, actual in zip(predictions, labels):
        if actual is None:
            counts['unlabeled'] += 1
        elif predicted and actual:
            counts['tp'] += 1
        elif predicted:
            counts['fp'] += 1
        elif actual:
            counts['fn'] += 1
        else:
            counts['tn'] += 1
    precision_n = counts['tp'] + counts['fp']
    recall_n = counts['tp'] + counts['fn']
    return {**counts,
            'precision': counts['tp'] / precision_n if precision_n else None,
            'recall': counts['tp'] / recall_n if recall_n else None}


def demo() -> dict:
    """构造重试成功、未知和评估器假阳性的记录。"""
    return {'tasks': success_summary({'a': ['success'], 'b': ['failure', 'success'],
                                      'c': ['unknown']}),
            'audit': audit_evaluator([True, True, False, False], [True, False, True, None])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
