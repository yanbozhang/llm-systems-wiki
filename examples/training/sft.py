"""SFT目标mask、LoRA解析梯度及合并等价的标准库示例。"""
import math


def build_sft_labels(token_ids, assistant_mask, completion_mask=None, attention_mask=None):
    """用适用mask交集构造未移位labels，并列出下一token有效目标位置。"""
    if not token_ids:
        raise ValueError("token序列不能为空")
    masks = [assistant_mask]
    masks += [m for m in (completion_mask, attention_mask) if m is not None]
    if any(len(m) != len(token_ids) or any(x not in (0, 1, False, True) for x in m) for m in masks):
        raise ValueError("所有mask须为同长二值序列")
    labels = [token if all(m[i] for m in masks) else -100 for i, token in enumerate(token_ids)]
    targets = [i for i in range(1, len(labels)) if labels[i] != -100]
    return {"labels": labels, "target_positions": targets,
            "prediction_pairs": [(i - 1, labels[i]) for i in targets]}


def _dimensions(x, a, b, alpha):
    rank, inputs, outputs = len(a), len(x), len(b)
    if not rank or not inputs or not outputs or not math.isfinite(alpha):
        raise ValueError("维度须非零且alpha有限")
    if any(len(row) != inputs for row in a) or any(len(row) != rank for row in b):
        raise ValueError("要求A为[r,in]，B为[out,r]")
    return rank, inputs, outputs


def lora_gradients(x, a, b, upstream, alpha=1.0):
    """给定输出梯度，计算标准alpha/r LoRA的A/B梯度，不更新基础权重。"""
    rank, inputs, outputs = _dimensions(x, a, b, alpha)
    if len(upstream) != outputs:
        raise ValueError("上游梯度宽度不匹配")
    scale = alpha / rank
    ax = [sum(row[j] * x[j] for j in range(inputs)) for row in a]
    btg = [sum(b[i][j] * upstream[i] for i in range(outputs)) for j in range(rank)]
    grad_b = [[scale * upstream[i] * ax[j] for j in range(rank)] for i in range(outputs)]
    grad_a = [[scale * btg[i] * x[j] for j in range(inputs)] for i in range(rank)]
    delta = [scale * sum(row[j] * ax[j] for j in range(rank)) for row in b]
    return {"grad_a": grad_a, "grad_b": grad_b, "delta_output": delta,
            "trainable_parameters": rank * (inputs + outputs), "scale": scale}


def lora_merge_equivalence(weight, a, b, x, alpha=1.0):
    """比较未合并与显式合并的单适配器前向，不修改任何输入矩阵。"""
    rank, inputs, outputs = _dimensions(x, a, b, alpha)
    if len(weight) != outputs or any(len(row) != inputs for row in weight):
        raise ValueError("基础权重须为[out,in]")
    scale = alpha / rank
    delta = [[scale * sum(b[i][k] * a[k][j] for k in range(rank))
              for j in range(inputs)] for i in range(outputs)]
    merged = [[weight[i][j] + delta[i][j] for j in range(inputs)] for i in range(outputs)]
    ax = [sum(row[j] * x[j] for j in range(inputs)) for row in a]
    separate = [sum(weight[i][j] * x[j] for j in range(inputs))
                + scale * sum(b[i][k] * ax[k] for k in range(rank)) for i in range(outputs)]
    combined = [sum(row[j] * x[j] for j in range(inputs)) for row in merged]
    return {"delta_weight": delta, "merged_weight": merged, "separate": separate,
            "combined": combined, "max_error": max(abs(u - v) for u, v in zip(separate, combined))}


def demo():
    """返回标签交集、零B初始化梯度与一次合并的数值。"""
    return {
        "labels": build_sft_labels([10, 20, 30, 31, 0], [0, 0, 1, 1, 1], attention_mask=[1, 1, 1, 1, 0]),
        "gradients": lora_gradients([1.0, 2.0], [[1.0, -1.0]], [[0.0], [0.0]], [1.0, -1.0], 2.0),
        "merge": lora_merge_equivalence([[1.0, 0.0], [0.0, 1.0]], [[1.0, -1.0]], [[0.5], [-0.5]], [1.0, 2.0], 2.0),
    }


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
