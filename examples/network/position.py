"""RoPE 的二维恒等式、配对布局和缓存位置教学示例。"""
import math


def _rotate_pair(x, angle):
    c, s = math.cos(angle), math.sin(angle)
    return [x[0] * c - x[1] * s, x[0] * s + x[1] * c]


def relative_rotation(q, k, m, n, theta):
    """二维列向量旋转，返回双边旋转与仅相对旋转的点积。"""
    if len(q) != 2 or len(k) != 2 or not all(math.isfinite(x) for x in list(q) + list(k) + [m, n, theta]):
        raise ValueError("要求有限二维向量和角度参数")
    qm, kn = _rotate_pair(q, m * theta), _rotate_pair(k, n * theta)
    relative_k = _rotate_pair(k, (n - m) * theta)
    return {"both": sum(a * b for a, b in zip(qm, kn)),
            "relative": sum(a * b for a, b in zip(q, relative_k)),
            "q_norm_squared": sum(x * x for x in q),
            "rotated_norm_squared": sum(x * x for x in qm)}


def rope_layout(vector, position, base=10000.0, layout="split"):
    """对偶数宽向量应用RoPE；split按前后半配对，interleaved按邻接维配对。"""
    d = len(vector)
    if not d or d % 2 or base <= 0 or layout not in ("split", "interleaved"):
        raise ValueError("要求正偶数宽、正底数和合法布局")
    if not all(math.isfinite(x) for x in list(vector) + [position, base]):
        raise ValueError("输入须有限")
    out = [0.0] * d
    for j in range(d // 2):
        left, right = (j, j + d // 2) if layout == "split" else (2 * j, 2 * j + 1)
        angle = position * base ** (-2 * j / d)
        out[left], out[right] = _rotate_pair([vector[left], vector[right]], angle)
    return out


def cached_rope_scores(query, raw_keys, query_position, key_positions, scale=1.0):
    """从原始键重建旋转后内积，检查缓存位置；不实现生产缓存。"""
    if not raw_keys or len(raw_keys) != len(key_positions):
        raise ValueError("键与位置须一一对应且非空")
    if any(len(k) != len(query) for k in raw_keys) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("键宽度须匹配且缩放因子为有限正数")
    rotated_q = rope_layout(query, query_position / scale)
    rotated_keys = [rope_layout(k, p / scale) for k, p in zip(raw_keys, key_positions)]
    return [sum(a * b for a, b in zip(rotated_q, k)) / math.sqrt(len(query)) for k in rotated_keys]


def demo():
    """返回恒等式、分半布局及正确和错误续写位置的得分。"""
    keys = [[1.0, 0.0], [1.0, 0.0]]
    return {
        "identity": relative_rotation([1.0, 0.0], [1.0, 0.0], 0, 1, math.pi / 2),
        "layout": rope_layout([1.0, 2.0, 3.0, 4.0], 1),
        "continued": cached_rope_scores([1.0, 0.0], keys, 2, [0, 1]),
        "reset": cached_rope_scores([1.0, 0.0], keys, 0, [0, 1]),
    }


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
