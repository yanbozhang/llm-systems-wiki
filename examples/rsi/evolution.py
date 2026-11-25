"""离线教学：参数与框架交叉实验、候选前沿及改进器对照。"""
import math


def cross_effect(old_old, new_old, old_new, new_new):
    values = (old_old, new_old, old_new, new_new)
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in values):
        raise ValueError("成功率必须位于零至一")
    return new_new - new_old - old_new + old_old


def pareto_front(candidates):
    rows = [dict(row) for row in candidates]
    for row in rows:
        if not math.isfinite(row["quality"]) or not 0 <= row["quality"] <= 1:
            raise ValueError("质量必须位于零至一")
        if not math.isfinite(row["cost"]) or row["cost"] < 0:
            raise ValueError("成本必须为非负有限数")
    return [row for row in rows if not any(
        other["quality"] >= row["quality"] and other["cost"] <= row["cost"]
        and (other["quality"] > row["quality"] or other["cost"] < row["cost"])
        for other in rows)]


def compare_improvers(early, late, early_start, late_start, early_budget, late_budget):
    early, late = list(early), list(late)
    if not early or len(early) != len(late) or early_start != late_start:
        raise ValueError("必须使用相同起点与配对任务")
    if not math.isfinite(early_budget) or early_budget <= 0 or early_budget != late_budget:
        raise ValueError("必须使用相同的正预算")
    if not all(math.isfinite(value) for value in early + late):
        raise ValueError("结果必须是有限数")
    return sum(new - old for old, new in zip(early, late)) / len(early)


def demo():
    return {"interaction": cross_effect(0.5, 0.6, 0.7, 0.85),
            "front": pareto_front([{"quality": 0.8, "cost": 4}, {"quality": 0.7, "cost": 5}]),
            "improver_delta": compare_improvers([0.1, 0.2], [0.2, 0.25], "base", "base", 10, 10)}


if __name__ == "__main__":
    print(demo())
