"""Aider RepoMap、编辑匹配与Git边界的纯数据教学；绝不执行Git或文件操作。"""
import math
from collections import defaultdict


def repo_map(files, edges, personalization, symbol_costs, budget, damping=0.85, iterations=50):
    """对预提取引用图做个性化PageRank，再按符号贡献选严格预算内的排序前缀。"""
    nodes = sorted(set(files))
    edges = list(edges)  # 每项：(引用文件, 定义文件, 符号, 已计算边权)
    if not nodes or type(budget) is not int or budget < 0 or type(iterations) is not int or iterations < 1 or not 0 < damping < 1:
        raise ValueError("需要非空图、有效预算、迭代数与阻尼")
    if not set(personalization) <= set(nodes) or any(not math.isfinite(v) or v < 0 for v in personalization.values()):
        raise ValueError("个性化权重必须有限、非负并位于图内")
    total = sum(personalization.values())
    if total <= 0:
        raise ValueError("个性化权重和须为正")
    prior = {n: personalization.get(n, 0.0) / total for n in nodes}
    outgoing = dict.fromkeys(nodes, 0.0)
    for src, dst, symbol, weight in edges:
        if src not in outgoing or dst not in outgoing or not math.isfinite(weight) or weight <= 0:
            raise ValueError("边须连接图内节点且权重为正")
        outgoing[src] += weight
    rank = dict(prior)
    residual = 0.0
    for _ in range(iterations):
        dangling = sum(rank[n] for n in nodes if outgoing[n] == 0)
        nxt = {n: (1 - damping) * prior[n] + damping * dangling * prior[n] for n in nodes}
        for src, dst, _, weight in edges:
            nxt[dst] += damping * rank[src] * weight / outgoing[src]
        residual = sum(abs(nxt[n] - rank[n]) for n in nodes)
        rank = nxt
    importance = defaultdict(float)
    for src, dst, symbol, weight in edges:
        importance[(dst, symbol)] += rank[src] * weight / outgoing[src]
    ranked = sorted(importance, key=lambda k: (-importance[k], k))
    selected, remaining = [], budget
    for key in ranked:
        cost = symbol_costs[key]
        if type(cost) is not int or cost < 1:
            raise ValueError("符号渲染成本须为正整数")
        if cost > remaining:
            break
        selected.append(key)
        remaining -= cost
    return {"file_rank": rank, "symbol_rank": [(k, importance[k]) for k in ranked],
            "selected": selected, "remaining_tokens": remaining, "residual_l1": residual}


def search_replace(text, search, replacement):
    """演示首个精确行块匹配及统一缺失缩进回退；不执行其他生产回退或写文件。"""
    if not all(isinstance(v, str) for v in (text, search, replacement)) or not search.strip():
        raise ValueError("需要非空SEARCH行块")
    def lines(value):
        return (value + ("\n" if value and not value.endswith("\n") else "")).splitlines(keepends=True)
    whole, part, after = lines(text), lines(search), lines(replacement)
    matches = [i for i in range(len(whole) - len(part) + 1) if whole[i:i + len(part)] == part]
    if matches:
        start = matches[0]
        return {"text": "".join(whole[:start] + after + whole[start + len(part):]),
                "mode": "exact", "match_count": len(matches), "start_line": start + 1}
    for start in range(len(whole) - len(part) + 1):
        prefixes = set()
        valid = True
        for actual, expected in zip(whole[start:start + len(part)], part):
            if not expected.strip():
                valid = valid and not actual.strip()
                continue
            if not actual.endswith(expected):
                valid = False
                break
            prefix = actual[:len(actual) - len(expected)]
            if prefix.strip():
                valid = False
                break
            prefixes.add(prefix)
        if valid and len(prefixes) == 1:
            prefix = prefixes.pop()
            shifted = [prefix + line if line.strip() else line for line in after]
            return {"text": "".join(whole[:start] + shifted + whole[start + len(part):]),
                    "mode": "indent", "match_count": None, "start_line": start + 1}
    return {"text": text, "mode": "no_match", "match_count": 0, "start_line": None}


def commit_plan(dirty_files, edited_files, auto_commits=True, dirty_commits=True, git_enabled=True, dry_run=False):
    """返回文件级提交计划，不读取仓库、不提交；假定edited_files已经获准编辑。"""
    dirty, edited = set(dirty_files), set(edited_files)
    enabled = bool(git_enabled and auto_commits and not dry_run)
    before = dirty & edited if enabled and dirty_commits else set()
    return {"before_edit": sorted(before), "after_edit": sorted(edited) if enabled else [],
            "unrelated_dirty": sorted(dirty - edited),
            "overlap_without_checkpoint": sorted((dirty & edited) - before),
            "executes_git": False}


def demo():
    """三文件图、缩进回退和用户改动检查点的教学输入。"""
    edges = [("app.py", "lib.py", "parse", 2.0), ("lib.py", "lib.py", "parse", 1.0)]
    return {"map": repo_map(["app.py", "lib.py", "idle.py"], edges,
                            {"app.py": 1.0}, {("lib.py", "parse"): 4}, 5),
            "edit": search_replace("    x = 1\n", "x = 1\n", "x = 2\n"),
            "git": commit_plan({"app.py", "notes.md"}, {"app.py", "new.py"})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
