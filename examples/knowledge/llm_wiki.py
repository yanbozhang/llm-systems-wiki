"""持久知识编纂的离线教学；不执行抽取或自动发布。"""
from collections import defaultdict, deque


def source_layers(records):
    layers = {"raw": [], "claims": [], "pages": []}
    for record in records:
        if record["layer"] not in layers:
            raise ValueError("未知知识层")
        layers[record["layer"]].append(record["id"])
    return layers


def publication_ready(evidence, source_versions):
    return bool(evidence) and all(
        reference.get("source_id") in source_versions
        and reference.get("source_version") == source_versions[reference["source_id"]]
        and reference.get("reviewed") is True for reference in evidence)


def wiki_impact(page_links, changed, relation_types=("supported_by", "requires")):
    reverse = defaultdict(set)
    for page, links in page_links.items():
        for target, kind in links:
            if kind in relation_types:
                reverse[target].add(page)
    roots = set(changed)
    visited, pending = set(roots), deque(sorted(roots))
    while pending:
        for dependent in sorted(reverse.get(pending.popleft(), ())):
            if dependent not in visited:
                visited.add(dependent)
                pending.append(dependent)
    return sorted(visited - roots)


def demo():
    return {"layers": source_layers([{"id": "source", "layer": "raw"}]),
            "ready": publication_ready([{"source_id": "source", "source_version": "v1", "reviewed": True}], {"source": "v1"}),
            "impact": wiki_impact({"claim": [("source", "supported_by")]}, ["source"])}


if __name__ == "__main__":
    print(demo())
