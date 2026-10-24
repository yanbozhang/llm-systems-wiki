"""BM25、基础RRF及重排漏斗的标准库算例；不调用检索或重排模型。"""
import math
from collections import Counter


def bm25_scores(query_terms, documents, k1=1.2, b=0.75):
    """二值查询词的BM25；documents是已分词列表，采用正IDF和(k1+1)因子。"""
    if not math.isfinite(k1) or not math.isfinite(b) or k1 < 0 or not 0 <= b <= 1:
        raise ValueError("k1须非负，b须在 [0,1]")
    docs = [list(d) for d in documents]
    if not docs:
        return []
    avgdl = sum(map(len, docs)) / len(docs)
    if avgdl == 0:
        return [0.0] * len(docs)
    terms = set(query_terms)
    counts = [Counter(d) for d in docs]
    df = {t: sum(t in c for c in counts) for t in terms}
    result = []
    for doc, count in zip(docs, counts):
        score = 0.0
        norm = k1 * (1 - b + b * len(doc) / avgdl)
        for term in terms:
            freq = count[term]
            if freq:
                idf = math.log1p((len(docs) - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * freq * (k1 + 1) / (freq + norm)
        result.append(score)
    return result


def reciprocal_rank_fusion(rankings, constant=60.0, weights=None):
    """基础加权RRF：排名从1开始，缺席贡献0；不包含qmd的额外名次奖金。"""
    lists = [list(r) for r in rankings]
    weights = [1.0] * len(lists) if weights is None else list(weights)
    if not math.isfinite(constant) or constant < 0 or len(weights) != len(lists):
        raise ValueError("常数须非负，权重数量须匹配")
    if any(not math.isfinite(w) or w < 0 for w in weights):
        raise ValueError("权重须为有限非负数")
    scores, first_seen = {}, {}
    for ranking, weight in zip(lists, weights):
        if len(set(ranking)) != len(ranking):
            raise ValueError("单个排名列表不应有重复文档")
        for rank, doc in enumerate(ranking, 1):
            first_seen.setdefault(doc, len(first_seen))
            scores[doc] = scores.get(doc, 0.0) + weight / (constant + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], first_seen[x[0]]))


def rerank_audit(candidates, model_scores, relevant, top_k):
    """在既定候选内按外部模型分数重排；None表示回退原排序，并审计漏召回。"""
    candidates = list(candidates)
    relevant = set(relevant)
    if type(top_k) is not int or top_k < 1 or len(set(candidates)) != len(candidates):
        raise ValueError("top_k须为正整数，候选不得重复")
    if model_scores is None:
        ordered = candidates
        mode = "fallback"
    else:
        if set(model_scores) != set(candidates) or any(not math.isfinite(v) for v in model_scores.values()):
            raise ValueError("每个候选须恰有一个有限分数，不可插入外部文档")
        ordered = sorted(candidates, key=lambda d: -model_scores[d])
        mode = "reranked"
    selected = ordered[:top_k]
    return {"selected": selected, "mode": mode,
            "missing_from_candidates": sorted(relevant - set(candidates)),
            "candidate_recall": len(relevant & set(candidates)) / len(relevant) if relevant else None,
            "selected_recall": len(relevant & set(selected)) / len(relevant) if relevant else None}


def demo():
    """构造关键词饱和、双路融合与缺失证据无法被重排补回的例子。"""
    return {"bm25": bm25_scores(["缓存"], [["缓存", "缓存"], ["缓存", "调度"], ["索引"]]),
            "rrf": reciprocal_rank_fusion([["A", "B"], ["B", "C"]]),
            "rerank": rerank_audit(["A", "C"], {"A": 0.9, "C": 0.1}, {"A", "B"}, 1)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
