"""Transformer 的标准库教学计算；不加载模型，不运行外部代码。"""
import math


def _softmax(values):
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError("得分须非空且有限")
    peak = max(values)
    weights = [math.exp(x - peak) for x in values]
    total = sum(weights)
    return [x / total for x in weights]


def causal_attention(q, k, v):
    """输入同长二维 Q/K/V；返回因果权重矩阵与加权输出。"""
    n = len(q)
    if not n or len(k) != n or len(v) != n or not q[0] or not v[0]:
        raise ValueError("Q/K/V须同长非空")
    d, dv = len(q[0]), len(v[0])
    if any(len(row) != d for row in q + k) or any(len(row) != dv for row in v):
        raise ValueError("各行维度须一致")
    if any(not math.isfinite(x) for row in q + k + v for x in row):
        raise ValueError("输入须有限")
    weights, output = [], []
    for i, query in enumerate(q):
        visible = [sum(a * b for a, b in zip(query, key)) / math.sqrt(d)
                   for key in k[:i + 1]]
        row = _softmax(visible) + [0.0] * (n - i - 1)
        weights.append(row)
        output.append([sum(row[j] * v[j][c] for j in range(n)) for c in range(dv)])
    return {"weights": weights, "output": output}


def split_merge_heads(rows, heads):
    """把 [T,C] 拆为 [H,T,D] 再按原顺序合并；不做投影。"""
    if not rows or not rows[0] or not isinstance(heads, int) or heads <= 0:
        raise ValueError("输入非空且头数为正整数")
    width = len(rows[0])
    if width % heads or any(len(row) != width for row in rows):
        raise ValueError("宽度须一致且可被头数整除")
    d = width // heads
    split = [[list(row[h * d:(h + 1) * d]) for row in rows] for h in range(heads)]
    merged = [[x for h in range(heads) for x in split[h][t]] for t in range(len(rows))]
    return {"heads": split, "merged": merged, "shape": [heads, len(rows), d]}


def generate_tokens(transition_logits, start, draws, temperature=1.0, top_k=None):
    """用末token转移表模拟自回归循环；draws给出每步零到一的抽样位置。"""
    size = len(transition_logits)
    if not size or any(len(row) != size for row in transition_logits):
        raise ValueError("转移表须为非空方阵")
    if not isinstance(start, int) or not 0 <= start < size:
        raise ValueError("起始token越界")
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("温度须为有限正数")
    if top_k is not None and (not isinstance(top_k, int) or not 1 <= top_k <= size):
        raise ValueError("top_k须在词表范围内")
    tokens, trace = [start], []
    for u in draws:
        if not 0 <= u < 1:
            raise ValueError("抽样位置须在[0,1)")
        logits = transition_logits[tokens[-1]]
        if not all(math.isfinite(x) for x in logits):
            raise ValueError("logits须有限")
        threshold = sorted(logits, reverse=True)[(top_k or size) - 1]
        keep = [i for i, score in enumerate(logits) if score >= threshold]
        probs = _softmax([logits[i] / temperature for i in keep])
        cumulative, chosen = 0.0, keep[-1]
        for i, p in zip(keep, probs):
            cumulative += p
            if u < cumulative:
                chosen = i
                break
        trace.append({"history": list(tokens), "candidates": keep, "probabilities": probs})
        tokens.append(chosen)
    return {"tokens": tokens, "trace": trace}


def demo():
    """返回三个知识点的可检查输入输出。"""
    return {
        "attention": causal_attention([[1.0, 0.0]] * 3, [[2.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[1.0], [3.0], [9.0]]),
        "heads": split_merge_heads([[0, 1, 2, 3], [4, 5, 6, 7]], 2),
        "generation": generate_tokens([[0.0, math.log(3)], [math.log(4), 0.0]], 0, [0.5, 0.5]),
    }


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
