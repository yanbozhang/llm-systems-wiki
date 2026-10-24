"""RAG评分协议教学：只对已冻结标签计算，不调用检索器、生成器或裁判。"""


def context_precision_profile(verdicts, corpus_relevant_count=None):
    """比较Ragas式上下文AP、普通P@K与全库相关数分母，标签按排名排列。"""
    labels = list(verdicts)
    if any(type(v) not in (int, bool) or v not in (0, 1) for v in labels):
        raise ValueError("有用性标签须为0或1")
    hits, numerator = 0, 0.0
    for rank, useful in enumerate(labels, 1):
        hits += useful
        if useful:
            numerator += hits / rank
    if corpus_relevant_count is not None:
        if type(corpus_relevant_count) is not int or corpus_relevant_count < hits or corpus_relevant_count < 0:
            raise ValueError("全库相关项数须非负且不小于已检到的独立相关项数")
    return {"context_ap": numerator / (hits + 1e-10),
            "precision_at_k": hits / len(labels) if labels else None,
            "corpus_ap": numerator / corpus_relevant_count if corpus_relevant_count else None,
            "recall_at_k": hits / corpus_relevant_count if corpus_relevant_count else None,
            "retrieved_count": len(labels), "relevant_retrieved": hits,
            "empty_context": not labels}


def claim_coverage(reference_attributed, answer_supported):
    """分别用参考答案声明和系统回答声明做分母；空声明集记为未定义。"""
    reference = list(reference_attributed)
    answer = list(answer_supported)
    if any(type(v) not in (int, bool) or v not in (0, 1) for v in reference + answer):
        raise ValueError("声明支持标签须为0或1")
    return {"context_recall": sum(reference) / len(reference) if reference else None,
            "faithfulness": sum(answer) / len(answer) if answer else None,
            "reference_claim_count": len(reference), "answer_claim_count": len(answer),
            "reference_supported": sum(reference), "answer_supported": sum(answer)}


def judge_error_audit(human_labels, judge_labels):
    """按声明ID对齐人工与裁判标签，返回混淆矩阵和平均支持率偏移。"""
    human, judge = dict(human_labels), dict(judge_labels)
    if human.keys() != judge.keys():
        raise ValueError("两个裁判必须判断完全相同的声明ID")
    if any(type(v) not in (int, bool) or v not in (0, 1) for v in list(human.values()) + list(judge.values())):
        raise ValueError("标签须为0或1")
    counts = {"tp": 0, "fn": 0, "fp": 0, "tn": 0}
    for cid, truth in human.items():
        key = "tp" if truth and judge[cid] else "fn" if truth else "fp" if judge[cid] else "tn"
        counts[key] += 1
    n = len(human)
    positive = counts["tp"] + counts["fn"]
    negative = counts["fp"] + counts["tn"]
    return {**counts, "count": n,
            "sensitivity": counts["tp"] / positive if positive else None,
            "false_positive_rate": counts["fp"] / negative if negative else None,
            "human_support_rate": sum(human.values()) / n if n else None,
            "judge_support_rate": sum(judge.values()) / n if n else None,
            "mean_bias": (counts["fp"] - counts["fn"]) / n if n else None}


def demo():
    """排名、声明分母与裁判假阳性的可手算输入。"""
    return {"ranking": context_precision_profile([1, 0, 1], 4),
            "claims": claim_coverage([1, 0, 0, 0], [1]),
            "judge": judge_error_audit({"a": 1, "b": 1, "c": 0, "d": 0},
                                        {"a": 1, "b": 1, "c": 1, "d": 0})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
