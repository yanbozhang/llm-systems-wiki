"""RAG概率、上下文预算与引用支持检查；人工标签不冒充自动事实判断。"""
import math


def rag_marginals(doc_probs, token_probs):
    """小规模已知目标序列概率：对比先乘后和的Sequence与先和后乘的Token。"""
    priors = list(doc_probs)
    rows = [list(r) for r in token_probs]
    if not priors or len(priors) != len(rows) or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
        raise ValueError("每份文档须有相同长度的非空token概率")
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in priors + [p for r in rows for p in r]):
        raise ValueError("概率须在 [0,1] 内")
    if not math.isclose(sum(priors), 1.0):
        raise ValueError("文档先验之和须为1")
    sequence = sum(p * math.prod(r) for p, r in zip(priors, rows))
    per_token = [sum(p * r[j] for p, r in zip(priors, rows)) for j in range(len(rows[0]))]
    return {"sequence_probability": sequence, "token_probability": math.prod(per_token),
            "per_token_probabilities": per_token}


def select_context(chunks, window_tokens, fixed_tokens, output_reserve):
    """按既定相关性顺序选完整片段，跳过过长项；身份含source/version/chunk。"""
    if any(type(x) is not int or x < 0 for x in (window_tokens, fixed_tokens, output_reserve)):
        raise ValueError("预算须为非负整数")
    budget = window_tokens - fixed_tokens - output_reserve
    if budget < 0:
        raise ValueError("固定开销和输出预算已超过窗口")
    picked, skipped, seen = [], [], set()
    for chunk in chunks:
        key = (chunk["source"], chunk["version"], chunk["chunk"])
        if key in seen:
            continue
        seen.add(key)
        cost = chunk["tokens"]
        if type(cost) is not int or cost < 1:
            raise ValueError("片段含包装后的token数须为正整数")
        if cost <= budget:
            picked.append(dict(chunk))
            budget -= cost
        else:
            skipped.append(key)
    return {"selected": picked, "skipped": skipped, "remaining_tokens": budget}


def audit_citations(claim_citations, evidence_support):
    """用人工冻结的支持关系审计引用；证据键是(source, version, chunk)。"""
    result = []
    for claim, refs in claim_citations.items():
        refs = list(dict.fromkeys(tuple(ref) for ref in refs))
        if any(len(ref) != 3 for ref in refs):
            raise ValueError("证据身份必须是三元组")
        unknown = [ref for ref in refs if ref not in evidence_support]
        supporting = [ref for ref in refs if claim in evidence_support.get(ref, set())]
        result.append({"claim": claim, "supporting": supporting, "unknown": unknown,
                       "supported": bool(supporting)})
    count = sum(r["supported"] for r in result)
    return {"claims": result, "supported_claims": count,
            "coverage": count / len(result) if result else None}


def demo():
    """返回两文档概率与版本不匹配的引用反例。"""
    chunks = [{"source": "A", "version": "v1", "chunk": "a", "tokens": 4},
              {"source": "B", "version": "v1", "chunk": "b", "tokens": 3}]
    return {"probability": rag_marginals([0.6, 0.4], [[0.9, 0.1], [0.2, 0.8]]),
            "context": select_context(chunks, 10, 2, 2),
            "citations": audit_citations({"claim-a": [("A", "v2", "a")]},
                                          {("A", "v1", "a"): {"claim-a"}})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
