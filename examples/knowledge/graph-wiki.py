"""图查询与Wiki影响传播的离线教学；不执行LLM、社区发现或文件写入。"""
import math
from collections import defaultdict, deque


def local_graph_context(entities, entity_chunks, relations):
    """按实体排名、片段关联边数排序，片段重复时归属最早命中的实体。"""
    entities = list(entities)
    relations = list(relations)
    if len(set(entities)) != len(entities):
        raise ValueError("实体入口不得重复")
    seen, candidates = set(), []
    for rank, entity in enumerate(entities):
        incident = [r for r in relations if entity in (r["source"], r["target"])]
        for chunk in entity_chunks.get(entity, []):
            if chunk in seen:
                continue
            seen.add(chunk)
            edge_count = sum(chunk in r["chunks"] for r in incident)
            candidates.append({"chunk": chunk, "entity_rank": rank, "edge_count": edge_count})
    return sorted(candidates, key=lambda c: (c["entity_rank"], -c["edge_count"]))


def reduce_points(points, budget):
    """模拟全局查询reduce前筛选：去零分、降序排序，首个超预算点处停止。"""
    if type(budget) is not int or budget < 0:
        raise ValueError("预算须为非负整数")
    rows = [dict(p) for p in points]
    for p in rows:
        if not math.isfinite(p["score"]) or not 0 <= p["score"] <= 100 or type(p["tokens"]) is not int or p["tokens"] < 1:
            raise ValueError("分数须在0至100，包装后token数须正")
    ranked = sorted((p for p in rows if p["score"] > 0), key=lambda p: -p["score"])
    if not ranked:
        return {"selected": [], "remaining_tokens": budget, "status": "no_data"}
    selected, used = [], 0
    for p in ranked:
        if used + p["tokens"] > budget:
            break
        selected.append(p)
        used += p["tokens"]
    return {"selected": selected, "remaining_tokens": budget - used,
            "status": "ready" if selected else "budget_exhausted"}


def wiki_impact(page_links, changed, relation_types=("supported_by", "requires")):
    """对人工核验的类型化依赖建反向索引，求来源变更的传递影响；普通related不传播。"""
    reverse = defaultdict(set)
    allowed = set(relation_types)
    for page, links in page_links.items():
        for target, kind in links:
            if kind in allowed:
                reverse[target].add(page)
    roots = set(changed)
    visited, queue = set(roots), deque(sorted(roots))
    while queue:
        target = queue.popleft()
        for dependent in sorted(reverse.get(target, ())):
            if dependent not in visited:
                visited.add(dependent)
                queue.append(dependent)
    return sorted(visited - roots)


def demo():
    """给出局部片段排序、全局预算与来源到练习的影响链。"""
    relations = [{"source": "A", "target": "B", "chunks": {"b"}},
                 {"source": "A", "target": "C", "chunks": {"b"}},
                 {"source": "B", "target": "D", "chunks": {"c"}}]
    pages = {"claim": [("source-v1", "supported_by")],
             "topic": [("claim", "requires")], "exercise": [("topic", "requires")],
             "neighbor": [("topic", "related")]}
    return {"local": local_graph_context(["A", "B"], {"A": ["a", "b"], "B": ["b", "c"]}, relations),
            "global": reduce_points([{"text": "a", "score": 80, "tokens": 4},
                                      {"text": "b", "score": 70, "tokens": 3}], 5),
            "impact": wiki_impact(pages, {"source-v1"})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
