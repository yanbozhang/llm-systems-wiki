"""Prefill/Decode 的时间、注意力工作量和预算教学模型；不调用服务。"""
import math


def request_metrics(arrival, token_times):
    """输入秒级到达时间和逐 token 时间，返回延迟与间隔；单 token 的 TPOT 为 None。"""
    times = list(token_times)
    if not math.isfinite(arrival) or not times:
        raise ValueError("需要有限的到达时间和至少一个输出事件")
    if any(not math.isfinite(t) for t in times) or times[0] < arrival:
        raise ValueError("时间无效或输出早于到达")
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("输出事件必须按时间排列")
    intervals = [b - a for a, b in zip(times, times[1:])]
    return {"ttft_s": times[0] - arrival, "e2e_s": times[-1] - arrival,
            "itl_s": intervals,
            "tpot_s": sum(intervals) / len(intervals) if intervals else None}


def attention_work(prompt_tokens, decode_steps, heads=1, head_dim=1):
    """统计有效因果位置对与 QK/AV 理想 FLOP，不把它当作硬件耗时。"""
    if any(not isinstance(x, int) or isinstance(x, bool) for x in
           (prompt_tokens, decode_steps, heads, head_dim)):
        raise ValueError("长度和维度必须是整数")
    if prompt_tokens < 1 or decode_steps < 0 or heads < 1 or head_dim < 1:
        raise ValueError("提示和维度须为正，解码步数须非负")
    prefill = prompt_tokens * (prompt_tokens + 1) // 2
    decode = decode_steps * prompt_tokens + decode_steps * (decode_steps + 1) // 2
    return {"prefill_pairs": prefill, "decode_pairs": decode,
            "attention_flops": 4 * heads * head_dim * (prefill + decode)}


def schedule_tokens(requests, budget, chunk_limit):
    """按传入顺序分配一轮 token 预算；每项为 (请求ID, 目标数, 已计算数)。"""
    if not isinstance(budget, int) or not isinstance(chunk_limit, int) or budget < 0 or chunk_limit < 1:
        raise ValueError("预算须非负，分块上限须为正整数")
    rows = list(requests)
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError("请求ID必须唯一")
    for _, target, computed in rows:
        if not isinstance(target, int) or not isinstance(computed, int) or not 0 <= computed <= target:
            raise ValueError("需满足 0 <= 已计算数 <= 目标数")
    result = []
    for rid, target, computed in rows:
        assigned = min(target - computed, chunk_limit, budget)
        result.append({"id": rid, "scheduled": assigned, "computed_after": computed + assigned})
        budget -= assigned
    return {"requests": result, "remaining_budget": budget}


def demo():
    """返回可供统一 UT 检查的小输入，不产生副作用。"""
    return {"timing": request_metrics(0, [0.8, 0.9, 1.0, 1.1, 1.2]),
            "work": attention_work(4, 2, 2, 8),
            "batch": schedule_tokens([("D", 101, 100), ("P", 12, 0)], 5, 4)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
