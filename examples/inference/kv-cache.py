"""KV 的数学注意力、字节布局与前缀身份；只处理教学数据。"""
import hashlib
import json
import math


def kv_layout(lengths, layers, kv_heads, head_dim, element_bytes, block_size):
    """返回有效、按最长补齐及独立分页的KV字节数，不含共享和临时工作区。"""
    lengths = list(lengths)
    if any(type(x) is not int or x < 0 for x in lengths):
        raise ValueError("长度须为非负整数")
    if any(type(x) is not int or x < 1 for x in
           (layers, kv_heads, head_dim, element_bytes, block_size)):
        raise ValueError("维度、字节数与块大小须为正整数")
    per_token = 2 * layers * kv_heads * head_dim * element_bytes
    effective = sum(lengths)
    padded = len(lengths) * max(lengths, default=0)
    blocks = sum((n + block_size - 1) // block_size for n in lengths)
    return {"bytes_per_token": per_token, "effective_bytes": effective * per_token,
            "padded_bytes": padded * per_token, "paged_bytes": blocks * block_size * per_token,
            "blocks": blocks, "tail_waste_tokens": blocks * block_size - effective}


def cached_attention(query, past_keys, past_values, new_key, new_value):
    """单头单步注意力：追加当前K/V，稳定softmax后返回输出与新缓存。"""
    q = list(query)
    keys = [list(k) for k in past_keys] + [list(new_key)]
    values = [list(v) for v in past_values] + [list(new_value)]
    if not q or len(keys) != len(values) or not values[-1]:
        raise ValueError("需要非空维度及成对K/V")
    if any(len(k) != len(q) for k in keys) or any(len(v) != len(values[-1]) for v in values):
        raise ValueError("K与Q维度、各V维度须分别一致")
    if any(not math.isfinite(x) for row in [q] + keys + values for x in row):
        raise ValueError("向量须为有限数")
    scores = [sum(a * b for a, b in zip(q, k)) / math.sqrt(len(q)) for k in keys]
    peak = max(scores)
    weights = [math.exp(s - peak) for s in scores]
    total = sum(weights)
    weights = [w / total for w in weights]
    output = [sum(w * v[j] for w, v in zip(weights, values)) for j in range(len(values[0]))]
    return {"output": output, "weights": weights, "keys": keys, "values": values}


def prefix_block_hashes(tokens, block_size, identity):
    """给完整token块计算链式哈希；identity显式包含模型、adapter等兼容身份。"""
    tokens = list(tokens)
    if type(block_size) is not int or block_size < 1 or any(type(x) is not int or x < 0 for x in tokens):
        raise ValueError("块大小须为正整数，token须为非负整数")
    required = {"model", "adapter", "tokenizer", "position", "dtype", "salt"}
    if not isinstance(identity, dict) or not required <= identity.keys():
        raise ValueError("缓存身份字段不完整")
    if any(not isinstance(v, str) for v in identity.values()):
        raise ValueError("身份值须为字符串")
    parent = ""
    result = []
    for start in range(0, len(tokens) - block_size + 1, block_size):
        payload = [parent, tokens[start:start + block_size], identity]
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        parent = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        result.append(parent)
    return result


def demo():
    """小输入的结构化演示；哈希值只代表合成教学数据。"""
    identity = dict(model="model-v1", adapter="none", tokenizer="tok-v1",
                    position="rope-v1", dtype="fp16", salt="classroom")
    return {"layout": kv_layout([1024, 3072], 32, 8, 128, 2, 16),
            "attention": cached_attention([0.0], [[1.0]], [[2.0]], [3.0], [4.0]),
            "hashes": prefix_block_hashes([1, 2, 3, 4, 5], 2, identity)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
