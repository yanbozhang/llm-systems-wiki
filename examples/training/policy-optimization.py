"""GRPO组内优势、裁剪梯度与KL/长度归约的标准库教学计算。"""
import math


def group_advantages(rewards, ddof=1, eps=1e-4):
    """同一提示的组内优势；None表示无法评分，明确排除而非当零奖励。"""
    if not rewards or ddof not in (0, 1) or not math.isfinite(eps) or eps <= 0:
        raise ValueError("奖励须非空、ddof为0或1、epsilon为有限正数")
    valid = [r for r in rewards if r is not None]
    if any(not math.isfinite(r) for r in valid):
        raise ValueError("奖励须有限；缺失请使用None")
    if not valid:
        return {"mean": None, "std": 0.0, "advantages": [0.0] * len(rewards), "valid_count": 0}
    mean = sum(valid) / len(valid)
    variance = sum((r - mean)**2 for r in valid) / (len(valid) - ddof) if len(valid) > ddof else 0.0
    std = math.sqrt(variance)
    return {"mean": mean, "std": std, "advantages": [0.0 if r is None else (r - mean) / (std + eps) for r in rewards],
            "valid_count": len(valid)}


def clipped_surrogate(new_logp, old_logp, advantage, epsilon=0.2):
    """返回单token裁剪目标、负目标损失及非边界处对new_logp的导数。"""
    if not all(math.isfinite(x) for x in [new_logp, old_logp, advantage, epsilon]) or not 0 <= epsilon < 1:
        raise ValueError("输入须有限，epsilon须在[0,1)")
    try:
        ratio = math.exp(new_logp - old_logp)
    except OverflowError as exc:
        raise ValueError("概率比超出浮点范围") from exc
    clipped = min(max(ratio, 1 - epsilon), 1 + epsilon)
    objective = min(ratio * advantage, clipped * advantage)
    saturated = (advantage > 0 and ratio > 1 + epsilon) or (advantage < 0 and ratio < 1 - epsilon)
    return {"ratio": ratio, "objective": objective, "loss": -objective,
            "grad_new_logp": 0.0 if saturated else -advantage * ratio, "saturated": saturated}


def grpo_loss_terms(new_logps, old_logps, reference_logps, advantages, masks,
                    epsilon=0.2, beta=0.1, max_completion_length=None):
    """按已采样token计算裁剪加KL，并返回序列、token和固定长度三种归约。"""
    batch = len(new_logps)
    if not batch or any(len(x) != batch for x in [old_logps, reference_logps, advantages, masks]):
        raise ValueError("各批数据与优势须同长非空")
    if not math.isfinite(beta) or beta < 0:
        raise ValueError("beta须非负且有限")
    losses, kls, lengths = [], [], []
    for new, old, ref, adv, mask in zip(new_logps, old_logps, reference_logps, advantages, masks):
        if not new or any(len(row) != len(new) for row in [old, ref, mask]) or any(m not in (0, 1) for m in mask):
            raise ValueError("每条回复的logp和二值mask须同长非空")
        length = sum(mask)
        if length == 0:
            raise ValueError("教学归约不接受零个有效token的回复")
        row_loss, row_kl = [], []
        for lp, old_lp, ref_lp, valid in zip(new, old, ref, mask):
            if not valid:
                row_loss.append(0.0); row_kl.append(0.0)
                continue
            term = clipped_surrogate(lp, old_lp, adv, epsilon)
            if not math.isfinite(ref_lp):
                raise ValueError("参考logp须有限")
            log_ref_ratio = ref_lp - lp
            try:
                kl = math.expm1(log_ref_ratio) - log_ref_ratio
            except OverflowError as exc:
                raise ValueError("参考概率比超出浮点范围") from exc
            row_loss.append(term['loss'] + beta * kl)
            row_kl.append(kl)
        losses.append(row_loss); kls.append(row_kl); lengths.append(length)
    cap = max(lengths) if max_completion_length is None else max_completion_length
    if not isinstance(cap, int) or cap < max(lengths):
        raise ValueError("固定长度须为不小于实际有效长度的整数")
    total = sum(sum(row) for row in losses)
    return {"token_losses": losses, "sampled_kl": kls, "lengths": lengths,
            "sequence_mean": sum(sum(row) / n for row, n in zip(losses, lengths)) / batch,
            "token_mean": total / sum(lengths), "constant_mean": total / (batch * cap)}


def demo():
    """返回标准差约定、两侧裁剪与不等长回复归约的反例。"""
    rows = [[-1.0], [-1.0, -1.0, -1.0]]
    return {"advantages": group_advantages([0.0, 0.0, 1.0, 1.0]),
            "positive_clip": clipped_surrogate(math.log(0.6), math.log(0.4), 1.0),
            "negative_unclipped": clipped_surrogate(math.log(0.6), math.log(0.4), -1.0),
            "reductions": grpo_loss_terms(rows, rows, rows, [1.0, 3.0], [[1], [1, 1, 1]], max_completion_length=3)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
