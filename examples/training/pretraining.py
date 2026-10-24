"""下一token目标、有效token损失与数据交叉重复审计的教学实现。"""
import math


def shift_targets(tokens, train_mask=None, ignore_index=-100):
    """外部错位一次，目标mask按目标token原始位置应用。"""
    if len(tokens) < 2:
        raise ValueError("至少需要两个token")
    if train_mask is None:
        train_mask = [True] * len(tokens)
    if len(train_mask) != len(tokens):
        raise ValueError("mask长度须与原序列一致")
    return {"input_ids": list(tokens[:-1]),
            "labels": [token if train_mask[i] else ignore_index for i, token in enumerate(tokens[1:], 1)]}


def token_loss(logits, targets, ignore_index=-100):
    """输入已对齐logits和目标，返回有效token平均CE、困惑度和解析梯度。"""
    if not logits or len(logits) != len(targets) or not logits[0]:
        raise ValueError("logits和目标须同长非空")
    width = len(logits[0])
    if any(len(row) != width for row in logits):
        raise ValueError("词表宽度须一致")
    count = sum(y != ignore_index for y in targets)
    if count == 0:
        raise ValueError("不能平均零个有效token")
    losses, gradients = [], []
    for row, target in zip(logits, targets):
        if not all(math.isfinite(x) for x in row):
            raise ValueError("logits须有限")
        if target == ignore_index:
            losses.append(0.0)
            gradients.append([0.0] * width)
            continue
        if not isinstance(target, int) or not 0 <= target < width:
            raise ValueError("目标索引越界")
        peak = max(row)
        exp_values = [math.exp(x - peak) for x in row]
        denom = sum(exp_values)
        losses.append(peak + math.log(denom) - row[target])
        gradients.append([(p / denom - float(j == target)) / count for j, p in enumerate(exp_values)])
    total = sum(losses)
    mean = total / count
    try:
        perplexity = math.exp(mean)
    except OverflowError:
        perplexity = math.inf
    return {"loss_sum": total, "valid_tokens": count, "mean_loss": mean,
            "perplexity": perplexity, "token_losses": losses, "gradients": gradients}


def audit_split(train_docs, validation_docs, shingle_size=2, threshold=0.5):
    """用空白分词的shingle集合审计跨集合近重复；只报候选，不自动删文档。"""
    if not isinstance(shingle_size, int) or shingle_size <= 0 or not 0 < threshold <= 1:
        raise ValueError("shingle大小须为正整数，阈值须在(0,1]")
    def features(text):
        tokens = text.casefold().split()
        if not tokens:
            raise ValueError("不接受空文档")
        size = min(shingle_size, len(tokens))
        return tuple(tokens), {tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}
    train = [features(text) for text in train_docs]
    valid = [features(text) for text in validation_docs]
    pairs, affected = [], set()
    for i, (left_tokens, left) in enumerate(train):
        for j, (right_tokens, right) in enumerate(valid):
            score = len(left & right) / len(left | right)
            if score >= threshold:
                pairs.append({"train": i, "validation": j, "jaccard": score,
                              "exact": left_tokens == right_tokens})
                affected.add(j)
    return {"pairs": pairs, "flagged_validation": len(affected),
            "flagged_fraction": len(affected) / len(valid) if valid else 0.0}


def demo():
    """返回错位、三目标困惑度和跨集合重复候选。"""
    return {"shift": shift_targets([10, 11, 12, 0], [True, True, True, False]),
            "loss": token_loss([[math.log(p), math.log(1 - p)] for p in [0.5, 0.25, 0.125]], [0, 0, 0]),
            "data": audit_split(["a b c d", "e f g"], ["a b c d", "a b c x"]) }


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
