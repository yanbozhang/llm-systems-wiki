"""MHA、MQA、GQA的头映射与预算，全部使用标准库。"""
import math


def grouped_attention(queries, keys, values):
    """每个Q头给一个查询；K/V按KV头与历史位置组织，返回映射和输出。"""
    hq, hkv = len(queries), len(keys)
    if not hq or not hkv or hq % hkv or len(values) != hkv:
        raise ValueError("Q头数须为KV头数的正整数倍")
    d = len(queries[0])
    if not d or any(len(q) != d for q in queries):
        raise ValueError("查询宽度须一致且非空")
    if any(not head for head in keys + values):
        raise ValueError("历史不可为空")
    length, dv = len(keys[0]), len(values[0][0])
    if not dv or any(len(head) != length for head in keys + values):
        raise ValueError("所有头历史须等长")
    if any(len(row) != d for head in keys for row in head):
        raise ValueError("键宽度不匹配")
    if any(len(row) != dv for head in values for row in head):
        raise ValueError("值宽度不匹配")
    if any(not math.isfinite(x) for row in queries for x in row) or any(
        not math.isfinite(x) for head in keys + values for row in head for x in row
    ):
        raise ValueError("输入须有限")
    group_size = hq // hkv
    mapping, weights, output = [], [], []
    for h, query in enumerate(queries):
        group = h // group_size
        scores = [sum(a * b for a, b in zip(query, key)) / math.sqrt(d) for key in keys[group]]
        e = [math.exp(s - max(scores)) for s in scores]
        w = [x / sum(e) for x in e]
        mapping.append(group)
        weights.append(w)
        output.append([sum(w[t] * values[group][t][c] for t in range(length)) for c in range(dv)])
    return {"mapping": mapping, "weights": weights, "output": output}


def kv_budget(batch, layers, tokens, query_heads, kv_heads, head_dim, bytes_per_element=2):
    """返回理想未分片KV张量字节数；不计权重、碎片或临时展开。"""
    dims = [batch, layers, tokens, query_heads, kv_heads, head_dim, bytes_per_element]
    if any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in dims):
        raise ValueError("预算参数须为正整数")
    if query_heads % kv_heads:
        raise ValueError("Q头数须可被KV头数整除")
    shared = 2 * batch * layers * tokens * kv_heads * head_dim * bytes_per_element
    mha = shared * query_heads // kv_heads
    return {"kv_bytes": shared, "mha_bytes": mha, "ratio": kv_heads / query_heads,
            "mib": shared / 2**20, "decode_score_elements": batch * query_heads * tokens}


def mean_pool_heads(head_vectors, kv_heads):
    """把各头同形投影展平为行，按连续分组求均值；不执行继续训练。"""
    count = len(head_vectors)
    if not count or not isinstance(kv_heads, int) or kv_heads <= 0 or count % kv_heads:
        raise ValueError("原头数须可被目标头数整除")
    width = len(head_vectors[0])
    if not width or any(len(row) != width for row in head_vectors):
        raise ValueError("所有投影须同形非空")
    group_size = count // kv_heads
    return [[sum(head_vectors[h][j] for h in range(g * group_size, (g + 1) * group_size)) / group_size
             for j in range(width)] for g in range(kv_heads)]


def demo():
    """返回共享头仍产生不同分布、缓存缩放与均值初始化示例。"""
    return {
        "grouped": grouped_attention([[1.0], [-1.0]], [[[1.0], [-1.0]]], [[[0.0], [10.0]]]),
        "budget": kv_budget(1, 32, 4096, 16, 4, 64),
        "pool": mean_pool_heads([[1.0, 0.0], [-1.0, 0.0], [2.0, 4.0], [4.0, 2.0]], 2),
    }


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
