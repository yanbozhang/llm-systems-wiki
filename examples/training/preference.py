"""DPO最优策略映射、偏好损失及序列log比值的标准库示例。"""
import math


def optimal_policy(reference, rewards, beta=1.0):
    """有限回答空间内解KL正则奖励最大化；返回策略与配分函数对数。"""
    if not reference or len(reference) != len(rewards) or not math.isfinite(beta) or beta <= 0:
        raise ValueError("概率与奖励须同长非空，beta须为有限正数")
    if any(not math.isfinite(p) or p <= 0 for p in reference) or not math.isclose(sum(reference), 1.0):
        raise ValueError("参考概率须严格为正且和为一")
    if not all(math.isfinite(r) for r in rewards):
        raise ValueError("奖励须有限")
    scores = [math.log(p) + r / beta for p, r in zip(reference, rewards)]
    peak = max(scores)
    shifted = [math.exp(s - peak) for s in scores]
    total = sum(shifted)
    return {"policy": [p / total for p in shifted], "log_partition": peak + math.log(total)}


def dpo_loss(chosen_logp, rejected_logp, ref_chosen_logp, ref_rejected_logp, beta=0.1):
    """标准sigmoid DPO单偏好对损失及对两项策略logp的偏导。"""
    if not all(math.isfinite(x) for x in [chosen_logp, rejected_logp, ref_chosen_logp, ref_rejected_logp, beta]) or beta <= 0:
        raise ValueError("输入须有限，beta须为正数")
    delta = (chosen_logp - ref_chosen_logp) - (rejected_logp - ref_rejected_logp)
    margin = beta * delta
    loss = max(0.0, -margin) + math.log1p(math.exp(-abs(margin)))
    wrong_probability = (math.exp(-margin) / (1 + math.exp(-margin)) if margin >= 0
                         else 1 / (1 + math.exp(margin)))
    return {"relative_delta": delta, "margin": margin, "loss": loss,
            "grad_chosen_logp": -beta * wrong_probability,
            "grad_rejected_logp": beta * wrong_probability}


def completion_logratio(policy_logps, reference_logps, mask):
    """输入逐token且已错位对齐的logp，返回回复log比值总和及诊断用均值。"""
    if not policy_logps or len(policy_logps) != len(reference_logps) or len(mask) != len(policy_logps):
        raise ValueError("概率序列和mask须同长非空")
    if any(m not in (0, 1, False, True) for m in mask):
        raise ValueError("mask须为二值")
    if not all(math.isfinite(x) for x in list(policy_logps) + list(reference_logps)):
        raise ValueError("logp须有限")
    ratios = [p - q for p, q, m in zip(policy_logps, reference_logps, mask) if m]
    if not ratios:
        raise ValueError("至少保留一个回复目标")
    total = sum(ratios)
    return {"sum": total, "mean": total / len(ratios), "tokens": len(ratios), "per_token": ratios}


def demo():
    """返回二回答最优策略、零差值损失与不同长度的log比值。"""
    return {"optimal": optimal_policy([0.5, 0.5], [math.log(3), 0.0]),
            "loss": dpo_loss(-2.0, -3.0, -2.0, -3.0),
            "chosen": completion_logratio([-1.0, -1.0], [-1.3, -1.3], [1, 1]),
            "rejected": completion_logratio([-1.0], [-1.5], [1])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
