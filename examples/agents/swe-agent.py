"""SWE-agent ACI窗口、唯一匹配与格式重试的纯数据教学示例。"""
from copy import deepcopy


def file_window(text, requested_start=1, window_size=5):
    """展示最多window_size行，返回一基行号与上下未显示行数；不读取文件。"""
    if not isinstance(text, str) or type(requested_start) is not int or type(window_size) is not int or requested_start < 1 or window_size < 1:
        raise ValueError("需要文本与正整数窗口参数")
    lines = text.splitlines()
    if not lines:
        return {"lines": [], "above": 0, "below": 0, "total": 0}
    start = min(requested_start - 1, max(0, len(lines) - window_size))
    end = min(len(lines), start + window_size)
    return {"lines": [(i + 1, lines[i]) for i in range(start, end)],
            "above": start, "below": len(lines) - end, "total": len(lines)}


def unique_edit(text, old, new):
    """仅当旧字符串恰出现一次且有变化时替换；任何失败都返回原文本。"""
    if not all(isinstance(x, str) for x in (text, old, new)) or not old:
        raise ValueError("输入须为字符串且old不可为空")
    count = text.count(old)
    if count == 0:
        return {"text": text, "status": "missing", "feedback": "重新读取目标片段，旧文本未精确匹配"}
    if count > 1:
        return {"text": text, "status": "ambiguous", "feedback": "补充足够上下文，使目标唯一"}
    if old == new:
        return {"text": text, "status": "unchanged", "feedback": "新旧文本相同，没有编辑"}
    return {"text": text.replace(old, new, 1), "status": "edited",
            "feedback": "匹配已应用，仍需检查语法和任务语义"}


def retry_trace(attempts, max_format_failures=3):
    """模拟一个外层step的格式重试；记录失败尝试，但不执行字符串中的动作。"""
    if type(max_format_failures) is not int or max_format_failures < 1:
        raise ValueError("失败预算须为正整数")
    trace, failures = [], 0
    retryable = {"format_error", "bash_syntax_error", "blocked_action"}
    for attempt in attempts:
        kind = attempt["kind"]
        if kind not in retryable | {"ok", "budget_error"}:
            raise ValueError("教学模型不支持该错误类别")
        trace.append(deepcopy(attempt))
        if kind in retryable:
            failures += 1
            if failures >= max_format_failures:
                return {"trace": trace, "format_failures": failures, "status": "exit_format", "executed": False}
        elif kind == "budget_error":
            return {"trace": trace, "format_failures": failures, "status": "exit_budget", "executed": False}
        else:
            return {"trace": trace, "format_failures": failures, "status": "step_complete", "executed": True}
    return {"trace": trace, "format_failures": failures, "status": "needs_attempt", "executed": False}


def demo():
    """模拟窗口边界、模糊编辑与一次格式错误后得到正常观察。"""
    return {"window": file_window("a\nb\nc\nd\ne\nf", 6, 3),
            "edit": unique_edit("x = 1\ny = 1", "1", "2"),
            "trace": retry_trace([{"kind": "format_error", "response": "missing action", "query": []},
                                  {"kind": "ok", "action": "view example.py", "observation": "1:x = 1", "query": []}])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
