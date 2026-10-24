"""多模态输入几何、MMMU核心答案判据与分层评分；不加载图像或调用模型。"""
import math
from collections import defaultdict


def square_pad_geometry(width, height, box):
    """按LLaVA expand2square计算原图区域的平移；只做填充，不模拟后续缩放裁剪。"""
    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError("图像宽高须为正整数")
    if len(box) != 4 or any(not math.isfinite(v) for v in box):
        raise ValueError("矩形须含四个有限坐标")
    left, top, right, bottom = box
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("矩形须位于原图内且面积为正")
    side = max(width, height)
    dx, dy = (side - width) // 2, (side - height) // 2
    moved = (left + dx, top + dy, right + dx, bottom + dy)
    return {"side": side, "offset": (dx, dy), "translated_box": moved,
            "normalized_box": tuple(v / side for v in moved),
            "content_area_fraction": width * height / (side * side)}


def mmmu_answer_score(question_type, gold, prediction):
    """复述MMMU核心判分：选择题标签匹配；开放题输入为已抽取候选，非完整原文解析器。"""
    answers = gold if isinstance(gold, list) else [gold]
    if not answers:
        raise ValueError("参考答案不能为空")
    if question_type == "multiple-choice":
        if not isinstance(prediction, str):
            raise ValueError("选择题预测须为选项标签")
        return any(answer == prediction for answer in answers)
    if question_type != "open" or not isinstance(prediction, list):
        raise ValueError("开放题须传入已抽取的候选列表")
    def normalize(value):
        text = str(value).strip()
        try:
            number = float(text.replace(",", ""))
        except ValueError:
            lowered = text.lower()
            return [" " + lowered, lowered + " "] if len(lowered) == 1 else [lowered]
        if not math.isfinite(number):
            raise ValueError("数值候选须为有限数")
        return [round(number, 2)]
    targets = [item for answer in answers for item in normalize(answer)]
    candidates = [item for pred in prediction for item in normalize(pred)]
    for pred in candidates:
        if isinstance(pred, str):
            if any(isinstance(target, str) and target in pred for target in targets):
                return True
        elif pred in targets:
            return True
    return False


def stratified_accuracy(rows, group_key="subject", expected_ids=None):
    """固定样本ID后计算样本加权准确率、组宏平均及人工错误层标签分布。"""
    rows = list(rows)
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("样本ID不能重复")
    if expected_ids is not None and set(ids) != set(expected_ids):
        raise ValueError("被评分样本集合与冻结集合不一致")
    groups = defaultdict(lambda: {"correct": 0, "count": 0})
    errors = defaultdict(int)
    for row in rows:
        if type(row["correct"]) is not bool:
            raise ValueError("correct须为布尔值")
        group = groups[row[group_key]]
        group["correct"] += row["correct"]
        group["count"] += 1
        if not row["correct"]:
            errors[row.get("error_layer") or "unclassified"] += 1
    for group in groups.values():
        group["accuracy"] = group["correct"] / group["count"]
    correct = sum(g["correct"] for g in groups.values())
    failures = len(rows) - correct
    return {"count": len(rows), "groups": dict(groups),
            "micro_accuracy": correct / len(rows) if rows else None,
            "macro_accuracy": sum(g["accuracy"] for g in groups.values()) / len(groups) if groups else None,
            "error_counts": dict(errors),
            "error_rates_among_failures": {k: v / failures for k, v in errors.items()} if failures else {}}


def demo():
    """矩形平移、两位小数和学科不均衡的教学输入。"""
    rows = [{"id": "a", "subject": "图表", "correct": True},
            {"id": "b", "subject": "图表", "correct": True},
            {"id": "c", "subject": "医学", "correct": False, "error_layer": "knowledge"}]
    return {"geometry": square_pad_geometry(640, 320, (0, 280, 640, 320)),
            "score": mmmu_answer_score("open", "3.14", [3.144]),
            "groups": stratified_accuracy(rows, expected_ids={"a", "b", "c"})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
