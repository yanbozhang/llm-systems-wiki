"""选择题评分、随机基线与答案解析的教学实现。"""
import json
import math
import re


def choice_prediction(log_scores, lengths, normalize=False):
    """按对数分数或分数/长度选最大项；并列时选第一项，长度单位由协议给出。"""
    if not isinstance(log_scores, list) or not isinstance(lengths, list) or not log_scores or len(log_scores) != len(lengths):
        raise ValueError('分数与长度须非空且等长')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in log_scores):
        raise ValueError('分数须为有限数')
    if any(type(n) is not int or n <= 0 for n in lengths):
        raise ValueError('长度须为正整数')
    scores = [score / length if normalize else score for score, length in zip(log_scores, lengths)]
    return max(range(len(scores)), key=scores.__getitem__)


def chance_adjusted_accuracy(accuracy, option_counts):
    """逐题均匀猜测的平均基线及其线性调整；调整值允许为负。"""
    if type(accuracy) not in (int, float) or not math.isfinite(accuracy) or not 0 <= accuracy <= 1:
        raise ValueError('准确率须位于0至1')
    if not isinstance(option_counts, list) or not option_counts:
        raise ValueError('至少一题')
    if any(type(k) is not int or k < 2 for k in option_counts):
        raise ValueError('每题至少两个有效选项')
    chance = math.fsum(1 / k for k in option_counts) / len(option_counts)
    return {'chance': chance, 'adjusted': (accuracy - chance) / (1 - chance)}


def parse_choice(text, option_count):
    """只解析明确的answer is/answer:标记；无有效或存在矛盾答案时返回None。"""
    if not isinstance(text, str) or type(option_count) is not int or not 2 <= option_count <= 26:
        raise ValueError('需要文本与2至26个选项')
    matches = re.findall(r'\b(?:final\s+)?answer\s*(?:is|:)\s*\(?([A-Z])\)?\b', text, flags=re.I)
    indices = {ord(label.upper()) - ord('A') for label in matches}
    if len(indices) != 1:
        return None
    index = indices.pop()
    return index if 0 <= index < option_count else None


def demo():
    return {'raw_prediction': choice_prediction([-2, -3], [1, 4]),
            'normalized_prediction': choice_prediction([-2, -3], [1, 4], normalize=True),
            'chance': chance_adjusted_accuracy(0.5, [4, 10]),
            'parsed': parse_choice('Final answer: B', 4),
            'ambiguous': parse_choice('Answer: A. Answer: B.', 4)}


if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
